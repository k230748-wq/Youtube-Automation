# YouTube Automation — Full Project Context

> **Read this file at the start of every new session** to restore full knowledge of the project.

Last updated: **March 2, 2026**

---

## Overview

YouTube Automation is a multi-agent pipeline for automated YouTube video creation across faceless channels. Sister project to ZEULE (digital product pipeline) — shares the same stack and architecture patterns.

- **Client**: Daniel Mendoza
- **Developer**: Mehroz Muneer
- **Root**: `/Users/apple/Desktop/Zelu/youtube-automation/`

## 6-Phase Pipeline

| Phase | Agent | What It Does |
|-------|-------|-------------|
| 1 | `ideas_agent.py` | Google Trends + SerpAPI + YouTube Data API → ranked video ideas with scores, hooks, keywords |
| 2 | `script_agent.py` | Claude → full narration script, 3+ title options, description, tags; creates Video record |
| 3 | `voice_agent.py` | OpenAI TTS (fallback ElevenLabs) → narration audio + word timestamps via Whisper; handles chunking |
| 4 | `media_agent.py` | Visual Beat Segmenter → timestamp-locked scenes → Pexels/Pixabay clips → Ideogram thumbnail |
| 5 | `video_agent.py` | FFmpeg: download clips → normalize/scale 1080p → crossfade transitions → mix audio/music → fades |
| 6 | `qa_agent.py` | Whisper subtitles (SRT) → LLM quality review → burn styled subtitles → upload package |

## Stack

- **Backend**: Flask, Celery 5.4 + Redis 7, PostgreSQL 16, Docker Compose
- **AI**: Anthropic Claude (sonnet-4-5), OpenAI GPT-4o, Perplexity
- **Media**: Pexels/Pixabay (stock video), Ideogram (thumbnails), ElevenLabs (TTS), FFmpeg (assembly), Whisper (subtitles)
- **Frontend**: React 18 + Vite 6 + Tailwind 3 + lucide-react + axios

## Ports (avoid conflicts with ZEULE)

| Service | Port | ZEULE equivalent |
|---------|------|-----------------|
| Flask | 5002 | 5001 |
| PostgreSQL | 5433 | 5432 |
| Redis | 6380 | 6379 |
| Frontend | 3001 | 3000 |

---

## Current State — March 2, 2026

### Backend: 100% Complete
- **6 agents**: All implemented with learning context injection, JSON mode LLM calls, error handling
- **13 integrations**: anthropic, openai, perplexity, serpapi, pexels, pixabay, ideogram, youtube_data, youtube_upload, elevenlabs, whisper, ffmpeg, bannerbear
- **9 API blueprints / 38 endpoints**: pipelines, channels, videos, ideas, approvals, assets, phase-toggles, tasks, upload
- **11 database models**: Channel, Idea, Video, Asset, PipelineRun, PhaseResult, Approval, PromptTemplate, LearningLog, PhaseToggle + base
- **Orchestrator**: State machine (PipelineStatus/PhaseStatus), engine (start/run_phase/resume), approval gates
- **Celery**: async tasks (run_pipeline, run_phase, resume_after_approval) + Beat scheduler (daily ideas discovery, stale cleanup, asset cleanup)
- **Prompts**: 4 YAML files (ideas_discovery, script_generation, media_collection, qa_review) with DB override support

### Frontend: 100% Complete
- **1,478-line App.jsx** — single-file React dashboard matching ZEULE pattern
- **7 pages**: Dashboard, Channels, Pipeline Detail, Videos, Video Detail, Ideas, Approvals, Settings
- **Features**: Dark mode sidebar nav, stat cards, pipeline table, phase cards with expandable JSON viewer, approval workflow (approve/reject/edit), video downloads, voice upload, YouTube upload, idea management, phase toggles
- **Build**: Passes cleanly (238 KB JS, 17 KB CSS)

### Docker: Configured
- `docker-compose.yml`: web, worker, beat, db (PostgreSQL), redis
- `Dockerfile`: Python 3.12-slim with ffmpeg installed
- Health checks on all services

---

## Directory Structure

```
youtube-automation/
├── app/
│   ├── __init__.py          # create_app() factory
│   ├── agents/              # 6 phase agents + base.py
│   ├── api/                 # 8 blueprints + routes.py
│   ├── integrations/        # 13 external clients
│   ├── models/              # 11 SQLAlchemy models
│   ├── orchestrator/        # engine.py, gates.py, state.py
│   └── utils/               # logger.py, retry.py, file_manager.py
├── config/
│   ├── settings.py          # Settings class loads from .env
│   └── prompts/             # 4 YAML prompt templates
├── worker/
│   ├── celery_app.py        # Broker config + Beat schedule
│   ├── tasks.py             # Async task definitions
│   └── scheduled.py         # Scheduled jobs
├── frontend/
│   ├── src/App.jsx          # Full dashboard (1,478 lines)
│   ├── src/main.jsx         # React entry
│   ├── src/index.css        # Base styles
│   ├── package.json         # React 18, Vite 6, Tailwind 3, axios, lucide-react
│   ├── vite.config.js       # Port 3001, proxy to Flask 5002
│   └── tailwind.config.js   # Dark mode class-based
├── migrations/              # Flask-Migrate ready
├── assets/                  # Runtime: videos, clips, audio, subtitles, thumbnails
├── docs/
│   ├── plans/               # Design doc + implementation plan
│   └── agent-drafts/        # Original agent templates (now in app/agents/)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── seed.py                  # Initialize DB with phase toggles
├── CLAUDE.md
└── CONTEXT.md               # ← This file
```

## API Endpoints Summary

### Pipelines `/api/pipelines/`
- `GET /` — list (paginated, filterable by status)
- `POST /` — create (channel_id required, topic optional, auto_start default true)
- `GET /<id>` — detail with phases array (each has output_data, approval, duration)
- `POST /<id>/start` — start pipeline
- `POST /<id>/stop` — stop pipeline
- `POST /<id>/restart_from/<phase>` — restart from specific phase

### Channels `/api/channels/`
- `GET /` — list all
- `POST /` — create (name, niche required; youtube_channel_id, voice_id, language optional)
- `GET /<id>` — detail
- `PATCH /<id>` — update
- `DELETE /<id>` — delete

### Videos `/api/videos/`
- `GET /` — list (paginated, filterable by channel_id)
- `GET /<id>` — detail with assets array
- `PATCH /<id>` — update (title, description, tags_list)
- `GET /<id>/download/<type>` — download file (video, audio, thumbnail, subtitle)
- `POST /<id>/upload-voice` — upload custom voice file
- `DELETE /<id>/delete` — delete

### Ideas `/api/ideas/`
- `GET /` — list (paginated, filterable by channel_id, status)
- `POST /` — create (channel_id, topic required; score, source optional)
- `PATCH /<id>` — update status (pending→approved/discarded)
- `DELETE /<id>` — delete

### Approvals `/api/approvals/`
- `GET /pending` — list pending (includes phase_output, phase_name)
- `POST /<id>/resolve` — resolve (decision: approved/rejected/edited, notes, edited_output)

### Phase Toggles `/api/phase-toggles/`
- `GET /` — list all 6
- `PATCH /<phase_number>` — update (is_enabled, requires_approval)
- `POST /seed` — seed defaults

### Upload `/api/upload/`
- `POST /<video_id>/youtube` — upload to YouTube (privacy_status)

## API Keys

### Configured in .env
- `ANTHROPIC_API_KEY` — Claude (sonnet-4-5)
- `OPENAI_API_KEY` — GPT-4o + Whisper + TTS
- `PERPLEXITY_API_KEY` — Research
- `SERPAPI_API_KEY` — Google Trends
- `IDEOGRAM_API_KEY` — Thumbnails
- `PEXELS_API_KEY` — Stock video
- `PIXABAY_API_KEY` — Fallback stock video
- `YOUTUBE_API_KEY` — Data API (read-only)
- `ELEVENLABS_API_KEY` — TTS voice

### Missing / Optional
- `YOUTUBE_OAUTH_TOKEN` — needed for actual YouTube upload (manual OAuth flow)
- `BANNERBEAR_API_KEY` — imported but not yet integrated

## Database Schema Key Points

- **Channel** → has many Ideas, Videos, PipelineRuns
- **PipelineRun** → has many PhaseResults → each may have one Approval
- **Video** → has many Assets (stock_clip, thumbnail, voice_draft, subtitle, scene_image)
- **LearningLog** → captures feedback from approved runs for future context injection
- **PromptTemplate** → DB-stored prompt overrides (allows editing without code)

## Celery Beat Schedule

- `discover_ideas_all_channels` — daily at 6 AM UTC
- `cleanup_stale_pipelines` — every 2 hours
- `cleanup_old_assets` — weekly Sunday 3 AM

## Docker Commands

```bash
# Build and start
docker compose build web worker && docker compose up -d && docker compose restart worker beat

# View logs
docker compose logs -f worker

# Seed database
docker compose exec web python seed.py

# Frontend dev
cd frontend && npm run dev  # → port 3001
```

## Frontend Architecture

Single-file App.jsx pattern (matching ZEULE sister project):
- **No router library** — state-based navigation via `view` + `detailId`
- **Inline components**: Card, Badge, Button, Modal, Toggle, StatusBadge, StatCard, EmptyState, Input, Select, Textarea
- **API service layer**: 25 methods wrapping axios calls to all endpoints
- **Dark mode**: Always-on (slate-950 bg), toggle switches to light
- **Sidebar**: Collapsible, 6 nav items + dark mode + collapse toggle
- **Auto-poll**: Pipeline detail refreshes every 5s when status is `running`

## Audio-First Architecture (2026-03-11)

Pipeline phase order changed for better visual-narration alignment:
- **Phase 3**: Voice Generation (was Phase 4)
- **Phase 4**: Media Collection (was Phase 3)

Voice runs first → Whisper extracts word timestamps → Visual Beat Segmenter
determines scene boundaries → Media agent generates images locked to exact times.

**Data Flow:**
```
Script → Voice Agent → audio + word_timestamps
                    ↓
          Visual Beat Segmenter → segments with scene_id + timing
                    ↓
          Media Agent → scene_clips with start_time/end_time
                    ↓
          Video Agent → uses locked timestamps for assembly
```

**Key Files:**
- `app/orchestrator/state.py` — Phase ordering constants
- `app/services/visual_beat_segmenter.py` — LLM-guided scene detection
- `config/prompts/visual_beat_segmentation.yaml` — Segmentation prompt

**Target:** 90%+ visual-narration alignment (up from ~70-75%).

---

## What's Next for Launch

1. `docker compose up -d` → initialize DB → `seed.py`
2. Test each phase with a sample channel
3. Set up YouTube OAuth for upload
4. Configure ElevenLabs voice IDs per channel
5. Run end-to-end pipeline test
6. Adjust approval thresholds and learning feedback
7. Client discussion: Lora/Flux for image generation ($0.03–$0.08 per image via serverless GPU)
