"""Main API blueprint — registers all route modules."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

from app.api.pipeline import pipeline_bp
from app.api.approvals import approvals_bp
from app.api.channels import channels_bp
from app.api.videos import videos_bp

api_bp.register_blueprint(pipeline_bp, url_prefix="/pipelines")
api_bp.register_blueprint(approvals_bp, url_prefix="/approvals")
api_bp.register_blueprint(channels_bp, url_prefix="/channels")
api_bp.register_blueprint(videos_bp, url_prefix="/videos")
