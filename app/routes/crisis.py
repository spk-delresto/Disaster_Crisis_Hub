import requests as http
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    Disaster, AuditLog, CrisisComment, AffectedArea,
    CrisisMedia, IncidentTimeline, ResourceRequest,
    EvacuationRoute, ReliefSupply, Volunteer
)
from app.ml.predictor import predict_severity
from datetime import datetime

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


@crisis_bp.route("/geojson")
@login_required
def geojson():
    disasters = Disaster.query.filter_by(status="active").all()
    features = [d.to_geojson() for d in disasters]
    return jsonify({"type": "FeatureCollection", "features": features})


@crisis_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title           = request.form.get("title", "").strip()
        description     = request.form.get("description", "").strip()
        disaster_type   = request.form.get("disaster_type")
        latitude        = request.form.get("latitude")
        longitude       = request.form.get("longitude")
        location_name   = request.form.get("location_name", "").strip()
        affected_people = int(request.form.get("affected_people", 0) or 0)
        if not all([title, disaster_type, latitude, longitude]):
            flash("Title, type, and location are required.", "danger")
            return render_template("crisis/create.html")
        severity_score = predict_severity(
            disaster_type=disaster_type, affected_people=affected_people,
            latitude=float(latitude), longitude=float(longitude),
        )
        if severity_score >= 0.75: severity = "critical"
        elif severity_score >= 0.5: severity = "high"
        elif severity_score >= 0.25: severity = "medium"
        else: severity = "low"
        disaster = Disaster(
            title=title, description=description,
            disaster_type=disaster_type, severity=severity,
            severity_score=round(severity_score, 3),
            latitude=float(latitude), longitude=float(longitude),
            location_name=location_name, affected_people=affected_people,
            created_by=current_user.id,
        )
        db.session.add(disaster)
        db.session.commit()
        _audit("CREATE_CRISIS", f"Created disaster #{disaster.id}: {title}")
        flash(f"Crisis report created. Predicted severity: {severity.upper()}", "success")
        return redirect(url_for("crisis.detail", disaster_id=disaster.id))
    return render_template("crisis/create.html")


@crisis_bp.route("/<int:disaster_id>")
@login_required
def detail(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    weather = None
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if api_key:
        try:
            resp = http.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": float(disaster.latitude), "lon": float(disaster.longitude),
                        "appid": api_key, "units": "metric"}, timeout=5,
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
            pass
    my_volunteer = Volunteer.query.filter_by(disaster_id=disaster_id, user_id=current_user.id).first()
    return render_template("crisis/detail.html", disaster=disaster, weather=weather, my_volunteer=my_volunteer)


@crisis_bp.route("/<int:disaster_id>/edit", methods=["GET", "POST"])
@login_required
def edit(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    if request.method == "POST":
        disaster.title           = request.form.get("title", disaster.title).strip()
        disaster.description     = request.form.get("description", disaster.description)
        disaster.disaster_type   = request.form.get("disaster_type", disaster.disaster_type)
        disaster.severity        = request.form.get("severity", disaster.severity)
        disaster.status          = request.form.get("status", disaster.status)
        disaster.affected_people = int(request.form.get("affected_people", 0) or 0)
        disaster.location_name   = request.form.get("location_name", disaster.location_name)
        db.session.commit()
        _audit("EDIT_CRISIS", f"Edited disaster #{disaster_id}")
        flash("Crisis report updated.", "success")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))
    return render_template("crisis/create.html", disaster=disaster, editing=True)


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


# ── COMMENTS ──────────────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/comments/add", methods=["POST"])
@login_required
def add_comment(disaster_id):
    text = request.form.get("comment", "").strip()
    if not text:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))
    db.session.add(CrisisComment(disaster_id=disaster_id, user_id=current_user.id, comment=text))
    db.session.commit()
    flash("Comment added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    c = CrisisComment.query.get_or_404(comment_id)
    if c.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=c.disaster_id))
    did = c.disaster_id
    db.session.delete(c)
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── AFFECTED AREAS ────────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/areas/add", methods=["POST"])
@login_required
def add_area(disaster_id):
    db.session.add(AffectedArea(
        disaster_id=disaster_id,
        area_name=request.form.get("area_name", "").strip(),
        population=int(request.form.get("population", 0) or 0),
        damage_level=request.form.get("damage_level", "moderate"),
        notes=request.form.get("notes", "").strip(),
    ))
    db.session.commit()
    flash("Affected area added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/areas/<int:area_id>/delete", methods=["POST"])
@login_required
def delete_area(area_id):
    area = AffectedArea.query.get_or_404(area_id)
    did = area.disaster_id
    db.session.delete(area)
    db.session.commit()
    flash("Area removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── CRISIS MEDIA ──────────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/media/add", methods=["POST"])
@login_required
def add_media(disaster_id):
    db.session.add(CrisisMedia(
        disaster_id=disaster_id, user_id=current_user.id,
        media_type=request.form.get("media_type", "link"),
        url=request.form.get("url", "").strip(),
        caption=request.form.get("caption", "").strip(),
    ))
    db.session.commit()
    flash("Media added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/media/<int:media_id>/delete", methods=["POST"])
@login_required
def delete_media(media_id):
    m = CrisisMedia.query.get_or_404(media_id)
    if m.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=m.disaster_id))
    did = m.disaster_id
    db.session.delete(m)
    db.session.commit()
    flash("Media removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── INCIDENT TIMELINE ─────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/timeline/add", methods=["POST"])
@login_required
def add_timeline(disaster_id):
    try:
        event_time = datetime.strptime(request.form.get("event_time", ""), "%Y-%m-%dT%H:%M")
    except ValueError:
        event_time = datetime.utcnow()
    db.session.add(IncidentTimeline(
        disaster_id=disaster_id, created_by=current_user.id,
        event_time=event_time,
        title=request.form.get("title", "").strip(),
        description=request.form.get("description", "").strip(),
    ))
    db.session.commit()
    flash("Timeline event added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/timeline/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_timeline(event_id):
    e = IncidentTimeline.query.get_or_404(event_id)
    if e.created_by != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=e.disaster_id))
    did = e.disaster_id
    db.session.delete(e)
    db.session.commit()
    flash("Timeline event deleted.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── RESOURCE REQUESTS ─────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/resources/add", methods=["POST"])
@login_required
def add_resource(disaster_id):
    db.session.add(ResourceRequest(
        disaster_id=disaster_id, user_id=current_user.id,
        resource=request.form.get("resource", "").strip(),
        quantity=int(request.form.get("quantity", 1) or 1),
        unit=request.form.get("unit", "").strip(),
        priority=request.form.get("priority", "medium"),
        notes=request.form.get("notes", "").strip(),
    ))
    db.session.commit()
    flash("Resource request submitted.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/resources/<int:req_id>/update", methods=["POST"])
@login_required
def update_resource(req_id):
    r = ResourceRequest.query.get_or_404(req_id)
    r.status = request.form.get("status", r.status)
    db.session.commit()
    flash("Resource updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=r.disaster_id))


@crisis_bp.route("/resources/<int:req_id>/delete", methods=["POST"])
@login_required
def delete_resource(req_id):
    r = ResourceRequest.query.get_or_404(req_id)
    did = r.disaster_id
    db.session.delete(r)
    db.session.commit()
    flash("Resource request removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── EVACUATION ROUTES ─────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/routes/add", methods=["POST"])
@login_required
def add_route(disaster_id):
    db.session.add(EvacuationRoute(
        disaster_id=disaster_id,
        route_name=request.form.get("route_name", "").strip(),
        origin=request.form.get("origin", "").strip(),
        destination=request.form.get("destination", "").strip(),
        distance_km=float(request.form.get("distance_km", 0) or 0),
        estimated_time=request.form.get("estimated_time", "").strip(),
        status=request.form.get("status", "open"),
        notes=request.form.get("notes", "").strip(),
    ))
    db.session.commit()
    flash("Evacuation route added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/routes/<int:route_id>/update", methods=["POST"])
@login_required
def update_route(route_id):
    r = EvacuationRoute.query.get_or_404(route_id)
    r.status = request.form.get("status", r.status)
    db.session.commit()
    flash("Route updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=r.disaster_id))


@crisis_bp.route("/routes/<int:route_id>/delete", methods=["POST"])
@login_required
def delete_route(route_id):
    r = EvacuationRoute.query.get_or_404(route_id)
    did = r.disaster_id
    db.session.delete(r)
    db.session.commit()
    flash("Route removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── RELIEF SUPPLIES ───────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/supplies/add", methods=["POST"])
@login_required
def add_supply(disaster_id):
    db.session.add(ReliefSupply(
        disaster_id=disaster_id,
        item_name=request.form.get("item_name", "").strip(),
        quantity=int(request.form.get("quantity", 0) or 0),
        unit=request.form.get("unit", "").strip(),
        donated_by=request.form.get("donated_by", "").strip(),
        status=request.form.get("status", "available"),
    ))
    db.session.commit()
    flash("Supply item added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/supplies/<int:supply_id>/update", methods=["POST"])
@login_required
def update_supply(supply_id):
    s = ReliefSupply.query.get_or_404(supply_id)
    s.quantity = int(request.form.get("quantity", s.quantity) or 0)
    s.status   = request.form.get("status", s.status)
    db.session.commit()
    flash("Supply updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=s.disaster_id))


@crisis_bp.route("/supplies/<int:supply_id>/delete", methods=["POST"])
@login_required
def delete_supply(supply_id):
    s = ReliefSupply.query.get_or_404(supply_id)
    did = s.disaster_id
    db.session.delete(s)
    db.session.commit()
    flash("Supply removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))


# ── VOLUNTEERS ────────────────────────────────────────────────────────────────

@crisis_bp.route("/<int:disaster_id>/volunteers/register", methods=["POST"])
@login_required
def register_volunteer(disaster_id):
    if Volunteer.query.filter_by(disaster_id=disaster_id, user_id=current_user.id).first():
        flash("You are already registered.", "warning")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))
    db.session.add(Volunteer(
        user_id=current_user.id, disaster_id=disaster_id,
        skills=request.form.get("skills", "").strip(),
        availability=request.form.get("availability", "").strip(),
        notes=request.form.get("notes", "").strip(),
    ))
    db.session.commit()
    flash("Volunteer registration submitted.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@crisis_bp.route("/volunteers/<int:vol_id>/update", methods=["POST"])
@login_required
def update_volunteer(vol_id):
    v = Volunteer.query.get_or_404(vol_id)
    if current_user.role not in ("admin", "responder"):
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=v.disaster_id))
    v.status = request.form.get("status", v.status)
    db.session.commit()
    flash("Volunteer status updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=v.disaster_id))


@crisis_bp.route("/volunteers/<int:vol_id>/delete", methods=["POST"])
@login_required
def delete_volunteer(vol_id):
    v = Volunteer.query.get_or_404(vol_id)
    did = v.disaster_id
    if v.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=did))
    db.session.delete(v)
    db.session.commit()
    flash("Volunteer registration removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=did))
