from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager


# ── User ──────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)   # bcrypt hash
    role       = db.Column(db.Enum("admin", "responder", "viewer"), default="viewer")
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    disasters = db.relationship("Disaster", backref="creator", lazy=True)
    contacts  = db.relationship("EmergencyContact", backref="owner", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Disaster ──────────────────────────────────────────────────────────────────

class Disaster(db.Model):
    __tablename__ = "disasters"

    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text)
    disaster_type  = db.Column(db.Enum("flood","earthquake","fire","hurricane","landslide","tsunami","other"), nullable=False)
    severity       = db.Column(db.Enum("low","medium","high","critical"), default="medium")
    severity_score = db.Column(db.Float)         # ML prediction 0-1
    latitude       = db.Column(db.Numeric(9, 6), nullable=False)
    longitude      = db.Column(db.Numeric(9, 6), nullable=False)
    location_name  = db.Column(db.String(200))
    affected_people = db.Column(db.Integer, default=0)
    status         = db.Column(db.Enum("active","monitoring","resolved"), default="active")
    created_by     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts = db.relationship("AlertLog", backref="disaster", lazy=True)

    @property
    def severity_label(self):
        labels = {"low": "🟢 Low", "medium": "🟡 Medium", "high": "🟠 High", "critical": "🔴 Critical"}
        return labels.get(self.severity, self.severity)

    def to_geojson(self):
        """Return a GeoJSON Feature for the Leaflet map."""
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(self.longitude), float(self.latitude)]},
            "properties": {
                "id": self.id,
                "title": self.title,
                "type": self.disaster_type,
                "severity": self.severity,
                "status": self.status,
                "affected": self.affected_people,
                "created_at": self.created_at.isoformat(),
            },
        }

# ── Emergency contact ─────────────────────────────────────────────────────────

class EmergencyContact(db.Model):
    __tablename__ = "emergency_contacts"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    phone        = db.Column(db.String(20))
    email        = db.Column(db.String(120))
    relation     = db.Column(db.String(50))
    notify_sms   = db.Column(db.Boolean, default=False)
    notify_email = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ── Alert log ─────────────────────────────────────────────────────────────────

class AlertLog(db.Model):
    __tablename__ = "alerts_log"

    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    sent_to     = db.Column(db.String(120), nullable=False)
    method      = db.Column(db.Enum("email", "sms"), nullable=False)
    status      = db.Column(db.Enum("sent", "failed", "pending"), default="pending")
    sent_at     = db.Column(db.DateTime, default=datetime.utcnow)


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
