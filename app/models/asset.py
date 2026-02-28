import uuid
from datetime import datetime, timezone

from app import db


class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = db.Column(db.String(36), db.ForeignKey("videos.id"), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # stock_clip | thumbnail | voice_draft | subtitle | scene_image
    file_path = db.Column(db.String(500), nullable=True)
    url = db.Column(db.String(1000), nullable=True)  # external URL (e.g., Pexels)
    metadata_json = db.Column(db.JSON, nullable=True, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "type": self.type,
            "file_path": self.file_path,
            "url": self.url,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
