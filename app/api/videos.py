"""Videos API — list and manage generated videos."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.video import Video
from app.models.asset import Asset

videos_bp = Blueprint("videos", __name__)


@videos_bp.route("/", methods=["GET"])
def list_videos():
    channel_id = request.args.get("channel_id")
    query = Video.query.order_by(Video.created_at.desc())
    if channel_id:
        query = query.filter_by(channel_id=channel_id)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        "videos": [v.to_dict() for v in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@videos_bp.route("/<video_id>", methods=["GET"])
def get_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    assets = Asset.query.filter_by(video_id=video_id).all()
    return jsonify({
        **video.to_dict(),
        "assets": [a.to_dict() for a in assets],
    })


@videos_bp.route("/<video_id>", methods=["PATCH"])
def update_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    data = request.get_json() or {}
    for field in ["title", "description", "script_text", "tags_list", "status"]:
        if field in data:
            setattr(video, field, data[field])

    db.session.commit()
    return jsonify(video.to_dict())
