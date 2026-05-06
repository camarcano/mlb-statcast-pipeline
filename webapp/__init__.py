import os

from flask import Flask, redirect, url_for
from flask_login import LoginManager

from webapp.db import close_db

login_manager = LoginManager()


def create_app(config_name="default"):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    config_map = {
        "default": "webapp.config.DevelopmentConfig",
        "development": "webapp.config.DevelopmentConfig",
        "production": "webapp.config.ProductionConfig",
    }
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    app.teardown_appcontext(close_db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return None

    from webapp.hitter import hitter_bp
    app.register_blueprint(hitter_bp, url_prefix="/hitter")

    from webapp.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/")
    def index():
        return redirect(url_for("hitter.leaderboard"))

    return app
