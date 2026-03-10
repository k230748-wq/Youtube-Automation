"""Pipeline API — create, list, start, and manage video pipelines."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.pipeline_run import PipelineRun
from app.models.phase_result import PhaseResult
from app.models.approval import Approval
from app.models.learning import LearningLog
from app.orchestrator.engine import create_pipeline

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/", methods=["GET"])
def list_pipelines():
    status_filter = request.args.get("status")
    query = PipelineRun.query.order_by(PipelineRun.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page)
    return jsonify({
        "pipelines": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@pipeline_bp.route("/", methods=["POST"])
def create_new_pipeline():
    data = request.get_json()
    if not data or not data.get("channel_id"):
        return jsonify({"error": "channel_id is required"}), 400

    from app.models.channel import Channel
    channel = Channel.query.get(data["channel_id"])
    if not channel:
        return jsonify({"error": "Channel not found"}), 404

    pipeline = create_pipeline(
        channel_id=channel.id,
        niche=channel.niche,
        topic=data.get("topic"),
        config=data.get("config", {}),
    )

    if data.get("auto_start", True):
        from worker.tasks import run_pipeline
        run_pipeline.delay(pipeline.id)

    return jsonify(pipeline.to_dict()), 201


@pipeline_bp.route("/<pipeline_id>", methods=["GET"])
def get_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    phases = PhaseResult.query.filter_by(pipeline_run_id=pipeline_id).order_by(PhaseResult.phase_number).all()
    phases_data = []
    for p in phases:
        d = p.to_dict()
        if p.approval:
            d["approval"] = p.approval.to_dict()
        phases_data.append(d)

    return jsonify({**pipeline.to_dict(), "phases": phases_data})


@pipeline_bp.route("/<pipeline_id>/start", methods=["POST"])
def start_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    from worker.tasks import run_pipeline
    task = run_pipeline.delay(pipeline_id)
    return jsonify({"message": "Pipeline started", "pipeline_id": pipeline_id, "task_id": task.id})


@pipeline_bp.route("/<pipeline_id>/stop", methods=["POST"])
def stop_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    pipeline.status = "failed"
    pipeline.error_message = "Manually stopped by user"
    db.session.commit()
    return jsonify({"message": "Pipeline stopped", "pipeline_id": pipeline_id})


@pipeline_bp.route("/<pipeline_id>/restart_from/<int:phase_number>", methods=["POST"])
def restart_from_phase(pipeline_id, phase_number):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    from app.orchestrator.state import TOTAL_PHASES
    if phase_number < 1 or phase_number > TOTAL_PHASES:
        return jsonify({"error": f"Invalid phase number. Must be between 1 and {TOTAL_PHASES}"}), 400

    data = request.get_json() or {}
    if data.get("config_updates"):
        config = pipeline.config or {}
        config.update(data["config_updates"])
        pipeline.config = config

    Approval.query.filter(Approval.pipeline_run_id == pipeline_id, Approval.phase_number >= phase_number).delete()
    PhaseResult.query.filter(PhaseResult.pipeline_run_id == pipeline_id, PhaseResult.phase_number >= phase_number).delete()

    pipeline.current_phase = phase_number
    pipeline.status = "pending"
    pipeline.error_message = None
    pipeline.completed_at = None
    db.session.commit()

    from worker.tasks import run_pipeline
    task = run_pipeline.delay(pipeline_id)
    return jsonify({"message": f"Pipeline restarting from phase {phase_number}", "pipeline_id": pipeline_id, "task_id": task.id})


@pipeline_bp.route("/<pipeline_id>/logs", methods=["GET"])
def get_pipeline_logs(pipeline_id):
    """Get learning logs for a pipeline run."""
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    logs = LearningLog.query.filter_by(
        pipeline_run_id=pipeline_id
    ).order_by(LearningLog.phase_number).all()

    return jsonify({
        "pipeline_id": pipeline_id,
        "logs": [l.to_dict() for l in logs],
    })


@pipeline_bp.route("/diagnostics/assets", methods=["GET"])
def list_worker_assets():
    """Diagnostic: list contents of /app/assets on worker."""
    pipeline_id = request.args.get("pipeline_id")
    from worker.tasks import list_assets
    task = list_assets.delay(pipeline_id)
    return jsonify({"task_id": task.id, "pipeline_id": pipeline_id})


@pipeline_bp.route("/<pipeline_id>/sync", methods=["POST"])
def sync_pipeline_files(pipeline_id):
    """Manually sync completed pipeline files to web service for download."""
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    if pipeline.status != "completed":
        return jsonify({"error": "Pipeline must be completed to sync files"}), 400

    from worker.tasks import sync_files
    task = sync_files.delay(pipeline_id)
    return jsonify({
        "message": "File sync started",
        "pipeline_id": pipeline_id,
        "task_id": task.id,
    })


@pipeline_bp.route("/<pipeline_id>", methods=["DELETE"])
def delete_pipeline(pipeline_id):
    """Delete a pipeline and its associated video/assets."""
    import os
    import shutil
    from app.models.video import Video
    from app.models.asset import Asset
    from config.settings import settings

    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    # Find associated video from Phase 2 output
    video_id = None
    phase_2 = PhaseResult.query.filter_by(pipeline_run_id=pipeline_id, phase_number=2).first()
    if phase_2 and phase_2.output_data:
        video_id = phase_2.output_data.get("video_id")

    # Delete associated video and its assets
    if video_id:
        Asset.query.filter_by(video_id=video_id).delete()
        Video.query.filter_by(id=video_id).delete()

    # Delete phase results, approvals, and learning logs
    PhaseResult.query.filter_by(pipeline_run_id=pipeline_id).delete()
    Approval.query.filter_by(pipeline_run_id=pipeline_id).delete()
    LearningLog.query.filter_by(pipeline_run_id=pipeline_id).delete()

    # Delete asset files from disk
    asset_dir = os.path.join(settings.ASSETS_DIR, pipeline_id)
    if os.path.exists(asset_dir):
        shutil.rmtree(asset_dir, ignore_errors=True)

    # Delete the pipeline
    db.session.delete(pipeline)
    db.session.commit()

    return jsonify({"message": "Pipeline deleted", "pipeline_id": pipeline_id})
