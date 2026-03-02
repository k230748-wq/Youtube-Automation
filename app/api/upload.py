"""Upload API — upload videos to YouTube."""

import os
from flask import Blueprint, request, jsonify

from app import db
from app.models.video import Video

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/<video_id>/youtube", methods=["POST"])
def upload_to_youtube(video_id):
    """Upload a video to YouTube.

    Requires YouTube OAuth token (run youtube_upload_client.authorize() first).

    Optional JSON body:
        - privacy_status: 'private' (default), 'unlisted', or 'public'
        - category_id: YouTube category ID (default '22' = People & Blogs)
    """
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    if not video.final_video_path or not os.path.exists(video.final_video_path):
        return jsonify({"error": "No video file found — run pipeline first"}), 400

    if not video.title:
        return jsonify({"error": "Video has no title"}), 400

    data = request.get_json() or {}
    privacy_status = data.get("privacy_status", "private")
    category_id = data.get("category_id", "22")

    try:
        from app.integrations.youtube_upload_client import upload_video

        result = upload_video(
            video_path=video.final_video_path,
            title=video.title,
            description=video.description or "",
            tags=video.tags_list or [],
            category_id=category_id,
            privacy_status=privacy_status,
            thumbnail_path=video.thumbnail_path,
        )

        # Update video status
        video.status = "uploaded"
        db.session.commit()

        return jsonify({
            "message": "Video uploaded to YouTube",
            "youtube": result,
            "video": video.to_dict(),
        })

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500
