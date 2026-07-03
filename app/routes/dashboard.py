from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from sqlalchemy import func
from app.models import Disaster, User, AuditLog
from app.extensions import db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    total     = Disaster.query.count()
    active    = Disaster.query.filter_by(status="active").count()
    critical  = Disaster.query.filter_by(severity="critical").count()
    resolved  = Disaster.query.filter_by(status="resolved").count()

    recent = Disaster.query.order_by(Disaster.created_at.desc()).limit(5).all()

    return render_template(
        "dashboard/index.html",
        total=total, active=active, critical=critical, resolved=resolved,
        recent=recent,
    )


@dashboard_bp.route("/api/chart-data")
@login_required
def chart_data():
    """JSON endpoint consumed by Chart.js on the dashboard."""

    # By type
    by_type = db.session.query(
        Disaster.disaster_type, func.count(Disaster.id)
    ).group_by(Disaster.disaster_type).all()

    # By severity
    by_severity = db.session.query(
        Disaster.severity, func.count(Disaster.id)
    ).group_by(Disaster.severity).all()

    # Timeline: last 7 days
    from datetime import datetime, timedelta
    days = []
    counts = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        count = Disaster.query.filter(
            func.date(Disaster.created_at) == day
        ).count()
        days.append(day.strftime("%b %d"))
        counts.append(count)

    return jsonify({
        "by_type":     {"labels": [r[0] for r in by_type],     "data": [r[1] for r in by_type]},
        "by_severity": {"labels": [r[0] for r in by_severity], "data": [r[1] for r in by_severity]},
        "timeline":    {"labels": days, "data": counts},
    })
