"""Task Status API — poll Celery task progress."""

from flask import Blueprint, jsonify

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Poll status of a Celery async task."""
    try:
        from worker.celery_app import celery
        result = celery.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": result.status,
        }

        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = str(result.result)

        return jsonify(response)
    except ImportError:
        return jsonify({"error": "Celery not available — run in Docker"}), 503
