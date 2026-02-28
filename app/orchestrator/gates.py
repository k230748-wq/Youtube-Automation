"""Approval gates — determines whether a phase needs human review."""

from datetime import datetime, timezone

from app import db
from app.models.phase_toggle import PhaseToggle
from app.models.approval import Approval
from app.models.phase_result import PhaseResult
from app.models.learning import LearningLog


def requires_approval(phase_number: int, pipeline_config: dict = None) -> bool:
    """Check if a phase requires human approval before proceeding."""
    # Pipeline-level config overrides take priority
    if pipeline_config:
        overrides = pipeline_config.get("approval_overrides", {})
        if str(phase_number) in overrides:
            return overrides[str(phase_number)]

    # Fall back to global toggle settings
    toggle = PhaseToggle.query.filter_by(phase_number=phase_number).first()
    if toggle:
        return toggle.requires_approval

    # Default: require approval (safe default)
    return True


def create_approval_gate(phase_result: PhaseResult) -> Approval:
    """Create an approval record and pause the pipeline."""
    approval = Approval(
        phase_result_id=phase_result.id,
        pipeline_run_id=phase_result.pipeline_run_id,
        phase_number=phase_result.phase_number,
        status="pending",
        original_output=phase_result.output_data,
    )
    db.session.add(approval)

    phase_result.status = "waiting_approval"
    db.session.commit()

    return approval


def resolve_approval(approval_id: str, decision: str, notes: str = None, edited_output: dict = None) -> Approval:
    """Resolve an approval gate (approve, reject, or edit)."""
    approval = Approval.query.get(approval_id)
    if not approval:
        raise ValueError(f"Approval {approval_id} not found")

    if approval.status != "pending":
        raise ValueError(f"Approval {approval_id} already resolved: {approval.status}")

    approval.status = decision  # approved | rejected | edited
    approval.reviewer_notes = notes
    approval.resolved_at = datetime.now(timezone.utc)

    if edited_output:
        approval.status = "edited"
        approval.edited_output = edited_output

    # Update the phase result
    phase_result = approval.phase_result
    if decision in ("approved", "edited"):
        phase_result.status = "approved"
        phase_result.approved_at = datetime.now(timezone.utc)
        if edited_output:
            phase_result.output_data = edited_output
    elif decision == "rejected":
        phase_result.status = "rejected"

    # Log to learning system
    log = LearningLog(
        pipeline_run_id=approval.pipeline_run_id,
        phase_number=approval.phase_number,
        agent_name=phase_result.agent_name,
        prompt_used=phase_result.prompt_used,
        output_summary=str(phase_result.output_data)[:1000],
        feedback=decision,
        niche=phase_result.pipeline_run.niche if phase_result.pipeline_run else None,
    )
    db.session.add(log)

    db.session.commit()
    return approval
