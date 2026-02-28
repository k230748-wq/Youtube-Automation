import uuid
from datetime import datetime, timezone

from app import db


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = db.Column(db.String(36), db.ForeignKey("channels.id"), nullable=False, index=True)
    idea_id = db.Column(db.String(36), db.ForeignKey("ideas.id"), nullable=True, index=True)
    pipeline_run_id = db.Column(db.String(36), db.ForeignKey("pipeline_runs.id"), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    script_text = db.Column(db.Text, nullable=True)
    tags_list = db.Column(db.JSON, nullable=True, default=list)
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft | processing | ready | uploaded
    final_video_path = db.Column(db.String(500), nullable=True)
    thumbnail_path = db.Column(db.String(500), nullable=True)
    subtitle_path = db.Column(db.String(500), nullable=True)
    audio_path = db.Column(db.String(500), nullable=True)
    duration_seconds = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    assets = db.relationship("Asset", backref="video", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "idea_id": self.idea_id,
            "pipeline_run_id": self.pipeline_run_id,
            "title": self.title,
            "description": self.description,
            "script_text": self.script_text,
            "tags_list": self.tags_list,
            "status": self.status,
            "final_video_path": self.final_video_path,
            "thumbnail_path": self.thumbnail_path,
            "subtitle_path": self.subtitle_path,
            "audio_path": self.audio_path,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
