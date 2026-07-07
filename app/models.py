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
