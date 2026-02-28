import uuid
from datetime import datetime, timezone

from app import db


class PhaseResult(db.Model):
    __tablename__ = "phase_results"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = db.Column(db.String(36), db.ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    phase_number = db.Column(db.Integer, nullable=False)
    agent_name = db.Column(db.String(100), nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="running",
    )  # running | waiting_approval | approved | rejected | completed | failed
    input_data = db.Column(db.JSON, nullable=True)
    output_data = db.Column(db.JSON, nullable=True)
    prompt_used = db.Column(db.Text, nullable=True)  # snapshot of prompt at execution time
    duration_seconds = db.Column(db.Float, nullable=True)
    error_log = db.Column(db.Text, nullable=True)
    trace_id = db.Column(db.String(36), nullable=True)  # for observability
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    approval = db.relationship("Approval", backref="phase_result", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "pipeline_run_id": self.pipeline_run_id,
            "phase_number": self.phase_number,
            "agent_name": self.agent_name,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "prompt_used": self.prompt_used,
            "duration_seconds": self.duration_seconds,
            "error_log": self.error_log,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }
