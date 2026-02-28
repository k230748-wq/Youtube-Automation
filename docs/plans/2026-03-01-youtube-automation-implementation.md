# YouTube Automation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a fully separate multi-agent YouTube video automation pipeline by copying reusable ZEULE infrastructure and adding video-specific agents/integrations.

**Architecture:** Flask + Celery + PostgreSQL + Redis, 6-phase pipeline (Ideas → Script → Media → Voice → Video Assembly → QA), FFmpeg for video stitching, ElevenLabs for TTS. Reuses ZEULE's orchestrator pattern, base agent, LLM clients, and frontend scaffold.

**Tech Stack:** Python 3.12, Flask, SQLAlchemy, Celery, Redis, PostgreSQL, FFmpeg, React + Vite + Tailwind

---

## Task 1: Create Project Scaffold

**Files:**
- Create: `youtube-automation/` directory structure
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `.env.example`

**Step 1: Create directory structure**

```bash
cd /Users/apple/Desktop/Zelu/youtube-automation
mkdir -p app/agents app/api app/integrations app/models app/orchestrator app/services app/utils
mkdir -p config/prompts
mkdir -p worker
mkdir -p frontend/src
mkdir -p migrations
mkdir -p assets/videos assets/thumbnails assets/clips assets/audio assets/subtitles
mkdir -p tests
```

**Step 2: Create .gitignore**

Copy from ZEULE and add video-specific patterns:

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
build/
assets/
*.db
.DS_Store
venv/
.venv/
node_modules/
*.mp4
*.mp3
*.wav
*.srt
```

**Step 3: Create requirements.txt**

```
# Core
flask==3.1.0
flask-cors==5.0.1
flask-sqlalchemy==3.1.1
flask-migrate==4.1.0
gunicorn==23.0.0

# Database
psycopg2-binary==2.9.10
sqlalchemy==2.0.36

# Task Queue
celery[redis]==5.4.0
redis==5.2.1

# AI / LLM
openai>=1.59.2
anthropic>=0.42.0

# API Integrations
httpx>=0.28.1
requests==2.32.3

# Image Processing
Pillow>=10.0

# Utilities
python-dotenv==1.0.1
pyyaml==6.0.2
structlog>=24.4.0
tenacity>=9.0.0

# Development
pytest>=8.3.4
```

**Step 4: Create .env.example**

```
# Flask
FLASK_ENV=development
SECRET_KEY=change-me

# Database
DATABASE_URL=postgresql://ytauto:ytauto_dev@localhost:5433/ytauto
POSTGRES_PASSWORD=ytauto_dev

# Redis
REDIS_URL=redis://localhost:6380/0

# AI / LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
PERPLEXITY_API_KEY=

# Research
SERPAPI_API_KEY=

# Media
IDEOGRAM_API_KEY=
BANNERBEAR_API_KEY=
PEXELS_API_KEY=
PIXABAY_API_KEY=

# YouTube
YOUTUBE_API_KEY=

# Voice
ELEVENLABS_API_KEY=

# Assets
ASSETS_DIR=./assets
```

**Step 5: Initialize git repo**

```bash
cd /Users/apple/Desktop/Zelu/youtube-automation
git init
```

**Step 6: Commit**

```bash
git add .gitignore requirements.txt .env.example
git commit -m "feat: project scaffold with dependencies and env template"
```

---

## Task 2: Copy & Adapt Core Infrastructure

**Files:**
- Create: `config/__init__.py`
- Create: `config/settings.py` (adapted from ZEULE `config/settings.py`)
- Create: `app/__init__.py` (adapted from ZEULE `app/__init__.py`)
- Create: `app/utils/__init__.py`
- Create: `app/utils/logger.py` (copy from ZEULE)
- Create: `app/utils/retry.py` (copy from ZEULE)
- Create: `app/utils/file_manager.py` (adapted from ZEULE)

**Step 1: Create `config/__init__.py`**

Empty file.

**Step 2: Create `config/settings.py`**

Adapt ZEULE's settings for YouTube project — different DB name, different port, YouTube-specific API keys:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Database (different name/port from ZEULE)
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ytauto:ytauto_dev@localhost:5433/ytauto")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis / Celery (different port from ZEULE)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL

    # AI / LLM
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

    # Research
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

    # Media
    IDEOGRAM_API_KEY = os.getenv("IDEOGRAM_API_KEY", "")
    BANNERBEAR_API_KEY = os.getenv("BANNERBEAR_API_KEY", "")
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

    # YouTube
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    # Voice
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

    # Assets
    ASSETS_DIR = os.getenv("ASSETS_DIR", "./assets")

    # Pipeline defaults
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5


settings = Settings()
```

**Step 3: Create `app/utils/__init__.py`** — empty file

**Step 4: Copy `app/utils/logger.py`** — exact copy from ZEULE

**Step 5: Copy `app/utils/retry.py`** — exact copy from ZEULE

**Step 6: Create `app/utils/file_manager.py`**

Adapt from ZEULE — change directory helpers for video assets:

```python
"""File and asset management utilities."""

import os
import json
from config.settings import settings


def get_video_dir(pipeline_run_id: str, video_id: str = None) -> str:
    """Get or create the directory for a video's assets."""
    base = os.path.join(settings.ASSETS_DIR, pipeline_run_id)
    if video_id:
        base = os.path.join(base, video_id)
    os.makedirs(base, exist_ok=True)
    return base


def save_json(filepath: str, data: dict):
    """Save data as JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(filepath: str) -> dict:
    """Load data from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def save_text(filepath: str, content: str):
    """Save text content to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)


def save_binary(filepath: str, data: bytes):
    """Save binary content (audio, video) to file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(data)


def list_assets(pipeline_run_id: str) -> list:
    """List all assets for a pipeline run."""
    base = os.path.join(settings.ASSETS_DIR, pipeline_run_id)
    if not os.path.exists(base):
        return []

    assets = []
    for root, dirs, files in os.walk(base):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, settings.ASSETS_DIR)
            assets.append({
                "path": rel_path,
                "name": f,
                "size": os.path.getsize(full_path),
            })

    return assets
```

**Step 7: Create `app/__init__.py`**

Stripped-down version of ZEULE's — no Jinja filters (not needed for video), register video-specific blueprints:

```python
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config.from_object("config.settings.Settings")

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    migrate.init_app(app, db)

    # Register models
    from app.models import (  # noqa: F401
        pipeline_run,
        phase_result,
        prompt_template,
        approval,
        learning,
        phase_toggle,
        channel,
        video,
        idea,
        asset,
    )

    # Register API blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # Health check
    @app.route("/health")
    def health():
        return {"status": "ok", "service": "youtube-automation"}

    return app
```

**Step 8: Commit**

```bash
git add config/ app/__init__.py app/utils/
git commit -m "feat: core infrastructure — settings, logger, retry, file manager, Flask app"
```

---

## Task 3: Create Data Models

**Files:**
- Create: `app/models/__init__.py`
- Create: `app/models/pipeline_run.py` (copy from ZEULE, remove product relationship)
- Create: `app/models/phase_result.py` (copy from ZEULE as-is)
- Create: `app/models/approval.py` (copy from ZEULE as-is)
- Create: `app/models/prompt_template.py` (copy from ZEULE as-is)
- Create: `app/models/learning.py` (adapt from ZEULE — remove product_id FK)
- Create: `app/models/phase_toggle.py` (adapt from ZEULE — 6 phases)
- Create: `app/models/channel.py` (NEW)
- Create: `app/models/video.py` (NEW)
- Create: `app/models/idea.py` (NEW)
- Create: `app/models/asset.py` (NEW)

**Step 1: Create `app/models/__init__.py`** — empty file

**Step 2: Copy `app/models/pipeline_run.py`**

Adapt from ZEULE — add `channel_id` FK, remove `products` relationship:

```python
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
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

**Step 3: Copy `app/models/phase_result.py`** — exact copy from ZEULE

**Step 4: Copy `app/models/approval.py`** — exact copy from ZEULE

**Step 5: Copy `app/models/prompt_template.py`** — exact copy from ZEULE

**Step 6: Adapt `app/models/learning.py`**

Remove the product_id FK (no products table in this project):

```python
import uuid
from datetime import datetime, timezone

from app import db


class LearningLog(db.Model):
    __tablename__ = "learning_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = db.Column(db.String(36), db.ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    phase_number = db.Column(db.Integer, nullable=False)
    agent_name = db.Column(db.String(100), nullable=False)
    prompt_used = db.Column(db.Text, nullable=True)
    output_summary = db.Column(db.Text, nullable=True)
    feedback = db.Column(db.String(20), nullable=True)
    performance_score = db.Column(db.Float, nullable=True)
    niche = db.Column(db.String(255), nullable=True, index=True)
    tags = db.Column(db.JSON, nullable=True, default=list)
    extra_metadata = db.Column("metadata", db.JSON, nullable=True, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "pipeline_run_id": self.pipeline_run_id,
            "phase_number": self.phase_number,
            "agent_name": self.agent_name,
            "output_summary": self.output_summary,
            "feedback": self.feedback,
            "performance_score": self.performance_score,
            "niche": self.niche,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

**Step 7: Adapt `app/models/phase_toggle.py`**

Update to 6 YouTube phases:

```python
from app import db


class PhaseToggle(db.Model):
    __tablename__ = "phase_toggles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    phase_number = db.Column(db.Integer, nullable=False, unique=True)
    phase_name = db.Column(db.String(100), nullable=False)
    requires_approval = db.Column(db.Boolean, nullable=False, default=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "phase_number": self.phase_number,
            "phase_name": self.phase_name,
            "requires_approval": self.requires_approval,
            "is_enabled": self.is_enabled,
        }

    @staticmethod
    def seed_defaults(db_session):
        defaults = [
            (1, "Ideas Discovery"),
            (2, "Script Generation"),
            (3, "Media Collection"),
            (4, "Voice Generation"),
            (5, "Video Assembly"),
            (6, "QA & Package"),
        ]
        for phase_num, phase_name in defaults:
            existing = PhaseToggle.query.filter_by(phase_number=phase_num).first()
            if not existing:
                toggle = PhaseToggle(
                    phase_number=phase_num,
                    phase_name=phase_name,
                    requires_approval=True,
                    is_enabled=True,
                )
                db_session.add(toggle)
        db_session.commit()
```

**Step 8: Create `app/models/channel.py`** (NEW)

```python
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
```

**Step 9: Create `app/models/idea.py`** (NEW)

```python
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
```

**Step 10: Create `app/models/video.py`** (NEW)

```python
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
```

**Step 11: Create `app/models/asset.py`** (NEW)

```python
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
```

**Step 12: Commit**

```bash
git add app/models/
git commit -m "feat: data models — Channel, Video, Idea, Asset + adapted pipeline/phase models"
```

---

## Task 4: Copy LLM Integrations & Orchestrator

**Files:**
- Create: `app/integrations/__init__.py`
- Create: `app/integrations/anthropic_client.py` (copy from ZEULE)
- Create: `app/integrations/openai_client.py` (copy from ZEULE)
- Create: `app/integrations/perplexity_client.py` (copy from ZEULE)
- Create: `app/integrations/serpapi_client.py` (copy from ZEULE)
- Create: `app/integrations/ideogram_client.py` (copy from ZEULE)
- Create: `app/orchestrator/__init__.py`
- Create: `app/orchestrator/state.py` (adapted — 6 phases)
- Create: `app/orchestrator/engine.py` (adapted — YouTube agents)
- Create: `app/orchestrator/gates.py` (copy from ZEULE)

**Step 1: Create `app/integrations/__init__.py`** — empty file

**Step 2: Copy these files exactly from ZEULE** (no changes):
- `app/integrations/anthropic_client.py`
- `app/integrations/openai_client.py`
- `app/integrations/serpapi_client.py`
- `app/integrations/ideogram_client.py`

**Step 3: Copy `app/integrations/perplexity_client.py`** from ZEULE (exact copy)

**Step 4: Create `app/orchestrator/__init__.py`** — empty file

**Step 5: Create `app/orchestrator/state.py`**

Adapt from ZEULE — 6 YouTube phases:

```python
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
    3: "Media Collection",
    4: "Voice Generation",
    5: "Video Assembly",
    6: "QA & Package",
}

PHASE_AGENTS = {
    1: "ideas_agent",
    2: "script_agent",
    3: "media_agent",
    4: "voice_agent",
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
```

**Step 6: Create `app/orchestrator/engine.py`**

Adapt from ZEULE — import YouTube agents instead of ZEULE agents:

```python
"""Pipeline orchestrator — coordinates the 6-phase video creation pipeline."""

import uuid
import time
from datetime import datetime, timezone

import structlog

from app import db
from app.models.pipeline_run import PipelineRun
from app.models.phase_result import PhaseResult
from app.orchestrator.state import (
    PipelineStatus,
    PhaseStatus,
    PHASE_AGENTS,
    PHASE_NAMES,
    TOTAL_PHASES,
)
from app.orchestrator.gates import requires_approval, create_approval_gate

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """Manages the lifecycle of a video creation pipeline."""

    def __init__(self, pipeline_run_id: str):
        self.pipeline_run_id = pipeline_run_id
        self.trace_id = str(uuid.uuid4())[:8]

    @property
    def pipeline(self) -> PipelineRun:
        return PipelineRun.query.get(self.pipeline_run_id)

    def start(self):
        pipeline = self.pipeline
        if not pipeline:
            raise ValueError(f"Pipeline {self.pipeline_run_id} not found")

        logger.info("pipeline.start", pipeline_id=self.pipeline_run_id, niche=pipeline.niche, current_phase=pipeline.current_phase, trace_id=self.trace_id)

        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = pipeline.started_at or datetime.now(timezone.utc)
        db.session.commit()

        return self.run_phase(pipeline.current_phase)

    def run_phase(self, phase_number: int):
        pipeline = self.pipeline

        if phase_number > TOTAL_PHASES:
            return self._complete_pipeline()

        agent_name = PHASE_AGENTS[phase_number]
        phase_name = PHASE_NAMES[phase_number]

        logger.info("phase.start", pipeline_id=self.pipeline_run_id, phase=phase_number, phase_name=phase_name, agent=agent_name, trace_id=self.trace_id)

        phase_result = PhaseResult(
            pipeline_run_id=self.pipeline_run_id,
            phase_number=phase_number,
            agent_name=agent_name,
            status=PhaseStatus.RUNNING,
            trace_id=self.trace_id,
        )
        db.session.add(phase_result)
        pipeline.current_phase = phase_number
        db.session.commit()

        try:
            agent = self._get_agent(agent_name)
            input_data = self._gather_phase_input(phase_number)

            phase_result.input_data = input_data
            db.session.commit()

            start_time = time.time()
            output_data = agent.execute(
                pipeline_run_id=self.pipeline_run_id,
                input_data=input_data,
                phase_result_id=phase_result.id,
            )
            duration = time.time() - start_time

            phase_result.output_data = output_data
            phase_result.duration_seconds = round(duration, 2)

            logger.info("phase.completed", pipeline_id=self.pipeline_run_id, phase=phase_number, duration=duration, trace_id=self.trace_id)

            if requires_approval(phase_number, pipeline.config):
                create_approval_gate(phase_result)
                pipeline.status = PipelineStatus.PAUSED
                db.session.commit()
                return {
                    "status": "paused",
                    "phase": phase_number,
                    "phase_name": phase_name,
                    "message": f"Phase {phase_number} ({phase_name}) waiting for approval",
                    "phase_result_id": phase_result.id,
                }

            phase_result.status = PhaseStatus.COMPLETED
            phase_result.completed_at = datetime.now(timezone.utc)
            db.session.commit()

            return self._advance_to_next_phase(phase_number)

        except Exception as e:
            logger.error("phase.failed", pipeline_id=self.pipeline_run_id, phase=phase_number, error=str(e), trace_id=self.trace_id)
            phase_result.status = PhaseStatus.FAILED
            phase_result.error_log = str(e)
            pipeline.status = PipelineStatus.FAILED
            pipeline.error_message = f"Phase {phase_number} failed: {str(e)}"
            db.session.commit()
            raise

    def resume_after_approval(self, phase_number: int):
        pipeline = self.pipeline
        phase_result = PhaseResult.query.filter_by(
            pipeline_run_id=self.pipeline_run_id,
            phase_number=phase_number,
        ).order_by(PhaseResult.created_at.desc()).first()

        if phase_result:
            phase_result.status = PhaseStatus.COMPLETED
            phase_result.completed_at = datetime.now(timezone.utc)

        pipeline.status = PipelineStatus.RUNNING
        db.session.commit()

        return self._advance_to_next_phase(phase_number)

    def _advance_to_next_phase(self, current_phase: int):
        next_phase = current_phase + 1
        if next_phase > TOTAL_PHASES:
            return self._complete_pipeline()
        return self.run_phase(next_phase)

    def _complete_pipeline(self):
        pipeline = self.pipeline
        pipeline.status = PipelineStatus.COMPLETED
        pipeline.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info("pipeline.completed", pipeline_id=self.pipeline_run_id, niche=pipeline.niche, trace_id=self.trace_id)
        return {"status": "completed", "pipeline_id": self.pipeline_run_id}

    def _get_agent(self, agent_name: str):
        from app.agents.ideas_agent import IdeasAgent
        from app.agents.script_agent import ScriptAgent
        from app.agents.media_agent import MediaAgent
        from app.agents.voice_agent import VoiceAgent
        from app.agents.video_agent import VideoAgent
        from app.agents.qa_agent import QAAgent

        agents = {
            "ideas_agent": IdeasAgent,
            "script_agent": ScriptAgent,
            "media_agent": MediaAgent,
            "voice_agent": VoiceAgent,
            "video_agent": VideoAgent,
            "qa_agent": QAAgent,
        }
        agent_class = agents.get(agent_name)
        if not agent_class:
            raise ValueError(f"Unknown agent: {agent_name}")
        return agent_class()

    def _gather_phase_input(self, phase_number: int) -> dict:
        pipeline = self.pipeline
        input_data = {
            "niche": pipeline.niche,
            "topic": pipeline.topic,
            "channel_id": pipeline.channel_id,
            "pipeline_config": pipeline.config,
        }

        previous_results = PhaseResult.query.filter(
            PhaseResult.pipeline_run_id == self.pipeline_run_id,
            PhaseResult.phase_number < phase_number,
            PhaseResult.status == PhaseStatus.COMPLETED,
        ).order_by(PhaseResult.phase_number).all()

        for result in previous_results:
            key = f"phase_{result.phase_number}_output"
            input_data[key] = result.output_data

        return input_data


def create_pipeline(channel_id: str = None, niche: str = "", topic: str = None, config: dict = None) -> PipelineRun:
    pipeline = PipelineRun(
        channel_id=channel_id,
        niche=niche,
        topic=topic,
        config=config or {},
        status=PipelineStatus.PENDING,
        current_phase=1,
    )
    db.session.add(pipeline)
    db.session.commit()
    logger.info("pipeline.created", pipeline_id=pipeline.id, niche=niche)
    return pipeline
```

**Step 7: Copy `app/orchestrator/gates.py`** — exact copy from ZEULE

**Step 8: Commit**

```bash
git add app/integrations/ app/orchestrator/
git commit -m "feat: orchestrator engine (6 phases) + LLM integrations copied from ZEULE"
```

---

## Task 5: Create Base Agent & Stub Agents

**Files:**
- Create: `app/agents/__init__.py`
- Create: `app/agents/base.py` (copy from ZEULE)
- Create: `app/agents/ideas_agent.py` (stub)
- Create: `app/agents/script_agent.py` (stub)
- Create: `app/agents/media_agent.py` (stub)
- Create: `app/agents/voice_agent.py` (stub)
- Create: `app/agents/video_agent.py` (stub)
- Create: `app/agents/qa_agent.py` (stub)

**Step 1: Create `app/agents/__init__.py`** — empty file

**Step 2: Copy `app/agents/base.py`** — exact copy from ZEULE

**Step 3-8: Create stub agents** — each follows this pattern:

```python
"""Ideas Agent — discovers trending video topics for a channel."""

from app.agents.base import BaseAgent


class IdeasAgent(BaseAgent):
    agent_name = "ideas_agent"
    phase_number = 1

    def run(self, input_data: dict, learning_context: list) -> dict:
        # TODO: Implement ideas discovery
        # 1. Get channel niche from input_data
        # 2. Call SerpAPI for Google Trends
        # 3. Call YouTube Data API for trending videos
        # 4. Score and rank ideas
        # 5. Return list of ideas
        return {"ideas": [], "status": "stub"}
```

Create similar stubs for: `script_agent.py` (phase 2), `media_agent.py` (phase 3), `voice_agent.py` (phase 4), `video_agent.py` (phase 5), `qa_agent.py` (phase 6).

**Step 9: Commit**

```bash
git add app/agents/
git commit -m "feat: base agent + 6 stub agents for YouTube pipeline"
```

---

## Task 6: Create API Endpoints

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/routes.py` (adapted from ZEULE)
- Create: `app/api/pipeline.py` (adapted from ZEULE)
- Create: `app/api/approvals.py` (copy from ZEULE)
- Create: `app/api/channels.py` (NEW)
- Create: `app/api/videos.py` (NEW)

**Step 1: Create `app/api/__init__.py`** — empty file

**Step 2: Create `app/api/routes.py`**

```python
"""Main API blueprint — registers all route modules."""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

from app.api.pipeline import pipeline_bp
from app.api.approvals import approvals_bp
from app.api.channels import channels_bp
from app.api.videos import videos_bp

api_bp.register_blueprint(pipeline_bp, url_prefix="/pipelines")
api_bp.register_blueprint(approvals_bp, url_prefix="/approvals")
api_bp.register_blueprint(channels_bp, url_prefix="/channels")
api_bp.register_blueprint(videos_bp, url_prefix="/videos")
```

**Step 3: Create `app/api/pipeline.py`**

Adapt from ZEULE — remove Product references, add channel_id to create:

```python
"""Pipeline API — create, list, start, and manage video pipelines."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.pipeline_run import PipelineRun
from app.models.phase_result import PhaseResult
from app.models.approval import Approval
from app.orchestrator.engine import create_pipeline

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/", methods=["GET"])
def list_pipelines():
    status_filter = request.args.get("status")
    query = PipelineRun.query.order_by(PipelineRun.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page)
    return jsonify({
        "pipelines": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@pipeline_bp.route("/", methods=["POST"])
def create_new_pipeline():
    data = request.get_json()
    if not data or not data.get("channel_id"):
        return jsonify({"error": "channel_id is required"}), 400

    from app.models.channel import Channel
    channel = Channel.query.get(data["channel_id"])
    if not channel:
        return jsonify({"error": "Channel not found"}), 404

    pipeline = create_pipeline(
        channel_id=channel.id,
        niche=channel.niche,
        topic=data.get("topic"),
        config=data.get("config", {}),
    )

    if data.get("auto_start", True):
        from worker.tasks import run_pipeline
        run_pipeline.delay(pipeline.id)

    return jsonify(pipeline.to_dict()), 201


@pipeline_bp.route("/<pipeline_id>", methods=["GET"])
def get_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    phases = PhaseResult.query.filter_by(pipeline_run_id=pipeline_id).order_by(PhaseResult.phase_number).all()
    phases_data = []
    for p in phases:
        d = p.to_dict()
        if p.approval:
            d["approval"] = p.approval.to_dict()
        phases_data.append(d)

    return jsonify({**pipeline.to_dict(), "phases": phases_data})


@pipeline_bp.route("/<pipeline_id>/start", methods=["POST"])
def start_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    from worker.tasks import run_pipeline
    task = run_pipeline.delay(pipeline_id)
    return jsonify({"message": "Pipeline started", "pipeline_id": pipeline_id, "task_id": task.id})


@pipeline_bp.route("/<pipeline_id>/stop", methods=["POST"])
def stop_pipeline(pipeline_id):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404
    pipeline.status = "failed"
    pipeline.error_message = "Manually stopped by user"
    db.session.commit()
    return jsonify({"message": "Pipeline stopped", "pipeline_id": pipeline_id})


@pipeline_bp.route("/<pipeline_id>/restart_from/<int:phase_number>", methods=["POST"])
def restart_from_phase(pipeline_id, phase_number):
    pipeline = PipelineRun.query.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found"}), 404

    from app.orchestrator.state import TOTAL_PHASES
    if phase_number < 1 or phase_number > TOTAL_PHASES:
        return jsonify({"error": f"Invalid phase number. Must be between 1 and {TOTAL_PHASES}"}), 400

    data = request.get_json() or {}
    if data.get("config_updates"):
        config = pipeline.config or {}
        config.update(data["config_updates"])
        pipeline.config = config

    Approval.query.filter(Approval.pipeline_run_id == pipeline_id, Approval.phase_number >= phase_number).delete()
    PhaseResult.query.filter(PhaseResult.pipeline_run_id == pipeline_id, PhaseResult.phase_number >= phase_number).delete()

    pipeline.current_phase = phase_number
    pipeline.status = "pending"
    pipeline.error_message = None
    pipeline.completed_at = None
    db.session.commit()

    from worker.tasks import run_pipeline
    task = run_pipeline.delay(pipeline_id)
    return jsonify({"message": f"Pipeline restarting from phase {phase_number}", "pipeline_id": pipeline_id, "task_id": task.id})
```

**Step 4: Copy `app/api/approvals.py`** — exact copy from ZEULE

**Step 5: Create `app/api/channels.py`** (NEW)

```python
"""Channels API — CRUD for YouTube channels."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.channel import Channel

channels_bp = Blueprint("channels", __name__)


@channels_bp.route("/", methods=["GET"])
def list_channels():
    channels = Channel.query.order_by(Channel.created_at.desc()).all()
    return jsonify({"channels": [c.to_dict() for c in channels]})


@channels_bp.route("/", methods=["POST"])
def create_channel():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("niche"):
        return jsonify({"error": "name and niche are required"}), 400

    channel = Channel(
        name=data["name"],
        niche=data["niche"],
        youtube_channel_id=data.get("youtube_channel_id"),
        voice_id=data.get("voice_id"),
        language=data.get("language", "en"),
        config=data.get("config", {}),
    )
    db.session.add(channel)
    db.session.commit()
    return jsonify(channel.to_dict()), 201


@channels_bp.route("/<channel_id>", methods=["GET"])
def get_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    return jsonify(channel.to_dict())


@channels_bp.route("/<channel_id>", methods=["PATCH"])
def update_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404

    data = request.get_json() or {}
    for field in ["name", "niche", "youtube_channel_id", "voice_id", "language", "active", "config"]:
        if field in data:
            setattr(channel, field, data[field])

    db.session.commit()
    return jsonify(channel.to_dict())


@channels_bp.route("/<channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    channel.active = False
    db.session.commit()
    return jsonify({"message": "Channel deactivated"})
```

**Step 6: Create `app/api/videos.py`** (NEW)

```python
"""Videos API — list and manage generated videos."""

from flask import Blueprint, request, jsonify, send_file

from app import db
from app.models.video import Video
from app.models.asset import Asset

videos_bp = Blueprint("videos", __name__)


@videos_bp.route("/", methods=["GET"])
def list_videos():
    channel_id = request.args.get("channel_id")
    query = Video.query.order_by(Video.created_at.desc())
    if channel_id:
        query = query.filter_by(channel_id=channel_id)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        "videos": [v.to_dict() for v in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@videos_bp.route("/<video_id>", methods=["GET"])
def get_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    assets = Asset.query.filter_by(video_id=video_id).all()
    return jsonify({
        **video.to_dict(),
        "assets": [a.to_dict() for a in assets],
    })


@videos_bp.route("/<video_id>", methods=["PATCH"])
def update_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    data = request.get_json() or {}
    for field in ["title", "description", "script_text", "tags_list", "status"]:
        if field in data:
            setattr(video, field, data[field])

    db.session.commit()
    return jsonify(video.to_dict())
```

**Step 7: Commit**

```bash
git add app/api/
git commit -m "feat: API endpoints — pipelines, channels, videos, approvals"
```

---

## Task 7: Create Worker & Docker Setup

**Files:**
- Create: `worker/__init__.py`
- Create: `worker/celery_app.py` (adapted from ZEULE)
- Create: `worker/tasks.py` (adapted from ZEULE)
- Create: `Dockerfile` (adapted — add FFmpeg)
- Create: `docker-compose.yml` (adapted — different ports)
- Create: `migrations/__init__.py`
- Create: `seed.py`

**Step 1: Create `worker/__init__.py`** — empty file

**Step 2: Create `worker/celery_app.py`**

```python
"""Celery application configuration."""

from celery import Celery
from config.settings import settings

celery = Celery(
    "youtube-automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,
    task_time_limit=4200,
)

celery.autodiscover_tasks(["worker"])
```

**Step 3: Create `worker/tasks.py`**

```python
"""Celery tasks — wraps pipeline phases for async execution."""

import structlog
from worker.celery_app import celery

logger = structlog.get_logger(__name__)


@celery.task(bind=True, name="worker.tasks.run_pipeline")
def run_pipeline(self, pipeline_run_id: str):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.start()
            logger.info("task.pipeline.done", pipeline_id=pipeline_run_id, result=result)
            return result
        except Exception as e:
            logger.error("task.pipeline.failed", pipeline_id=pipeline_run_id, error=str(e))
            raise


@celery.task(bind=True, name="worker.tasks.run_phase")
def run_phase(self, pipeline_run_id: str, phase_number: int):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.run_phase(phase_number)
            logger.info("task.phase.done", pipeline_id=pipeline_run_id, phase=phase_number)
            return result
        except Exception as e:
            logger.error("task.phase.failed", pipeline_id=pipeline_run_id, phase=phase_number, error=str(e))
            raise


@celery.task(bind=True, name="worker.tasks.resume_after_approval")
def resume_after_approval(self, pipeline_run_id: str, phase_number: int):
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.orchestrator.engine import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(pipeline_run_id)
        try:
            result = orchestrator.resume_after_approval(phase_number)
            logger.info("task.resume.done", pipeline_id=pipeline_run_id, phase=phase_number)
            return result
        except Exception as e:
            logger.error("task.resume.failed", pipeline_id=pipeline_run_id, phase=phase_number, error=str(e))
            raise
```

**Step 4: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/assets

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]
```

**Step 5: Create `docker-compose.yml`**

```yaml
services:
  web:
    build: .
    command: gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
    ports:
      - "5002:5000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./assets:/app/assets

  worker:
    build: .
    command: celery -A worker.celery_app worker --loglevel=info --concurrency=4
    environment:
      - PYTHONPATH=/app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./assets:/app/assets

  beat:
    build: .
    command: celery -A worker.celery_app beat --loglevel=info
    environment:
      - PYTHONPATH=/app
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ytauto
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ytauto_dev}
      POSTGRES_DB: ytauto
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ytauto"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

**Step 6: Create `migrations/__init__.py`** — empty file

**Step 7: Create `seed.py`**

```python
"""Seed the database with default data."""

from app import create_app, db
from app.models.phase_toggle import PhaseToggle
from app.models.channel import Channel


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        PhaseToggle.seed_defaults(db.session)
        print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
```

**Step 8: Commit**

```bash
git add worker/ Dockerfile docker-compose.yml migrations/ seed.py
git commit -m "feat: Docker setup with FFmpeg, Celery worker, seed script"
```

---

## Task 8: Create Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.js`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/App.jsx` (skeleton with channel selector + pipeline view)

**Step 1: Create `frontend/package.json`**

```json
{
  "name": "youtube-automation-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.460.0",
    "axios": "^1.7.9"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.16",
    "vite": "^6.0.3"
  }
}
```

**Step 2: Create `frontend/vite.config.js`**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 3: Copy `frontend/tailwind.config.js`** — same as ZEULE

**Step 4: Copy `frontend/postcss.config.js`** from ZEULE

**Step 5: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>YouTube Automation — Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

**Step 6: Copy `frontend/src/main.jsx`** — same as ZEULE

**Step 7: Copy `frontend/src/index.css`** — same as ZEULE

**Step 8: Create `frontend/src/App.jsx`** — skeleton dashboard

```jsx
import { useState, useEffect } from 'react'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default function App() {
  const [channels, setChannels] = useState([])
  const [selectedChannel, setSelectedChannel] = useState(null)
  const [pipelines, setPipelines] = useState([])
  const [view, setView] = useState('channels')

  useEffect(() => {
    api.get('/channels/').then(r => setChannels(r.data.channels)).catch(() => {})
    api.get('/pipelines/').then(r => setPipelines(r.data.pipelines)).catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold">YouTube Automation</h1>
        <nav className="flex gap-4 mt-2 text-sm">
          <button onClick={() => setView('channels')} className={view === 'channels' ? 'text-blue-400' : 'text-gray-400'}>Channels</button>
          <button onClick={() => setView('pipelines')} className={view === 'pipelines' ? 'text-blue-400' : 'text-gray-400'}>Pipelines</button>
          <button onClick={() => setView('videos')} className={view === 'videos' ? 'text-blue-400' : 'text-gray-400'}>Videos</button>
        </nav>
      </header>
      <main className="p-6">
        {view === 'channels' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Channels ({channels.length})</h2>
            {channels.length === 0 && <p className="text-gray-500">No channels yet. Create one to get started.</p>}
            {channels.map(ch => (
              <div key={ch.id} className="border border-gray-800 rounded p-4 mb-2">
                <p className="font-medium">{ch.name}</p>
                <p className="text-sm text-gray-400">{ch.niche}</p>
              </div>
            ))}
          </div>
        )}
        {view === 'pipelines' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Pipelines ({pipelines.length})</h2>
            {pipelines.map(p => (
              <div key={p.id} className="border border-gray-800 rounded p-4 mb-2">
                <p className="font-medium">{p.niche}</p>
                <p className="text-sm text-gray-400">Phase {p.current_phase} — {p.status}</p>
              </div>
            ))}
          </div>
        )}
        {view === 'videos' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Videos</h2>
            <p className="text-gray-500">Video list will appear here after pipeline runs.</p>
          </div>
        )}
      </main>
    </div>
  )
}
```

**Step 9: Install frontend dependencies**

```bash
cd /Users/apple/Desktop/Zelu/youtube-automation/frontend && npm install
```

**Step 10: Commit**

```bash
cd /Users/apple/Desktop/Zelu/youtube-automation
git add frontend/
git commit -m "feat: React frontend scaffold — channels, pipelines, videos views"
```

---

## Task 9: Create Prompt Templates

**Files:**
- Create: `config/prompts/ideas_discovery.yaml`
- Create: `config/prompts/script_generation.yaml`
- Create: `config/prompts/media_collection.yaml`
- Create: `config/prompts/qa_review.yaml`

**Step 1: Create `config/prompts/ideas_discovery.yaml`**

```yaml
templates:
  analyze_trends:
    You are a YouTube trend analyst. Given the following trending data and channel niche, generate a ranked list of 10 video ideas.

    Channel niche: {{niche}}
    Trending data: {{trends_data}}
    YouTube trending: {{youtube_data}}

    For each idea provide:
    - topic: A compelling video topic (specific, not vague)
    - score: 1-100 based on trend strength, competition, and audience interest
    - hook: A one-sentence hook to open the video
    - estimated_length: Suggested video length in minutes
    - keywords: 5 relevant search keywords

    Return as JSON: {"ideas": [...]}

  rank_ideas:
    You are a YouTube content strategist. Rank these video ideas by potential for views and engagement.

    Channel niche: {{niche}}
    Ideas: {{ideas}}

    Return the top 5 ideas re-ranked with updated scores and brief reasoning.
    Return as JSON: {"ranked_ideas": [...]}
```

**Step 2: Create `config/prompts/script_generation.yaml`**

```yaml
templates:
  write_script:
    You are a professional YouTube scriptwriter specializing in {{niche}} content.

    Write a complete narrated video script for the following topic:
    Topic: {{topic}}
    Target length: {{target_length}} minutes
    Hook: {{hook}}

    Structure:
    1. Hook (first 30 seconds — grab attention immediately)
    2. Intro (set expectations, what viewer will learn)
    3. Main content (3-5 key sections with clear transitions)
    4. Call to action (subscribe, comment, like)
    5. Outro

    Write in a conversational, engaging tone. Include [SCENE: description] markers for visual cues.
    Mark sections with [SECTION: name] for scene splitting.

    Return as JSON:
    {
      "script": "full script text with [SCENE] and [SECTION] markers",
      "sections": [{"name": "...", "text": "...", "duration_estimate": 60}],
      "total_estimated_duration": 600
    }

  generate_title:
    Generate 5 catchy YouTube video titles (max 60 characters each) for a video about:
    Topic: {{topic}}
    Niche: {{niche}}

    Rules:
    - Include relevant keywords
    - Use power words (Ultimate, Complete, Secret, etc.)
    - At least one with a number
    - At least one with a question

    Return as JSON: {"titles": ["...", "...", ...]}

  generate_description:
    Write a SEO-optimized YouTube video description for:
    Title: {{title}}
    Topic: {{topic}}
    Keywords: {{keywords}}

    Structure:
    - First 2 lines: compelling summary with primary keyword (shown in search results)
    - Timestamps section (use {{sections}} for chapter markers)
    - Key takeaways (3-5 bullet points)
    - Call to action (subscribe + social links placeholder)
    - Tags line

    Return as JSON: {"description": "...", "tags": ["...", ...]}
```

**Step 3: Create `config/prompts/media_collection.yaml`**

```yaml
templates:
  extract_scenes:
    You are a video producer. Break this script into visual scenes for a faceless YouTube video.

    Script sections:
    {{sections}}

    For each scene provide:
    - scene_number: sequential number
    - section_name: which script section this belongs to
    - visual_description: what should be shown on screen (for stock footage search)
    - search_keywords: 3-5 keywords to search stock footage sites
    - duration_seconds: how long this scene should last
    - text_overlay: any text that should appear on screen (optional)

    Return as JSON: {"scenes": [...]}

  thumbnail_prompt:
    Generate an image generation prompt for a YouTube thumbnail.

    Video title: {{title}}
    Niche: {{niche}}

    Requirements:
    - Bold, eye-catching composition
    - Bright colors, high contrast
    - Space for text overlay on the left or right third
    - 1280x720 aspect ratio (16:9)
    - No text in the image itself (text will be added as overlay)

    Return as JSON: {"prompt": "...", "negative_prompt": "text, words, letters, watermark, blurry"}
```

**Step 4: Create `config/prompts/qa_review.yaml`**

```yaml
templates:
  review_script:
    Review this YouTube video script for quality, accuracy, and engagement.

    Script: {{script}}
    Title: {{title}}
    Niche: {{niche}}

    Check for:
    1. Factual accuracy — flag any claims that need verification
    2. Engagement — is the hook strong? Are transitions smooth?
    3. Length — does estimated duration match target?
    4. SEO — are keywords naturally integrated?
    5. Policy compliance — any content that could violate YouTube guidelines?

    Return as JSON:
    {
      "score": 1-100,
      "issues": [{"type": "...", "description": "...", "severity": "high|medium|low"}],
      "suggestions": ["..."],
      "approved": true/false
    }
```

**Step 5: Commit**

```bash
git add config/prompts/
git commit -m "feat: prompt templates for ideas, script, media, and QA agents"
```

---

## Task 10: Create New Integration Stubs

**Files:**
- Create: `app/integrations/pexels_client.py`
- Create: `app/integrations/pixabay_client.py`
- Create: `app/integrations/youtube_data_client.py`
- Create: `app/integrations/elevenlabs_client.py`
- Create: `app/integrations/ffmpeg_client.py`
- Create: `app/integrations/whisper_client.py`

**Step 1: Create `app/integrations/pexels_client.py`**

```python
"""Pexels API integration — free stock video and image search."""

import httpx
from config.settings import settings

BASE_URL = "https://api.pexels.com"


def search_videos(query: str, orientation: str = "landscape", per_page: int = 5) -> list:
    """Search Pexels for stock videos."""
    response = httpx.get(
        f"{BASE_URL}/videos/search",
        headers={"Authorization": settings.PEXELS_API_KEY},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": v["id"],
            "url": v["url"],
            "duration": v.get("duration"),
            "video_files": [
                {"link": f["link"], "quality": f.get("quality"), "width": f.get("width"), "height": f.get("height")}
                for f in v.get("video_files", [])
                if f.get("quality") in ("hd", "sd")
            ],
            "video_pictures": [p["picture"] for p in v.get("video_pictures", [])[:2]],
        }
        for v in data.get("videos", [])
    ]


def search_photos(query: str, orientation: str = "landscape", per_page: int = 5) -> list:
    """Search Pexels for stock photos."""
    response = httpx.get(
        f"{BASE_URL}/v1/search",
        headers={"Authorization": settings.PEXELS_API_KEY},
        params={"query": query, "orientation": orientation, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": p["id"],
            "url": p["url"],
            "src": p.get("src", {}),
            "photographer": p.get("photographer"),
        }
        for p in data.get("photos", [])
    ]
```

**Step 2: Create `app/integrations/pixabay_client.py`**

```python
"""Pixabay API integration — free stock video and image search (fallback)."""

import httpx
from config.settings import settings

BASE_URL = "https://pixabay.com/api"


def search_videos(query: str, per_page: int = 5) -> list:
    """Search Pixabay for stock videos."""
    response = httpx.get(
        f"{BASE_URL}/videos/",
        params={"key": settings.PIXABAY_API_KEY, "q": query, "per_page": per_page},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": v["id"],
            "duration": v.get("duration"),
            "videos": v.get("videos", {}),
            "tags": v.get("tags"),
        }
        for v in data.get("hits", [])
    ]


def search_images(query: str, per_page: int = 5) -> list:
    """Search Pixabay for stock images."""
    response = httpx.get(
        f"{BASE_URL}/",
        params={"key": settings.PIXABAY_API_KEY, "q": query, "per_page": per_page, "image_type": "photo"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": img["id"],
            "largeImageURL": img.get("largeImageURL"),
            "webformatURL": img.get("webformatURL"),
            "tags": img.get("tags"),
        }
        for img in data.get("hits", [])
    ]
```

**Step 3: Create `app/integrations/youtube_data_client.py`**

```python
"""YouTube Data API integration — trending videos, search, keyword research."""

import httpx
from config.settings import settings

BASE_URL = "https://www.googleapis.com/youtube/v3"


def search_videos(query: str, max_results: int = 10, order: str = "relevance") -> list:
    """Search YouTube for videos matching a query."""
    response = httpx.get(
        f"{BASE_URL}/search",
        params={
            "key": settings.YOUTUBE_API_KEY,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results,
            "order": order,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "channel_title": item["snippet"]["channelTitle"],
            "published_at": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"].get("high", {}).get("url"),
        }
        for item in data.get("items", [])
    ]


def get_trending(region_code: str = "US", category_id: str = None, max_results: int = 10) -> list:
    """Get trending videos for a region."""
    params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
    }
    if category_id:
        params["videoCategoryId"] = category_id

    response = httpx.get(f"{BASE_URL}/videos", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    return [
        {
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "channel_title": item["snippet"]["channelTitle"],
            "view_count": item["statistics"].get("viewCount"),
            "like_count": item["statistics"].get("likeCount"),
            "comment_count": item["statistics"].get("commentCount"),
            "tags": item["snippet"].get("tags", []),
        }
        for item in data.get("items", [])
    ]


def get_video_details(video_id: str) -> dict:
    """Get detailed info about a specific video."""
    response = httpx.get(
        f"{BASE_URL}/videos",
        params={
            "key": settings.YOUTUBE_API_KEY,
            "id": video_id,
            "part": "snippet,statistics,contentDetails",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get("items", [])
    return items[0] if items else {}
```

**Step 4: Create `app/integrations/elevenlabs_client.py`**

```python
"""ElevenLabs API integration — text-to-speech for video narration."""

import httpx
from config.settings import settings

BASE_URL = "https://api.elevenlabs.io/v1"


def text_to_speech(text: str, voice_id: str, output_path: str, model_id: str = "eleven_monolingual_v1") -> str:
    """Generate speech audio from text and save to file."""
    response = httpx.post(
        f"{BASE_URL}/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        },
        timeout=120,
    )
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def list_voices() -> list:
    """List available ElevenLabs voices."""
    response = httpx.get(
        f"{BASE_URL}/voices",
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category"),
            "labels": v.get("labels", {}),
        }
        for v in data.get("voices", [])
    ]
```

**Step 5: Create `app/integrations/ffmpeg_client.py`**

```python
"""FFmpeg integration — video assembly, stitching, overlays."""

import os
import subprocess
import structlog

logger = structlog.get_logger(__name__)


def stitch_clips(clip_paths: list, output_path: str) -> str:
    """Concatenate video clips into a single video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create concat file
    concat_file = output_path.replace(".mp4", "_concat.txt")
    with open(concat_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    os.remove(concat_file)

    if result.returncode != 0:
        logger.error("ffmpeg.stitch.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg stitch failed: {result.stderr}")

    return output_path


def add_audio(video_path: str, audio_path: str, output_path: str) -> str:
    """Add audio track to a video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        logger.error("ffmpeg.add_audio.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg add audio failed: {result.stderr}")

    return output_path


def add_subtitles(video_path: str, srt_path: str, output_path: str) -> str:
    """Burn subtitles into a video."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={srt_path}",
        "-c:a", "copy",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.error("ffmpeg.subtitles.failed", stderr=result.stderr)
        raise RuntimeError(f"FFmpeg subtitles failed: {result.stderr}")

    return output_path


def get_duration(file_path: str) -> float:
    """Get duration of a video/audio file in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")
    return float(result.stdout.strip())


def download_clip(url: str, output_path: str) -> str:
    """Download a video clip from URL."""
    import httpx
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    return output_path
```

**Step 6: Create `app/integrations/whisper_client.py`**

```python
"""OpenAI Whisper integration — audio transcription for subtitles."""

from openai import OpenAI
from config.settings import settings


def transcribe(audio_path: str, output_format: str = "srt") -> str:
    """Transcribe audio to text or subtitle format."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format=output_format,
        )

    return transcript
```

**Step 7: Commit**

```bash
git add app/integrations/pexels_client.py app/integrations/pixabay_client.py app/integrations/youtube_data_client.py app/integrations/elevenlabs_client.py app/integrations/ffmpeg_client.py app/integrations/whisper_client.py
git commit -m "feat: new integrations — Pexels, Pixabay, YouTube Data, ElevenLabs, FFmpeg, Whisper"
```

---

## Task 11: Create CLAUDE.md & Tests Scaffold

**Files:**
- Create: `CLAUDE.md`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

**Step 1: Create `CLAUDE.md`**

```markdown
# YouTube Automation — Claude Code Instructions

## Project
YouTube Automation — multi-agent pipeline for automated YouTube video creation across 7 faceless channels.
6-phase pipeline: Ideas Discovery → Script Generation → Media Collection → Voice Generation → Video Assembly → QA & Package.

## Stack
- Backend: Flask, Celery 5.4 + Redis 7, PostgreSQL 16, Docker Compose
- AI: Anthropic Claude, OpenAI GPT-4o, Perplexity
- Media: Pexels/Pixabay (stock), Ideogram (thumbnails), ElevenLabs (TTS), FFmpeg (assembly)
- Frontend: React + Vite + Tailwind (port 3001, proxies to Flask 5002)

## Key Paths
- Project root: `/Users/apple/Desktop/Zelu/youtube-automation/`
- Agents: `app/agents/`
- Integrations: `app/integrations/`
- Prompts: `config/prompts/`
- Frontend: `frontend/src/`

## Docker Commands
docker compose build web worker
docker compose up -d && docker compose restart worker beat
docker compose logs -f worker

## API
- Pipeline API: `http://localhost:5002/api/pipelines/`
- Channels API: `http://localhost:5002/api/channels/`
- Videos API: `http://localhost:5002/api/videos/`
- Frontend dev: `cd frontend && npm run dev` → port 3001

## Ports (avoid conflicts with ZEULE)
- Flask: 5002 (ZEULE uses 5001)
- PostgreSQL: 5433 (ZEULE uses 5432)
- Redis: 6380 (ZEULE uses 6379)
- Frontend: 3001 (ZEULE uses 3000)
```

**Step 2: Create `tests/__init__.py`** — empty file

**Step 3: Create a basic `tests/test_models.py`**

```python
"""Basic model tests."""

import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_create_channel(client):
    response = client.post("/api/channels/", json={"name": "Test Channel", "niche": "technology"})
    assert response.status_code == 201
    assert response.json["name"] == "Test Channel"


def test_list_channels(client):
    client.post("/api/channels/", json={"name": "Ch1", "niche": "tech"})
    response = client.get("/api/channels/")
    assert response.status_code == 200
    assert len(response.json["channels"]) == 1
```

**Step 4: Commit**

```bash
git add CLAUDE.md tests/
git commit -m "feat: CLAUDE.md project instructions + basic test scaffold"
```

---

## Task 12: Build & Verify Docker Stack

**Step 1: Copy `.env.example` to `.env` and fill in API keys**

```bash
cp .env.example .env
# Edit .env with actual keys (shared with ZEULE where applicable)
```

**Step 2: Build Docker images**

```bash
docker compose build web worker
```

Expected: Build succeeds, FFmpeg installed in image.

**Step 3: Start services**

```bash
docker compose up -d
```

Expected: web, worker, beat, db, redis all running.

**Step 4: Run migrations**

```bash
docker compose exec web flask db init
docker compose exec web flask db migrate -m "Initial models"
docker compose exec web flask db upgrade
```

**Step 5: Seed database**

```bash
docker compose exec web python seed.py
```

**Step 6: Verify health endpoint**

```bash
curl http://localhost:5002/health
```

Expected: `{"status": "ok", "service": "youtube-automation"}`

**Step 7: Test channel creation**

```bash
curl -X POST http://localhost:5002/api/channels/ -H "Content-Type: application/json" -d '{"name": "Tech Explained", "niche": "technology"}'
```

Expected: 201 response with channel data.

**Step 8: Commit any fixes if needed**

```bash
git add -A && git commit -m "fix: Docker build and startup verified"
```

---

## Summary

| Task | What | Effort |
|------|------|--------|
| 1 | Project scaffold | 10 min |
| 2 | Core infrastructure (settings, utils, Flask app) | 15 min |
| 3 | Data models (8 models) | 20 min |
| 4 | LLM integrations + orchestrator (copy + adapt) | 20 min |
| 5 | Base agent + 6 stub agents | 15 min |
| 6 | API endpoints (4 blueprints) | 20 min |
| 7 | Worker + Docker + seed | 15 min |
| 8 | Frontend scaffold | 15 min |
| 9 | Prompt templates | 15 min |
| 10 | New integration stubs (6 clients) | 25 min |
| 11 | CLAUDE.md + tests | 10 min |
| 12 | Build & verify Docker stack | 15 min |
| **Total** | **Full project scaffold with working Docker stack** | **~3 hours** |

After these 12 tasks, you'll have a fully scaffolded, Docker-ready YouTube automation project with all agents stubbed, all integrations written, all models defined, and a working frontend shell. The next sprint will be implementing the actual agent logic (Ideas → Script → Media → Voice → Video → QA).
