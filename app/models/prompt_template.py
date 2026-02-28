import uuid
from datetime import datetime, timezone

from app import db


class PromptTemplate(db.Model):
    __tablename__ = "prompt_templates"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phase_number = db.Column(db.Integer, nullable=False)
    agent_name = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    template_key = db.Column(db.String(100), nullable=False)  # e.g. "analyze_trends", "validate_niche"
    template = db.Column(db.Text, nullable=False)
    variables = db.Column(db.JSON, nullable=True, default=list)  # expected template variables
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("template_key", "version", name="uq_template_key_version"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "phase_number": self.phase_number,
            "agent_name": self.agent_name,
            "name": self.name,
            "template_key": self.template_key,
            "template": self.template,
            "variables": self.variables,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def render(self, **kwargs):
        """Render the template with provided variables."""
        rendered = self.template
        for key, value in kwargs.items():
            rendered = rendered.replace("{{" + key + "}}", str(value))
        return rendered
