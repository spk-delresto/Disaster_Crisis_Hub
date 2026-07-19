from flask import Blueprint, render_template
from flask_login import current_user
from app.models import Disaster, User

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def index():
    total_crises  = Disaster.query.count()
    active_crises = Disaster.query.filter_by(status="active").count()
    total_users   = User.query.count()
    return render_template(
        "home.html",
        total_crises=total_crises,
        active_crises=active_crises,
        total_users=total_users,
    )
