"""Videos API — list, manage, download, and upload voice for generated videos."""

import os
from flask import Blueprint, request, jsonify, send_file

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


@videos_bp.route("/<video_id>/download/<file_type>", methods=["GET"])
def download_video_file(video_id, file_type):
    """Download a video file. file_type: video | video_no_subs | thumbnail | audio | subtitle

    Checks both the original path and /app/downloads (web volume) for the file.
    """
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    # Map file type to video model path and downloads folder filename
    path_map = {
        "video": (video.final_video_path, "video.mp4"),
        "thumbnail": (video.thumbnail_path, "thumbnail.png"),
        "audio": (video.audio_path, "audio.mp3"),
        "subtitle": (video.subtitle_path, "subtitle.srt"),
    }

    if file_type not in path_map:
        return jsonify({"error": f"Invalid file type '{file_type}'"}), 400

    original_path, downloads_name = path_map[file_type]

    # Try original path first (for local dev)
    if original_path and os.path.exists(original_path):
        return send_file(
            os.path.abspath(original_path),
            as_attachment=True,
            download_name=os.path.basename(original_path),
        )

    # Try /app/downloads (web volume on Railway)
    pipeline_id = video.pipeline_run_id

    # Fallback: look up pipeline from Phase 2 output if video was created before fix
    if not pipeline_id:
        from app.models.phase_result import PhaseResult
        phase_2 = PhaseResult.query.filter(
            PhaseResult.phase_number == 2,
            PhaseResult.output_data.isnot(None),
        ).all()
        for p2 in phase_2:
            if p2.output_data.get("video_id") == video_id:
                pipeline_id = p2.pipeline_run_id
                break

    if pipeline_id:
        downloads_path = f"/app/downloads/{pipeline_id}/{downloads_name}"
        if os.path.exists(downloads_path):
            return send_file(
                downloads_path,
                as_attachment=True,
                download_name=downloads_name,
            )

    return jsonify({"error": f"File not found for type '{file_type}'"}), 404


@videos_bp.route("/<video_id>/upload-voice", methods=["POST"])
def upload_voice(video_id):
    """Upload a manual voiceover to replace AI-generated audio.

    Accepts multipart form with 'audio' file field.
    Stores the file and optionally re-runs Phase 5+6.
    """
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided. Use 'audio' field."}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Save uploaded voice file
    from app.utils.file_manager import get_video_dir
    pipeline_run_id = video.pipeline_run_id or video.id
    video_dir = get_video_dir(pipeline_run_id)

    ext = os.path.splitext(audio_file.filename)[1] or ".mp3"
    voice_path = os.path.join(video_dir, f"manual_voice{ext}")
    audio_file.save(voice_path)

    # Update video record
    video.audio_path = voice_path
    db.session.commit()

    # Optionally re-run Phase 5 (video assembly) + Phase 6 (QA)
    rerun = request.form.get("rerun_assembly", "false").lower() == "true"
    task_id = None
    if rerun and video.pipeline_run_id:
        from worker.tasks import run_phase
        task = run_phase.delay(video.pipeline_run_id, 5)
        task_id = task.id

    return jsonify({
        "message": "Voice uploaded successfully",
        "audio_path": voice_path,
        "rerun_task_id": task_id,
        "video": video.to_dict(),
    })


@videos_bp.route("/<video_id>/delete", methods=["DELETE"])
def delete_video(video_id):
    """Delete a video and its assets."""
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    # Delete associated assets
    Asset.query.filter_by(video_id=video_id).delete()

    db.session.delete(video)
    db.session.commit()
    return jsonify({"message": "Video deleted"})
