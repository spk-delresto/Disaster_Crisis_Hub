from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager


# ── 1. User ───────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.Enum("admin", "responder", "viewer"), default="viewer")
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    disasters      = db.relationship("Disaster", backref="creator", lazy=True)
    contacts       = db.relationship("EmergencyContact", backref="owner", lazy=True, cascade="all, delete-orphan")
    comments       = db.relationship("CrisisComment", backref="author", lazy=True)
    volunteers     = db.relationship("Volunteer", backref="user", lazy=True)
    announcements  = db.relationship("Announcement", backref="creator", lazy=True)
    resource_reqs  = db.relationship("ResourceRequest", backref="requester", lazy=True)
    timeline_events = db.relationship("IncidentTimeline", backref="reporter", lazy=True)
    feedback       = db.relationship("Feedback", backref="submitter", lazy=True)
    media          = db.relationship("CrisisMedia", backref="uploader", lazy=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── 2. Disaster (Crisis Report) ───────────────────────────────────────────────
disaster_categories = db.Table(
    "disaster_categories",
    db.Column("disaster_id", db.Integer, db.ForeignKey("disasters.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
)

class Disaster(db.Model):
    __tablename__ = "disasters"
    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text)
    disaster_type   = db.Column(db.Enum("flood","earthquake","fire","hurricane","landslide","tsunami","other"), nullable=False)
    severity        = db.Column(db.Enum("low","medium","high","critical"), default="medium")
    severity_score  = db.Column(db.Float)
    latitude        = db.Column(db.Numeric(9, 6), nullable=False)
    longitude       = db.Column(db.Numeric(9, 6), nullable=False)
    location_name   = db.Column(db.String(200))
    affected_people = db.Column(db.Integer, default=0)
    status          = db.Column(db.Enum("active","monitoring","resolved"), default="active")
    created_by      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts          = db.relationship("AlertLog", backref="disaster", lazy=True, cascade="all, delete-orphan")
    comments        = db.relationship("CrisisComment", backref="disaster", lazy=True, cascade="all, delete-orphan")
    categories      = db.relationship("Category", secondary=disaster_categories, backref="disasters")
    resource_reqs   = db.relationship("ResourceRequest", backref="disaster", lazy=True, cascade="all, delete-orphan")
    volunteers      = db.relationship("Volunteer", backref="disaster", lazy=True, cascade="all, delete-orphan")
    affected_areas  = db.relationship("AffectedArea", backref="disaster", lazy=True, cascade="all, delete-orphan")
    media           = db.relationship("CrisisMedia", backref="disaster", lazy=True, cascade="all, delete-orphan")
    supplies        = db.relationship("ReliefSupply", backref="disaster", lazy=True, cascade="all, delete-orphan")
    routes          = db.relationship("EvacuationRoute", backref="disaster", lazy=True, cascade="all, delete-orphan")
    timeline        = db.relationship("IncidentTimeline", backref="disaster", lazy=True, cascade="all, delete-orphan")
    feedback        = db.relationship("Feedback", backref="disaster", lazy=True)

    def to_geojson(self):
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(self.longitude), float(self.latitude)]},
            "properties": {
                "id": self.id, "title": self.title, "type": self.disaster_type,
                "severity": self.severity, "status": self.status,
                "affected": self.affected_people, "created_at": self.created_at.isoformat(),
            },
        }


# ── 3. Emergency Contact ──────────────────────────────────────────────────────
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


# ── 4. Alert Log ──────────────────────────────────────────────────────────────
class AlertLog(db.Model):
    __tablename__ = "alerts_log"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    sent_to     = db.Column(db.String(120), nullable=False)
    method      = db.Column(db.Enum("email", "sms"), nullable=False)
    status      = db.Column(db.Enum("sent", "failed", "pending"), default="pending")
    sent_at     = db.Column(db.DateTime, default=datetime.utcnow)


# ── 5. Audit Log ──────────────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = "audit_log"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action     = db.Column(db.String(100), nullable=False)
    detail     = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship("User", foreign_keys=[user_id])


# ── 6. Crisis Comment ─────────────────────────────────────────────────────────
class CrisisComment(db.Model):
    __tablename__ = "crisis_comments"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    comment     = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── 7. Category ───────────────────────────────────────────────────────────────
class Category(db.Model):
    __tablename__ = "categories"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    color       = db.Column(db.String(7), default="#3b82f6")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ── 8. Resource Request ───────────────────────────────────────────────────────
class ResourceRequest(db.Model):
    __tablename__ = "resource_requests"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resource    = db.Column(db.String(200), nullable=False)
    quantity    = db.Column(db.Integer, default=1)
    unit        = db.Column(db.String(50))
    priority    = db.Column(db.Enum("low","medium","high","critical"), default="medium")
    status      = db.Column(db.Enum("pending","approved","fulfilled","cancelled"), default="pending")
    notes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── 9. Volunteer ──────────────────────────────────────────────────────────────
class Volunteer(db.Model):
    __tablename__ = "volunteers"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    disaster_id  = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    skills       = db.Column(db.Text)
    availability = db.Column(db.String(100))
    status       = db.Column(db.Enum("pending","approved","active","completed"), default="pending")
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ── 10. Announcement ──────────────────────────────────────────────────────────
class Announcement(db.Model):
    __tablename__ = "announcements"
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    priority   = db.Column(db.Enum("normal","urgent","critical"), default="normal")
    is_active  = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── 11. Affected Area ─────────────────────────────────────────────────────────
class AffectedArea(db.Model):
    __tablename__ = "affected_areas"
    id           = db.Column(db.Integer, primary_key=True)
    disaster_id  = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    area_name    = db.Column(db.String(200), nullable=False)
    population   = db.Column(db.Integer, default=0)
    damage_level = db.Column(db.Enum("minor","moderate","severe","destroyed"), default="moderate")
    notes        = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)


# ── 12. Crisis Media ──────────────────────────────────────────────────────────
class CrisisMedia(db.Model):
    __tablename__ = "crisis_media"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    media_type  = db.Column(db.Enum("image","video","document","link"), nullable=False)
    url         = db.Column(db.String(500), nullable=False)
    caption     = db.Column(db.String(300))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ── 13. Relief Supply ─────────────────────────────────────────────────────────
class ReliefSupply(db.Model):
    __tablename__ = "relief_supplies"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    item_name   = db.Column(db.String(200), nullable=False)
    quantity    = db.Column(db.Integer, default=0)
    unit        = db.Column(db.String(50))
    donated_by  = db.Column(db.String(200))
    status      = db.Column(db.Enum("available","distributed","depleted"), default="available")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── 14. Evacuation Route ──────────────────────────────────────────────────────
class EvacuationRoute(db.Model):
    __tablename__ = "evacuation_routes"
    id             = db.Column(db.Integer, primary_key=True)
    disaster_id    = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    route_name     = db.Column(db.String(200), nullable=False)
    origin         = db.Column(db.String(200), nullable=False)
    destination    = db.Column(db.String(200), nullable=False)
    distance_km    = db.Column(db.Float)
    estimated_time = db.Column(db.String(100))
    status         = db.Column(db.Enum("open","congested","closed"), default="open")
    notes          = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)


# ── 15. Incident Timeline ─────────────────────────────────────────────────────
class IncidentTimeline(db.Model):
    __tablename__ = "incident_timeline"
    id          = db.Column(db.Integer, primary_key=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=False)
    event_time  = db.Column(db.DateTime, nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# ── 16. Feedback ──────────────────────────────────────────────────────────────
class Feedback(db.Model):
    __tablename__ = "feedback"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    disaster_id = db.Column(db.Integer, db.ForeignKey("disasters.id"), nullable=True)
    subject     = db.Column(db.String(200), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    category    = db.Column(db.Enum("general","inaccurate_info","missing_resource","suggestion","other"), default="general")
    status      = db.Column(db.Enum("open","reviewed","resolved"), default="open")
    admin_reply = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

