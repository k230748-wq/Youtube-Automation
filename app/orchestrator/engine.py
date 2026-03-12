"""Pipeline orchestrator — coordinates the 6-phase video creation pipeline."""

import uuid
import time
from datetime import datetime, timezone

import structlog

from app import db
from app.models.pipeline_run import PipelineRun
from app.models.phase_result import PhaseResult
from app.orchestrator.state import (
    PipelineStatus,
    PhaseStatus,
    PHASE_AGENTS,
    PHASE_NAMES,
    TOTAL_PHASES,
)
from app.orchestrator.gates import requires_approval, create_approval_gate

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """Manages the lifecycle of a video creation pipeline."""

    def __init__(self, pipeline_run_id: str):
        self.pipeline_run_id = pipeline_run_id
        self.trace_id = str(uuid.uuid4())[:8]

    @property
    def pipeline(self) -> PipelineRun:
        return PipelineRun.query.get(self.pipeline_run_id)

    def start(self):
        pipeline = self.pipeline
        if not pipeline:
            raise ValueError(f"Pipeline {self.pipeline_run_id} not found")

        logger.info("pipeline.start", pipeline_id=self.pipeline_run_id, niche=pipeline.niche, current_phase=pipeline.current_phase, trace_id=self.trace_id)

        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = pipeline.started_at or datetime.now(timezone.utc)
        db.session.commit()

        return self.run_phase(pipeline.current_phase)

    def run_phase(self, phase_number: int):
        pipeline = self.pipeline

        if phase_number > TOTAL_PHASES:
            return self._complete_pipeline()

        agent_name = PHASE_AGENTS[phase_number]
        phase_name = PHASE_NAMES[phase_number]

        logger.info("phase.start", pipeline_id=self.pipeline_run_id, phase=phase_number, phase_name=phase_name, agent=agent_name, trace_id=self.trace_id)

        phase_result = PhaseResult(
            pipeline_run_id=self.pipeline_run_id,
            phase_number=phase_number,
            agent_name=agent_name,
            status=PhaseStatus.RUNNING,
            trace_id=self.trace_id,
        )
        db.session.add(phase_result)
        pipeline.current_phase = phase_number
        db.session.commit()

        try:
            agent = self._get_agent(agent_name)
            input_data = self._gather_phase_input(phase_number)

            phase_result.input_data = input_data
            db.session.commit()

            start_time = time.time()
            output_data = agent.execute(
                pipeline_run_id=self.pipeline_run_id,
                input_data=input_data,
                phase_result_id=phase_result.id,
            )
            duration = time.time() - start_time

            phase_result.output_data = output_data
            phase_result.duration_seconds = round(duration, 2)

            # After Phase 2 (script), link the Video record to this pipeline
            if phase_number == 2 and output_data.get("video_id"):
                self._link_video_to_pipeline(output_data["video_id"])

            logger.info("phase.completed", pipeline_id=self.pipeline_run_id, phase=phase_number, duration=duration, trace_id=self.trace_id)

            if requires_approval(phase_number, pipeline.config):
                create_approval_gate(phase_result)
                pipeline.status = PipelineStatus.PAUSED
                db.session.commit()
                return {
                    "status": "paused",
                    "phase": phase_number,
                    "phase_name": phase_name,
                    "message": f"Phase {phase_number} ({phase_name}) waiting for approval",
                    "phase_result_id": phase_result.id,
                }

            phase_result.status = PhaseStatus.COMPLETED
            phase_result.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            return self._advance_to_next_phase(phase_number)

        except Exception as e:
            logger.error("phase.failed", pipeline_id=self.pipeline_run_id, phase=phase_number, error=str(e), trace_id=self.trace_id)
            phase_result.status = PhaseStatus.FAILED
            phase_result.error_log = str(e)
            pipeline.status = PipelineStatus.FAILED
            pipeline.error_message = f"Phase {phase_number} failed: {str(e)}"
            db.session.commit()
            raise

    def resume_after_approval(self, phase_number: int):
        pipeline = self.pipeline
        phase_result = PhaseResult.query.filter_by(
            pipeline_run_id=self.pipeline_run_id,
            phase_number=phase_number,
        ).order_by(PhaseResult.created_at.desc()).first()

        if phase_result:
            phase_result.status = PhaseStatus.COMPLETED
            phase_result.completed_at = datetime.now(timezone.utc)

        pipeline.status = PipelineStatus.RUNNING
        db.session.commit()

        return self._advance_to_next_phase(phase_number)

    def _advance_to_next_phase(self, current_phase: int):
        next_phase = current_phase + 1
        if next_phase > TOTAL_PHASES:
            return self._complete_pipeline()
        return self.run_phase(next_phase)

    def _complete_pipeline(self):
        pipeline = self.pipeline
        pipeline.status = PipelineStatus.COMPLETED
        pipeline.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info("pipeline.completed", pipeline_id=self.pipeline_run_id, niche=pipeline.niche, trace_id=self.trace_id)
        return {"status": "completed", "pipeline_id": self.pipeline_run_id}

    def _get_agent(self, agent_name: str):
        from app.agents.ideas_agent import IdeasAgent
        from app.agents.script_agent import ScriptAgent
        from app.agents.prompt_agent import PromptAgent
        from app.agents.media_agent import MediaAgent
        from app.agents.voice_agent import VoiceAgent
        from app.agents.video_agent import VideoAgent
        from app.agents.qa_agent import QAAgent

        agents = {
            "ideas_agent": IdeasAgent,
            "script_agent": ScriptAgent,
            "prompt_agent": PromptAgent,
            "media_agent": MediaAgent,
            "voice_agent": VoiceAgent,
            "video_agent": VideoAgent,
            "qa_agent": QAAgent,
        }
        agent_class = agents.get(agent_name)
        if not agent_class:
            raise ValueError(f"Unknown agent: {agent_name}")
        return agent_class()

    def _gather_phase_input(self, phase_number: int) -> dict:
        pipeline = self.pipeline
        input_data = {
            "niche": pipeline.niche,
            "topic": pipeline.topic,
            "channel_id": pipeline.channel_id,
            "pipeline_config": pipeline.config,
        }

        # Pull language from channel (defaults to "en")
        if pipeline.channel_id:
            try:
                from app.models.channel import Channel
                channel = Channel.query.get(pipeline.channel_id)
                if channel:
                    input_data["language"] = channel.language or "en"
            except Exception:
                pass
        input_data.setdefault("language", "en")

        previous_results = PhaseResult.query.filter(
            PhaseResult.pipeline_run_id == self.pipeline_run_id,
            PhaseResult.phase_number < phase_number,
            PhaseResult.status == PhaseStatus.COMPLETED,
        ).order_by(PhaseResult.phase_number).all()

        for result in previous_results:
            key = f"phase_{result.phase_number}_output"
            input_data[key] = result.output_data

        return input_data

    def _link_video_to_pipeline(self, video_id: str):
        """Link a Video record to this pipeline run."""
        try:
            from app.models.video import Video
            video = Video.query.get(video_id)
            if video:
                video.pipeline_run_id = self.pipeline_run_id
                db.session.commit()
                logger.info("video.linked", video_id=video_id, pipeline_id=self.pipeline_run_id)
        except Exception as e:
            logger.warning("video.link_failed", video_id=video_id, error=str(e))


def create_pipeline(channel_id: str = None, niche: str = "", topic: str = None, config: dict = None) -> PipelineRun:
    pipeline = PipelineRun(
        channel_id=channel_id,
        niche=niche,
        topic=topic,
        config=config or {},
        status=PipelineStatus.PENDING,
        current_phase=1,
    )
    db.session.add(pipeline)
    db.session.commit()
    logger.info("pipeline.created", pipeline_id=pipeline.id, niche=niche)
    return pipeline
