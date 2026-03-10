"""Main API blueprint — registers all route modules."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

from app.api.pipeline import pipeline_bp
from app.api.approvals import approvals_bp
from app.api.channels import channels_bp
from app.api.videos import videos_bp
from app.api.ideas import ideas_bp
from app.api.assets import assets_bp
from app.api.phase_toggles import toggles_bp
from app.api.tasks import tasks_bp
from app.api.upload import upload_bp
from app.api.internal import internal_bp

api_bp.register_blueprint(pipeline_bp, url_prefix="/pipelines")
api_bp.register_blueprint(approvals_bp, url_prefix="/approvals")
api_bp.register_blueprint(channels_bp, url_prefix="/channels")
api_bp.register_blueprint(videos_bp, url_prefix="/videos")
api_bp.register_blueprint(ideas_bp, url_prefix="/ideas")
api_bp.register_blueprint(assets_bp, url_prefix="/assets")
api_bp.register_blueprint(toggles_bp, url_prefix="/phase-toggles")
api_bp.register_blueprint(tasks_bp, url_prefix="/tasks")
api_bp.register_blueprint(upload_bp, url_prefix="/upload")
api_bp.register_blueprint(internal_bp, url_prefix="/internal")
