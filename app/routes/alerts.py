from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.extensions import db, mail
from app.models import Disaster, EmergencyContact, AlertLog, AuditLog
from flask_mail import Message

alerts_bp = Blueprint("alerts", __name__)


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


# ── Emergency contacts ────────────────────────────────────────────────────────

@alerts_bp.route("/contacts")
@login_required
def contacts():
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()
    return render_template("alerts/index.html", contacts=contacts)


@alerts_bp.route("/contacts/add", methods=["POST"])
@login_required
def add_contact():
    name         = request.form.get("name", "").strip()
    phone        = request.form.get("phone", "").strip()
    email        = request.form.get("email", "").strip().lower()
    relation     = request.form.get("relation", "").strip()
    notify_sms   = bool(request.form.get("notify_sms"))
    notify_email = bool(request.form.get("notify_email", True))

    if not name:
        flash("Name is required.", "danger")
        return redirect(url_for("alerts.contacts"))

    contact = EmergencyContact(
        user_id=current_user.id,
        name=name, phone=phone, email=email,
        relation=relation, notify_sms=notify_sms, notify_email=notify_email,
    )
    db.session.add(contact)
    db.session.commit()
    _audit("ADD_CONTACT", f"Added contact: {name}")
    flash(f"Contact {name} added.", "success")
    return redirect(url_for("alerts.contacts"))


@alerts_bp.route("/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete_contact(contact_id):
    contact = EmergencyContact.query.get_or_404(contact_id)
    if contact.user_id != current_user.id:
        flash("Permission denied.", "danger")
        return redirect(url_for("alerts.contacts"))
    db.session.delete(contact)
    db.session.commit()
    _audit("DELETE_CONTACT", f"Deleted contact #{contact_id}")
    flash("Contact removed.", "info")
    return redirect(url_for("alerts.contacts"))


# ── Send alert ────────────────────────────────────────────────────────────────

@alerts_bp.route("/send/<int:disaster_id>", methods=["POST"])
@login_required
def send_alert(disaster_id):
    disaster = Disaster.query.get_or_404(disaster_id)
    contacts = EmergencyContact.query.filter_by(user_id=current_user.id).all()

    sent_count = 0
    for contact in contacts:
        if contact.notify_email and contact.email:
            _send_email_alert(contact, disaster)
            sent_count += 1
        if contact.notify_sms and contact.phone:
            _send_sms_alert(contact, disaster)
            sent_count += 1

    _audit("SEND_ALERT", f"Sent alerts for disaster #{disaster_id} to {sent_count} recipients")
    flash(f"Alerts dispatched to {sent_count} contact(s).", "success")
    return redirect(url_for("crisis.detail", disaster_id=disaster_id))


def _send_email_alert(contact, disaster):
    try:
        msg = Message(
            subject=f"[ALERT] {disaster.severity.upper()} — {disaster.title}",
            recipients=[contact.email],
            body=(
                f"Hello {contact.name},\n\n"
                f"A {disaster.severity} severity {disaster.disaster_type} has been reported.\n\n"
                f"Location: {disaster.location_name or f'{disaster.latitude}, {disaster.longitude}'}\n"
                f"Affected people: {disaster.affected_people}\n"
                f"Details: {disaster.description or 'No further details provided.'}\n\n"
                "Stay safe.\n— Disaster Crisis Hub"
            ),
        )
        mail.send(msg)
        log = AlertLog(disaster_id=disaster.id, sent_to=contact.email, method="email", status="sent")
    except Exception as e:
        log = AlertLog(disaster_id=disaster.id, sent_to=contact.email, method="email", status="failed")
    db.session.add(log)
    db.session.commit()


def _send_sms_alert(contact, disaster):
    try:
        from twilio.rest import Client
        from flask import current_app
        client = Client(
            current_app.config["TWILIO_ACCOUNT_SID"],
            current_app.config["TWILIO_AUTH_TOKEN"],
        )
        client.messages.create(
            body=(
                f"ALERT: {disaster.severity.upper()} {disaster.disaster_type} at "
                f"{disaster.location_name or 'unknown location'}. "
                f"Affected: {disaster.affected_people} people."
            ),
            from_=current_app.config["TWILIO_PHONE"],
            to=contact.phone,
        )
        log = AlertLog(disaster_id=disaster.id, sent_to=contact.phone, method="sms", status="sent")
    except Exception:
        log = AlertLog(disaster_id=disaster.id, sent_to=contact.phone, method="sms", status="failed")
    db.session.add(log)
    db.session.commit()
