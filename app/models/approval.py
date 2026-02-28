import uuid
from datetime import datetime, timezone

from app import db


class Approval(db.Model):
    __tablename__ = "approvals"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phase_result_id = db.Column(db.String(36), db.ForeignKey("phase_results.id"), nullable=False, unique=True)
    pipeline_run_id = db.Column(db.String(36), db.ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    phase_number = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )  # pending | approved | rejected | edited
    reviewer_notes = db.Column(db.Text, nullable=True)
    original_output = db.Column(db.JSON, nullable=True)
    edited_output = db.Column(db.JSON, nullable=True)  # if reviewer modified the output
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "phase_result_id": self.phase_result_id,
            "pipeline_run_id": self.pipeline_run_id,
            "phase_number": self.phase_number,
            "status": self.status,
            "reviewer_notes": self.reviewer_notes,
            "original_output": self.original_output,
            "edited_output": self.edited_output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
