"""Scheduled Celery tasks — automated idea discovery, cleanup, uploads."""

import structlog
from worker.celery_app import celery

logger = structlog.get_logger(__name__)


@celery.task(bind=True, name="worker.scheduled.discover_ideas_all_channels")
def discover_ideas_all_channels(self):
    """Run idea discovery for all active channels."""
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.models.channel import Channel
        channels = Channel.query.filter_by(active=True).all()

        results = []
        for channel in channels:
            try:
                result = _discover_for_channel(channel)
                results.append({"channel": channel.name, "ideas": result})
            except Exception as e:
                logger.error("scheduled.ideas_failed",
                             channel=channel.name, error=str(e))
                results.append({"channel": channel.name, "error": str(e)})

        logger.info("scheduled.ideas_complete", channels=len(channels))
        return results


def _discover_for_channel(channel):
    """Run ideas agent for a single channel."""
    from app.agents.ideas_agent import IdeasAgent

    agent = IdeasAgent()
    input_data = {
        "channel_id": channel.id,
        "niche": channel.niche,
        "pipeline_config": channel.config or {},
    }
    result = agent.run(input_data, learning_context=[])
    return len(result.get("ideas", []))


@celery.task(bind=True, name="worker.scheduled.cleanup_stale_pipelines")
def cleanup_stale_pipelines(self):
    """Mark pipelines stuck in 'running' for >2 hours as failed."""
    from app import create_app
    app = create_app()
    with app.app_context():
        from datetime import datetime, timezone, timedelta
        from app import db
        from app.models.pipeline_run import PipelineRun

        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        stale = PipelineRun.query.filter(
            PipelineRun.status == "running",
            PipelineRun.updated_at < cutoff,
        ).all()

        for p in stale:
            p.status = "failed"
            p.error_message = "Timed out — stuck for >2 hours"
            logger.warning("scheduled.stale_pipeline", pipeline_id=p.id)

        db.session.commit()
        logger.info("scheduled.cleanup_done", stale_count=len(stale))
        return len(stale)


@celery.task(bind=True, name="worker.scheduled.cleanup_old_assets")
def cleanup_old_assets(self):
    """Delete asset files for pipelines older than 30 days."""
    from app import create_app
    app = create_app()
    with app.app_context():
        import os
        import shutil
        from datetime import datetime, timezone, timedelta
        from app.models.pipeline_run import PipelineRun
        from config.settings import settings

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        old_pipelines = PipelineRun.query.filter(
            PipelineRun.created_at < cutoff,
            PipelineRun.status.in_(["completed", "failed"]),
        ).all()

        cleaned = 0
        for p in old_pipelines:
            asset_dir = os.path.join(settings.ASSETS_DIR, p.id)
            if os.path.exists(asset_dir):
                shutil.rmtree(asset_dir)
                cleaned += 1
                logger.info("scheduled.assets_cleaned", pipeline_id=p.id)

        logger.info("scheduled.cleanup_assets_done", cleaned=cleaned)
        return cleaned
