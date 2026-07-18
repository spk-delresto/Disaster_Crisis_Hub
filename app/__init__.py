from flask import Flask
from app.config import config
from app.extensions import db, login_manager, csrf, limiter, mail

def create_app(env="default"):
    app = Flask(__name__)
    app.config.from_object(config[env])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.crisis import crisis_bp
    from app.routes.alerts import alerts_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp
    from app.routes.extra import extra_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(crisis_bp, url_prefix="/crisis")
    app.register_blueprint(alerts_bp, url_prefix="/alerts")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(extra_bp)

    with app.app_context():
        db.create_all()

    return app
