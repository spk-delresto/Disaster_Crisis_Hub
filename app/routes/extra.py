from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    CrisisComment, Category, ResourceRequest, Volunteer,
    Announcement, AffectedArea, CrisisMedia, ReliefSupply,
    EvacuationRoute, IncidentTimeline, Feedback, Disaster, AuditLog
)
from datetime import datetime

extra_bp = Blueprint("extra", __name__)


def _audit(action, detail=None):
    log = AuditLog(
        user_id=current_user.id,
        action=action, detail=detail,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:300],
    )
    db.session.add(log)
    db.session.commit()


# ══════════════════════════════════════════════════════════════════════════════
# 6. CRISIS COMMENTS
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/comments/add", methods=["POST"])
@login_required
def add_comment(disaster_id):
    comment_text = request.form.get("comment", "").strip()
    if not comment_text:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))
    comment = CrisisComment(disaster_id=disaster_id, user_id=current_user.id, comment=comment_text)
    db.session.add(comment)
    db.session.commit()
    _audit("ADD_COMMENT", f"Comment on disaster #{disaster_id}")
    flash("Comment added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@extra_bp.route("/comments/<int:comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(comment_id):
    comment = CrisisComment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=comment.disaster_id))
    comment.comment = request.form.get("comment", comment.comment).strip()
    db.session.commit()
    flash("Comment updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=comment.disaster_id))


@extra_bp.route("/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = CrisisComment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=comment.disaster_id))
    disaster_id = comment.disaster_id
    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "info")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 7. CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/categories")
@login_required
def categories():
    cats = Category.query.order_by(Category.name).all()
    return render_template("extra/categories.html", categories=cats)


@extra_bp.route("/categories/add", methods=["POST"])
@login_required
def add_category():
    if current_user.role not in ("admin", "responder"):
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.categories"))
    name  = request.form.get("name", "").strip()
    desc  = request.form.get("description", "").strip()
    color = request.form.get("color", "#3b82f6")
    if not name:
        flash("Category name required.", "danger")
        return redirect(url_for("extra.categories"))
    cat = Category(name=name, description=desc, color=color)
    db.session.add(cat)
    db.session.commit()
    _audit("ADD_CATEGORY", f"Created category: {name}")
    flash(f"Category '{name}' created.", "success")
    return redirect(url_for("extra.categories"))


@extra_bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@login_required
def edit_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    cat.name        = request.form.get("name", cat.name).strip()
    cat.description = request.form.get("description", cat.description)
    cat.color       = request.form.get("color", cat.color)
    db.session.commit()
    flash("Category updated.", "success")
    return redirect(url_for("extra.categories"))


@extra_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
def delete_category(cat_id):
    if current_user.role != "admin":
        flash("Admin only.", "danger")
        return redirect(url_for("extra.categories"))
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("extra.categories"))


# ══════════════════════════════════════════════════════════════════════════════
# 8. RESOURCE REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/resources")
@login_required
def resources(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    reqs = ResourceRequest.query.filter_by(disaster_id=disaster_id).order_by(ResourceRequest.created_at.desc()).all()
    return render_template("extra/resources.html", disaster=disaster, reqs=reqs)


@extra_bp.route("/crisis/<int:disaster_id>/resources/add", methods=["POST"])
@login_required
def add_resource(disaster_id):
    req = ResourceRequest(
        disaster_id=disaster_id, user_id=current_user.id,
        resource=request.form.get("resource", "").strip(),
        quantity=int(request.form.get("quantity", 1) or 1),
        unit=request.form.get("unit", "").strip(),
        priority=request.form.get("priority", "medium"),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(req)
    db.session.commit()
    _audit("ADD_RESOURCE_REQUEST", f"Resource request for disaster #{disaster_id}")
    flash("Resource request submitted.", "success")
    return redirect(url_for("extra.resources", disaster_id=disaster_id))


@extra_bp.route("/resources/<int:req_id>/update", methods=["POST"])
@login_required
def update_resource(req_id):
    req = ResourceRequest.query.get_or_404(req_id)
    req.status = request.form.get("status", req.status)
    db.session.commit()
    flash("Resource status updated.", "success")
    return redirect(url_for("extra.resources", disaster_id=req.disaster_id))


@extra_bp.route("/resources/<int:req_id>/delete", methods=["POST"])
@login_required
def delete_resource(req_id):
    req = ResourceRequest.query.get_or_404(req_id)
    disaster_id = req.disaster_id
    db.session.delete(req)
    db.session.commit()
    flash("Resource request removed.", "info")
    return redirect(url_for("extra.resources", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 9. VOLUNTEERS
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/volunteers")
@login_required
def volunteers(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    vols = Volunteer.query.filter_by(disaster_id=disaster_id).all()
    my_reg = Volunteer.query.filter_by(disaster_id=disaster_id, user_id=current_user.id).first()
    return render_template("extra/volunteers.html", disaster=disaster, volunteers=vols, my_reg=my_reg)


@extra_bp.route("/crisis/<int:disaster_id>/volunteers/register", methods=["POST"])
@login_required
def register_volunteer(disaster_id):
    existing = Volunteer.query.filter_by(disaster_id=disaster_id, user_id=current_user.id).first()
    if existing:
        flash("You are already registered for this crisis.", "warning")
        return redirect(url_for("extra.volunteers", disaster_id=disaster_id))
    vol = Volunteer(
        user_id=current_user.id, disaster_id=disaster_id,
        skills=request.form.get("skills", "").strip(),
        availability=request.form.get("availability", "").strip(),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(vol)
    db.session.commit()
    _audit("VOLUNTEER_REGISTER", f"Registered for disaster #{disaster_id}")
    flash("Volunteer registration submitted.", "success")
    return redirect(url_for("extra.volunteers", disaster_id=disaster_id))


@extra_bp.route("/volunteers/<int:vol_id>/update", methods=["POST"])
@login_required
def update_volunteer(vol_id):
    vol = Volunteer.query.get_or_404(vol_id)
    if current_user.role not in ("admin", "responder"):
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.volunteers", disaster_id=vol.disaster_id))
    vol.status = request.form.get("status", vol.status)
    db.session.commit()
    flash("Volunteer status updated.", "success")
    return redirect(url_for("extra.volunteers", disaster_id=vol.disaster_id))


@extra_bp.route("/volunteers/<int:vol_id>/delete", methods=["POST"])
@login_required
def delete_volunteer(vol_id):
    vol = Volunteer.query.get_or_404(vol_id)
    disaster_id = vol.disaster_id
    if vol.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.volunteers", disaster_id=disaster_id))
    db.session.delete(vol)
    db.session.commit()
    flash("Volunteer registration removed.", "info")
    return redirect(url_for("extra.volunteers", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 10. ANNOUNCEMENTS
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/announcements")
@login_required
def announcements():
    anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template("extra/announcements.html", announcements=anns)


@extra_bp.route("/announcements/add", methods=["POST"])
@login_required
def add_announcement():
    if current_user.role not in ("admin", "responder"):
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.announcements"))
    ann = Announcement(
        title=request.form.get("title", "").strip(),
        content=request.form.get("content", "").strip(),
        priority=request.form.get("priority", "normal"),
        created_by=current_user.id,
    )
    db.session.add(ann)
    db.session.commit()
    _audit("ADD_ANNOUNCEMENT", f"Created: {ann.title}")
    flash("Announcement published.", "success")
    return redirect(url_for("extra.announcements"))


@extra_bp.route("/announcements/<int:ann_id>/edit", methods=["POST"])
@login_required
def edit_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    if ann.created_by != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.announcements"))
    ann.title    = request.form.get("title", ann.title).strip()
    ann.content  = request.form.get("content", ann.content).strip()
    ann.priority = request.form.get("priority", ann.priority)
    ann.is_active = request.form.get("is_active") == "on"
    db.session.commit()
    flash("Announcement updated.", "success")
    return redirect(url_for("extra.announcements"))


@extra_bp.route("/announcements/<int:ann_id>/delete", methods=["POST"])
@login_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    if ann.created_by != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.announcements"))
    db.session.delete(ann)
    db.session.commit()
    flash("Announcement deleted.", "info")
    return redirect(url_for("extra.announcements"))


# ══════════════════════════════════════════════════════════════════════════════
# 11. AFFECTED AREAS
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/areas/add", methods=["POST"])
@login_required
def add_area(disaster_id):
    area = AffectedArea(
        disaster_id=disaster_id,
        area_name=request.form.get("area_name", "").strip(),
        population=int(request.form.get("population", 0) or 0),
        damage_level=request.form.get("damage_level", "moderate"),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(area)
    db.session.commit()
    flash("Affected area added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@extra_bp.route("/areas/<int:area_id>/edit", methods=["POST"])
@login_required
def edit_area(area_id):
    area = AffectedArea.query.get_or_404(area_id)
    area.area_name   = request.form.get("area_name", area.area_name).strip()
    area.population  = int(request.form.get("population", area.population) or 0)
    area.damage_level = request.form.get("damage_level", area.damage_level)
    area.notes       = request.form.get("notes", area.notes)
    db.session.commit()
    flash("Affected area updated.", "success")
    return redirect(url_for("crisis.detail", disaster_id=area.disaster_id))


@extra_bp.route("/areas/<int:area_id>/delete", methods=["POST"])
@login_required
def delete_area(area_id):
    area = AffectedArea.query.get_or_404(area_id)
    disaster_id = area.disaster_id
    db.session.delete(area)
    db.session.commit()
    flash("Affected area removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 12. CRISIS MEDIA
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/media/add", methods=["POST"])
@login_required
def add_media(disaster_id):
    media = CrisisMedia(
        disaster_id=disaster_id, user_id=current_user.id,
        media_type=request.form.get("media_type", "link"),
        url=request.form.get("url", "").strip(),
        caption=request.form.get("caption", "").strip(),
    )
    db.session.add(media)
    db.session.commit()
    flash("Media added.", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


@extra_bp.route("/media/<int:media_id>/delete", methods=["POST"])
@login_required
def delete_media(media_id):
    media = CrisisMedia.query.get_or_404(media_id)
    disaster_id = media.disaster_id
    if media.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("crisis.detail", disaster_id=disaster_id))
    db.session.delete(media)
    db.session.commit()
    flash("Media removed.", "info")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 13. RELIEF SUPPLIES
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/supplies")
@login_required
def supplies(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    items = ReliefSupply.query.filter_by(disaster_id=disaster_id).all()
    return render_template("extra/supplies.html", disaster=disaster, supplies=items)


@extra_bp.route("/crisis/<int:disaster_id>/supplies/add", methods=["POST"])
@login_required
def add_supply(disaster_id):
    supply = ReliefSupply(
        disaster_id=disaster_id,
        item_name=request.form.get("item_name", "").strip(),
        quantity=int(request.form.get("quantity", 0) or 0),
        unit=request.form.get("unit", "").strip(),
        donated_by=request.form.get("donated_by", "").strip(),
        status=request.form.get("status", "available"),
    )
    db.session.add(supply)
    db.session.commit()
    flash("Supply item added.", "success")
    return redirect(url_for("extra.supplies", disaster_id=disaster_id))


@extra_bp.route("/supplies/<int:supply_id>/update", methods=["POST"])
@login_required
def update_supply(supply_id):
    supply = ReliefSupply.query.get_or_404(supply_id)
    supply.quantity = int(request.form.get("quantity", supply.quantity) or 0)
    supply.status   = request.form.get("status", supply.status)
    db.session.commit()
    flash("Supply updated.", "success")
    return redirect(url_for("extra.supplies", disaster_id=supply.disaster_id))


@extra_bp.route("/supplies/<int:supply_id>/delete", methods=["POST"])
@login_required
def delete_supply(supply_id):
    supply = ReliefSupply.query.get_or_404(supply_id)
    disaster_id = supply.disaster_id
    db.session.delete(supply)
    db.session.commit()
    flash("Supply removed.", "info")
    return redirect(url_for("extra.supplies", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 14. EVACUATION ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/routes")
@login_required
def evac_routes(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    routes = EvacuationRoute.query.filter_by(disaster_id=disaster_id).all()
    return render_template("extra/evac_routes.html", disaster=disaster, routes=routes)


@extra_bp.route("/crisis/<int:disaster_id>/routes/add", methods=["POST"])
@login_required
def add_route(disaster_id):
    route = EvacuationRoute(
        disaster_id=disaster_id,
        route_name=request.form.get("route_name", "").strip(),
        origin=request.form.get("origin", "").strip(),
        destination=request.form.get("destination", "").strip(),
        distance_km=float(request.form.get("distance_km", 0) or 0),
        estimated_time=request.form.get("estimated_time", "").strip(),
        status=request.form.get("status", "open"),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(route)
    db.session.commit()
    flash("Evacuation route added.", "success")
    return redirect(url_for("extra.evac_routes", disaster_id=disaster_id))


@extra_bp.route("/routes/<int:route_id>/update", methods=["POST"])
@login_required
def update_route(route_id):
    route = EvacuationRoute.query.get_or_404(route_id)
    route.status = request.form.get("status", route.status)
    route.notes  = request.form.get("notes", route.notes)
    db.session.commit()
    flash("Route updated.", "success")
    return redirect(url_for("extra.evac_routes", disaster_id=route.disaster_id))


@extra_bp.route("/routes/<int:route_id>/delete", methods=["POST"])
@login_required
def delete_route(route_id):
    route = EvacuationRoute.query.get_or_404(route_id)
    disaster_id = route.disaster_id
    db.session.delete(route)
    db.session.commit()
    flash("Route removed.", "info")
    return redirect(url_for("extra.evac_routes", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 15. INCIDENT TIMELINE
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/crisis/<int:disaster_id>/timeline")
@login_required
def timeline(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    events = IncidentTimeline.query.filter_by(disaster_id=disaster_id).order_by(IncidentTimeline.event_time.desc()).all()
    return render_template("extra/timeline.html", disaster=disaster, events=events)


@extra_bp.route("/crisis/<int:disaster_id>/timeline/add", methods=["POST"])
@login_required
def add_timeline(disaster_id):
    event_time_str = request.form.get("event_time", "")
    try:
        event_time = datetime.strptime(event_time_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        event_time = datetime.utcnow()
    event = IncidentTimeline(
        disaster_id=disaster_id, created_by=current_user.id,
        event_time=event_time,
        title=request.form.get("title", "").strip(),
        description=request.form.get("description", "").strip(),
    )
    db.session.add(event)
    db.session.commit()
    flash("Timeline event added.", "success")
    return redirect(url_for("extra.timeline", disaster_id=disaster_id))


@extra_bp.route("/timeline/<int:event_id>/edit", methods=["POST"])
@login_required
def edit_timeline(event_id):
    event = IncidentTimeline.query.get_or_404(event_id)
    if event.created_by != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.timeline", disaster_id=event.disaster_id))
    event.title       = request.form.get("title", event.title).strip()
    event.description = request.form.get("description", event.description)
    db.session.commit()
    flash("Timeline event updated.", "success")
    return redirect(url_for("extra.timeline", disaster_id=event.disaster_id))


@extra_bp.route("/timeline/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_timeline(event_id):
    event = IncidentTimeline.query.get_or_404(event_id)
    disaster_id = event.disaster_id
    if event.created_by != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.timeline", disaster_id=disaster_id))
    db.session.delete(event)
    db.session.commit()
    flash("Timeline event deleted.", "info")
    return redirect(url_for("extra.timeline", disaster_id=disaster_id))


# ══════════════════════════════════════════════════════════════════════════════
# 16. FEEDBACK
# ══════════════════════════════════════════════════════════════════════════════

@extra_bp.route("/feedback")
@login_required
def feedback_list():
    if current_user.role == "admin":
        items = Feedback.query.order_by(Feedback.created_at.desc()).all()
    else:
        items = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
    return render_template("extra/feedback.html", feedback_items=items)


@extra_bp.route("/feedback/add", methods=["POST"])
@login_required
def add_feedback():
    fb = Feedback(
        user_id=current_user.id,
        disaster_id=request.form.get("disaster_id") or None,
        subject=request.form.get("subject", "").strip(),
        message=request.form.get("message", "").strip(),
        category=request.form.get("category", "general"),
    )
    db.session.add(fb)
    db.session.commit()
    flash("Feedback submitted. Thank you!", "success")
    return redirect(url_for("extra.feedback_list"))


@extra_bp.route("/feedback/<int:fb_id>/reply", methods=["POST"])
@login_required
def reply_feedback(fb_id):
    if current_user.role != "admin":
        flash("Admin only.", "danger")
        return redirect(url_for("extra.feedback_list"))
    fb = Feedback.query.get_or_404(fb_id)
    fb.admin_reply = request.form.get("admin_reply", "").strip()
    fb.status      = request.form.get("status", fb.status)
    db.session.commit()
    flash("Reply saved.", "success")
    return redirect(url_for("extra.feedback_list"))


@extra_bp.route("/feedback/<int:fb_id>/delete", methods=["POST"])
@login_required
def delete_feedback(fb_id):
    fb = Feedback.query.get_or_404(fb_id)
    if fb.user_id != current_user.id and current_user.role != "admin":
        flash("Permission denied.", "danger")
        return redirect(url_for("extra.feedback_list"))
    db.session.delete(fb)
    db.session.commit()
    flash("Feedback deleted.", "info")
    return redirect(url_for("extra.feedback_list"))
