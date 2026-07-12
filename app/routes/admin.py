from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import User, Disaster, AuditLog, AlertLog
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint("admin", __name__)


# ── Admin-only decorator ──────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


def _audit(action, detail=None):
    log = AuditLog(
        user_id=current_user.id,
        action=action,
        detail=detail,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:300],
    )
    db.session.add(log)
    db.session.commit()


# ── Admin dashboard ───────────────────────────────────────────────────────────

@admin_bp.route("/")
@login_required
@admin_required
def index():
    total_users     = User.query.count()
    active_users    = User.query.filter_by(is_active=True).count()
    total_disasters = Disaster.query.count()
    total_alerts    = AlertLog.query.count()

    # Recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()

    # User role breakdown
    role_counts = db.session.query(
        User.role, func.count(User.id)
    ).group_by(User.role).all()

    # Logins in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_logins = AuditLog.query.filter(
        AuditLog.action == "LOGIN",
        AuditLog.created_at >= week_ago
    ).count()

    return render_template(
        "admin/index.html",
        total_users=total_users,
        active_users=active_users,
        total_disasters=total_disasters,
        total_alerts=total_alerts,
        recent_logs=recent_logs,
        role_counts=dict(role_counts),
        recent_logins=recent_logins,
    )


# ── User management ───────────────────────────────────────────────────────────

@admin_bp.route("/users")
@login_required
@admin_required
def users():
    search = request.args.get("search", "").strip()
    query = User.query.order_by(User.created_at.desc())
    if search:
        query = query.filter(
            User.username.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
    users = query.all()
    return render_template("admin/users.html", users=users, search=search)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        new_role     = request.form.get("role", user.role)
        is_active    = request.form.get("is_active") == "on"
        new_password = request.form.get("new_password", "").strip()

        if user.id == current_user.id and new_role != "admin":
            flash("You cannot remove your own admin role.", "danger")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        user.role      = new_role
        user.is_active = is_active

        if new_password:
            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "danger")
                return render_template("admin/edit_user.html", user=user)
            user.password = generate_password_hash(new_password, method="pbkdf2:sha256")
            _audit("ADMIN_RESET_PASSWORD", f"Reset password for user #{user_id}")

        db.session.commit()
        _audit("ADMIN_EDIT_USER", f"Edited user #{user_id}: role={new_role}, active={is_active}")
        flash(f"User {user.username} updated.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/edit_user.html", user=user)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    db.session.commit()
    status = "activated" if user.is_active else "deactivated"
    _audit("ADMIN_TOGGLE_USER", f"User #{user_id} {status}")
    flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.users"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    _audit("ADMIN_DELETE_USER", f"Deleted user #{user_id} ({username})")
    flash(f"User {username} deleted.", "info")
    return redirect(url_for("admin.users"))


# ── Crisis management ─────────────────────────────────────────────────────────

@admin_bp.route("/crises")
@login_required
@admin_required
def crises():
    crises = Disaster.query.order_by(Disaster.created_at.desc()).all()
    return render_template("admin/crises.html", crises=crises)


@admin_bp.route("/crises/<int:disaster_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_crisis(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    title = disaster.title
    db.session.delete(disaster)
    db.session.commit()
    _audit("ADMIN_DELETE_CRISIS", f"Force-deleted crisis #{disaster_id}: {title}")
    flash(f"Crisis '{title}' deleted.", "info")
    return redirect(url_for("admin.crises"))


# ── Audit log viewer ──────────────────────────────────────────────────────────

@admin_bp.route("/audit")
@login_required
@admin_required
def audit():
    page        = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "")
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    logs = query.paginate(page=page, per_page=30, error_out=False)

    # Distinct actions for filter dropdown
    actions = db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    actions = [a[0] for a in actions]

    return render_template("admin/audit.html", logs=logs,
                           action_filter=action_filter, actions=actions)
