import uuid
from datetime import datetime, timezone

from app import db


class Channel(db.Model):
    __tablename__ = "channels"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    niche = db.Column(db.String(255), nullable=False)
    youtube_channel_id = db.Column(db.String(100), nullable=True)
    voice_id = db.Column(db.String(100), nullable=True)  # ElevenLabs voice ID
    language = db.Column(db.String(50), nullable=False, default="en")
    active = db.Column(db.Boolean, nullable=False, default=True)
    config = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    ideas = db.relationship("Idea", backref="channel", lazy="dynamic")
    videos = db.relationship("Video", backref="channel", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "niche": self.niche,
            "youtube_channel_id": self.youtube_channel_id,
            "voice_id": self.voice_id,
            "language": self.language,
            "active": self.active,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
