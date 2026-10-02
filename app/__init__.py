# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.models import db
from routes.admin import admin_bp
from routes.batch import batch_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    app.config["SECRET_KEY"] = app.config.get("SECRET_KEY") or os.environ.get("SECRET_KEY", "netassist-dev-secret-change-me")

    # Allow the local frontend to communicate with Flask.
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5500",
                    "http://localhost:5500",
                ]
            }
        }
    )

    db.init_app(app)

    from routes.chat import chat_bp
    from routes.reviews import reviews_bp
    from routes.escalations import escalations_bp
    from routes.auth import auth_bp
    from routes.customers import customers_bp
    from services.auth import init_auth

    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
    app.register_blueprint(escalations_bp, url_prefix="/api/escalations")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(batch_bp, url_prefix="/api/batch")

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    init_auth(app)

    return app