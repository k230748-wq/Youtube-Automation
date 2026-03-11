"""Pipeline state machine — manages transitions between phases."""

from enum import Enum


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


PIPELINE_TRANSITIONS = {
    PipelineStatus.PENDING: [PipelineStatus.RUNNING, PipelineStatus.FAILED],
    PipelineStatus.RUNNING: [PipelineStatus.PAUSED, PipelineStatus.COMPLETED, PipelineStatus.FAILED],
    PipelineStatus.PAUSED: [PipelineStatus.RUNNING, PipelineStatus.FAILED],
    PipelineStatus.COMPLETED: [],
    PipelineStatus.FAILED: [PipelineStatus.PENDING],
}

PHASE_TRANSITIONS = {
    PhaseStatus.PENDING: [PhaseStatus.RUNNING],
    PhaseStatus.RUNNING: [PhaseStatus.WAITING_APPROVAL, PhaseStatus.COMPLETED, PhaseStatus.FAILED],
    PhaseStatus.WAITING_APPROVAL: [PhaseStatus.APPROVED, PhaseStatus.REJECTED],
    PhaseStatus.APPROVED: [PhaseStatus.COMPLETED],
    PhaseStatus.REJECTED: [PhaseStatus.RUNNING],
    PhaseStatus.COMPLETED: [],
    PhaseStatus.FAILED: [PhaseStatus.PENDING],
}

PHASE_NAMES = {
    1: "Ideas Discovery",
    2: "Script Generation",
    3: "Voice Generation",
    4: "Media Collection",
    5: "Video Assembly",
    6: "QA & Package",
}

PHASE_AGENTS = {
    1: "ideas_agent",
    2: "script_agent",
    3: "voice_agent",
    4: "media_agent",
    5: "video_agent",
    6: "qa_agent",
}

TOTAL_PHASES = 6


def can_transition_pipeline(current: str, target: str) -> bool:
    current_status = PipelineStatus(current)
    target_status = PipelineStatus(target)
    return target_status in PIPELINE_TRANSITIONS.get(current_status, [])


def can_transition_phase(current: str, target: str) -> bool:
    current_status = PhaseStatus(current)
    target_status = PhaseStatus(target)
    return target_status in PHASE_TRANSITIONS.get(current_status, [])
