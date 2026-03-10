"""Internal API — worker-to-web file transfers."""

import os
from flask import Blueprint, request, jsonify

internal_bp = Blueprint("internal", __name__)

# Downloads directory mounted as volume on web service
DOWNLOADS_DIR = "/app/downloads"


@internal_bp.route("/upload/<pipeline_id>/<file_type>", methods=["POST"])
def upload_file(pipeline_id, file_type):
    """Receive file upload from worker service.

    file_type: 'video', 'audio', 'subtitle', 'thumbnail'
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Create pipeline directory
    pipeline_dir = os.path.join(DOWNLOADS_DIR, pipeline_id)
    os.makedirs(pipeline_dir, exist_ok=True)

    # Determine filename based on type
    ext_map = {
        "video": ".mp4",
        "video_no_subs": "_no_subs.mp4",
        "audio": ".mp3",
        "subtitle": ".srt",
        "thumbnail": ".png",
    }

    ext = ext_map.get(file_type, "")
    if not ext:
        ext = os.path.splitext(file.filename)[1] or ".bin"

    filename = f"{file_type}{ext}"
    file_path = os.path.join(pipeline_dir, filename)

    file.save(file_path)

    return jsonify({
        "message": "File uploaded",
        "path": file_path,
        "size": os.path.getsize(file_path),
    })


@internal_bp.route("/files/<pipeline_id>", methods=["GET"])
def list_files(pipeline_id):
    """List files available for a pipeline."""
    pipeline_dir = os.path.join(DOWNLOADS_DIR, pipeline_id)
    if not os.path.exists(pipeline_dir):
        return jsonify({"files": []})

    files = []
    for f in os.listdir(pipeline_dir):
        path = os.path.join(pipeline_dir, f)
        files.append({
            "name": f,
            "path": path,
            "size": os.path.getsize(path),
        })

    return jsonify({"files": files})
