from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config.from_object("config.settings.Settings")

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    migrate.init_app(app, db)

    # Register models
    from app.models import (  # noqa: F401
        pipeline_run,
        phase_result,
        prompt_template,
        approval,
        learning,
        phase_toggle,
        channel,
        video,
        idea,
        asset,
    )

    # Register API blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # Health check
    @app.route("/health")
    def health():
        return {"status": "ok", "service": "youtube-automation"}

    return app
