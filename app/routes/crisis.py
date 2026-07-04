import requests as http
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Disaster, AuditLog
from app.ml.predictor import predict_severity

crisis_bp = Blueprint("crisis", __name__)


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


# ── List all disasters ────────────────────────────────────────────────────────

@crisis_bp.route("/")
@login_required
def list_crises():
    status_filter = request.args.get("status", "")
    type_filter   = request.args.get("type", "")
    query = Disaster.query.order_by(Disaster.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    if type_filter:
        query = query.filter_by(disaster_type=type_filter)
    disasters = query.all()
    return render_template("crisis/list.html", disasters=disasters,
                           status_filter=status_filter, type_filter=type_filter)


# ── GeoJSON endpoint for Leaflet map ─────────────────────────────────────────

@crisis_bp.route("/geojson")
@login_required
def geojson():
    disasters = Disaster.query.filter_by(status="active").all()
    features = [d.to_geojson() for d in disasters]
    return jsonify({"type": "FeatureCollection", "features": features})


# ── Create disaster ───────────────────────────────────────────────────────────

@crisis_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title          = request.form.get("title", "").strip()
        description    = request.form.get("description", "").strip()
        disaster_type  = request.form.get("disaster_type")
        severity       = request.form.get("severity", "medium")
        latitude       = request.form.get("latitude")
        longitude      = request.form.get("longitude")
        location_name  = request.form.get("location_name", "").strip()
        affected_people = int(request.form.get("affected_people", 0) or 0)

        if not all([title, disaster_type, latitude, longitude]):
            flash("Title, type, and location are required.", "danger")
            return render_template("crisis/create.html")

        # ML severity prediction
        severity_score = predict_severity(
            disaster_type=disaster_type,
            affected_people=affected_people,
            latitude=float(latitude),
            longitude=float(longitude),
        )
        if severity_score >= 0.75:
            severity = "critical"
        elif severity_score >= 0.5:
            severity = "high"
        elif severity_score >= 0.25:
            severity = "medium"
        else:
            severity = "low"

        disaster = Disaster(
            title=title,
            description=description,
            disaster_type=disaster_type,
            severity=severity,
            severity_score=round(severity_score, 3),
            latitude=float(latitude),
            longitude=float(longitude),
            location_name=location_name,
            affected_people=affected_people,
            created_by=current_user.id,
        )
        db.session.add(disaster)
        db.session.commit()
        _audit("CREATE_CRISIS", f"Created disaster #{disaster.id}: {title}")
        flash(f"Crisis report created. Predicted severity: {severity.upper()}", "success")
        return redirect(url_for("crisis.detail", disaster_id=disaster.id))

    return render_template("crisis/create.html")

