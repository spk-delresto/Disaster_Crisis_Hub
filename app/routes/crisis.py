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

# ── View single disaster ──────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>")
@login_required
def detail(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)

    # Fetch current weather from OpenWeatherMap
    weather = None
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if api_key:
        try:
            resp = http.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": float(disaster.latitude), "lon": float(disaster.longitude),
                        "appid": api_key, "units": "metric"},
                timeout=5,
            )
            if resp.ok:
                data = resp.json()
                weather = {
                    "temp": data["main"]["temp"],
                    "description": data["weather"][0]["description"].capitalize(),
                    "wind_speed": data["wind"]["speed"],
                    "humidity": data["main"]["humidity"],
                    "icon": data["weather"][0]["icon"],
                }
        except Exception:
            pass  # Weather is non-critical

    return render_template("crisis/detail.html", disaster=disaster, weather=weather)


# ── Edit disaster ─────────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/edit", methods=["GET", "POST"])
@login_required
def edit(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)

    if request.method == "POST":
        disaster.title          = request.form.get("title", disaster.title).strip()
        disaster.description    = request.form.get("description", disaster.description)
        disaster.disaster_type  = request.form.get("disaster_type", disaster.disaster_type)
        disaster.severity       = request.form.get("severity", disaster.severity)
        disaster.status         = request.form.get("status", disaster.status)
        disaster.affected_people = int(request.form.get("affected_people", 0) or 0)
        disaster.location_name  = request.form.get("location_name", disaster.location_name)
        db.session.commit()
        _audit("EDIT_CRISIS", f"Edited disaster #{disaster_id}")
        flash("Crisis report updated.", "success")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))

    return render_template("crisis/create.html", disaster=disaster, editing=True)


# ── Delete disaster ───────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/delete", methods=["POST"])
@login_required
def delete(disaster_id):
    if current_user.role not in ("admin", "responder"):
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.list_crises"))
    disaster = Disaster.query.get_or_404(disaster_id)
    db.session.delete(disaster)
    db.session.commit()
    _audit("DELETE_CRISIS", f"Deleted disaster #{disaster_id}")
    flash("Crisis report deleted.", "info")
    return redirect(url_for("crisis.list_crises"))
