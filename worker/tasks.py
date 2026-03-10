"""Celery tasks — wraps pipeline phases for async execution."""

import structlog
from worker.celery_app import celery

logger = structlog.get_logger(__name__)


@celery.task(bind=True, name="worker.tasks.run_pipeline")
def run_pipeline(self, pipeline_run_id: str):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.start()
            logger.info("task.pipeline.done", pipeline_id=pipeline_run_id, result=result)
            return result
        except Exception as e:
            logger.error("task.pipeline.failed", pipeline_id=pipeline_run_id, error=str(e))
            raise


@celery.task(bind=True, name="worker.tasks.run_phase")
def run_phase(self, pipeline_run_id: str, phase_number: int):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.run_phase(phase_number)
            logger.info("task.phase.done", pipeline_id=pipeline_run_id, phase=phase_number)
            return result
        except Exception as e:
            logger.error("task.phase.failed", pipeline_id=pipeline_run_id, phase=phase_number, error=str(e))
            raise


@celery.task(bind=True, name="worker.tasks.resume_after_approval")
def resume_after_approval(self, pipeline_run_id: str, phase_number: int):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.resume_after_approval(phase_number)
            logger.info("task.resume.done", pipeline_id=pipeline_run_id, phase=phase_number)
            return result
        except Exception as e:
            logger.error("task.resume.failed", pipeline_id=pipeline_run_id, phase=phase_number, error=str(e))
            raise


@celery.task(bind=True, name="worker.tasks.sync_files")
def sync_files(self, pipeline_run_id: str):
    """Manually sync files from worker volume to web service."""
    import os
    import httpx
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.models.phase_result import PhaseResult

        # Get Phase 6 output which contains the upload_package
        phase_6 = PhaseResult.query.filter_by(
            pipeline_run_id=pipeline_run_id, phase_number=6
        ).first()

        if not phase_6 or not phase_6.output_data:
            logger.error("sync.no_phase6", pipeline_id=pipeline_run_id)
            return {"error": "No Phase 6 output found"}

        upload_package = phase_6.output_data.get("upload_package", {})
        if not upload_package:
            logger.error("sync.no_package", pipeline_id=pipeline_run_id)
            return {"error": "No upload package in Phase 6"}

        web_url = os.environ.get("WEB_INTERNAL_URL", "https://web-production-b0ce2.up.railway.app")
        upload_endpoint = f"{web_url}/api/internal/upload/{pipeline_run_id}"

        files_to_sync = [
            ("video", upload_package.get("video_file")),
            ("audio", upload_package.get("audio_file")),
            ("subtitle", upload_package.get("subtitle_file")),
            ("thumbnail", upload_package.get("thumbnail_file")),
        ]

        results = []
        for file_type, file_path in files_to_sync:
            if not file_path:
                results.append({"type": file_type, "status": "skipped", "reason": "no path"})
                continue
            if not os.path.exists(file_path):
                results.append({"type": file_type, "status": "skipped", "reason": f"file not found: {file_path}"})
                continue

            try:
                file_size = os.path.getsize(file_path)
                with open(file_path, "rb") as f:
                    response = httpx.post(
                        f"{upload_endpoint}/{file_type}",
                        files={"file": (os.path.basename(file_path), f)},
                        timeout=300,
                    )
                    if response.status_code == 200:
                        results.append({
                            "type": file_type,
                            "status": "success",
                            "size": file_size,
                            "response": response.json(),
                        })
                        logger.info("sync.file_ok", file_type=file_type, size=file_size)
                    else:
                        results.append({
                            "type": file_type,
                            "status": "error",
                            "http_status": response.status_code,
                            "response": response.text[:200],
                        })
                        logger.error("sync.file_failed", file_type=file_type, status=response.status_code)
            except Exception as e:
                results.append({
                    "type": file_type,
                    "status": "exception",
                    "error": str(e),
                })
                logger.error("sync.file_exception", file_type=file_type, error=str(e))

        logger.info("sync.complete", pipeline_id=pipeline_run_id, results=results)
        return {"pipeline_id": pipeline_run_id, "results": results}
