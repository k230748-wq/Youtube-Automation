import uuid
from datetime import datetime, timezone

from app import db


class Idea(db.Model):
    __tablename__ = "ideas"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = db.Column(db.String(36), db.ForeignKey("channels.id"), nullable=False, index=True)
    topic = db.Column(db.String(500), nullable=False)
    score = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(50), nullable=True)  # google_trends | serpapi | youtube | manual
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | approved | discarded | used
    meta_json = db.Column(db.JSON, nullable=True, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    videos = db.relationship("Video", backref="idea", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "topic": self.topic,
            "score": self.score,
            "source": self.source,
            "status": self.status,
            "meta_json": self.meta_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
