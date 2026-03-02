import uuid
from datetime import datetime, timezone

from app import db


class PipelineRun(db.Model):
    __tablename__ = "pipeline_runs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    current_phase = db.Column(db.Integer, nullable=False, default=1)
    channel_id = db.Column(db.String(36), db.ForeignKey("channels.id"), nullable=True, index=True)
    niche = db.Column(db.String(255), nullable=False)
    topic = db.Column(db.String(255), nullable=True)
    config = db.Column(db.JSON, nullable=False, default=dict)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    phase_results = db.relationship("PhaseResult", backref="pipeline_run", lazy="dynamic", order_by="PhaseResult.phase_number")
    videos = db.relationship("Video", backref="pipeline_run", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "current_phase": self.current_phase,
            "channel_id": self.channel_id,
            "niche": self.niche,
            "topic": self.topic,
            "config": self.config,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
