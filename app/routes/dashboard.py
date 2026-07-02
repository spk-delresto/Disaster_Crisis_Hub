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
