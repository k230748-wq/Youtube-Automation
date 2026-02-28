# YouTube Automation Pipeline — Design Document

**Date**: March 1, 2026
**Project**: youtube-automation
**Location**: `/Users/apple/Desktop/Zelu/youtube-automation/`

---

## Overview

Multi-agent pipeline for automated YouTube video creation across 7 faceless channels. Automates: idea research, script writing, media collection, voice narration, video assembly, and QA packaging. Final upload is manual via YouTube Studio.

---

## 6-Phase Pipeline

| Phase | Name | Agent | What It Does |
|-------|------|-------|-------------|
| 1 | Ideas Discovery | ideas_agent | Google Trends + SerpAPI + YouTube Data API → ranked video ideas per channel |
| 2 | Script Generation | script_agent | Claude/GPT → script + title + description + tags |
| 3 | Media Collection | media_agent | Pexels/Pixabay stock clips per scene + Ideogram/DALL-E thumbnail |
| 4 | Voice Generation | voice_agent | ElevenLabs TTS → narration audio from script |
| 5 | Video Assembly | video_agent | FFmpeg: stitch clips + audio + overlays → final MP4 |
| 6 | QA & Package | qa_agent | Whisper subtitles + quality review + package for upload |

Each phase has an approval gate — pipeline pauses for human review.

---

## Architecture

- **Fully separate project** from ZEULE — own git repo, Docker stack, database, frontend
- Reuses ZEULE patterns: base agent, orchestrator engine, Celery workers, LLM clients
- Same stack: Flask + PostgreSQL + Redis + Celery + Docker Compose
- Frontend: React + Vite + Tailwind
- Port: 5002 (ZEULE uses 5001)

---

## Data Models

### Channels
`channel_id, name, niche, youtube_channel_id, voice_id, language, active, created_at`

### Ideas
`idea_id, channel_id, topic, score, source, status, meta_json, created_at`

### Videos
`video_id, channel_id, idea_id, title, description, script_text, status, final_video_path, thumbnail_path, created_at`

### Assets
`asset_id, video_id, type, file_path, metadata_json, created_at`
- Types: stock_clip, thumbnail, voice_draft, subtitle

### Tags
`tag_id, video_id, tag_text`

### PipelineRun / PhaseResult
Same pattern as ZEULE — tracks pipeline execution, phase outputs, approval status.

---

## Integrations

### Copied from ZEULE (as-is or minimal adaptation)
- `anthropic_client.py` — Claude API calls
- `openai_client.py` — GPT-4 + Whisper + DALL-E
- `perplexity_client.py` — research queries
- `serpapi_client.py` — Google Trends data
- `ideogram_client.py` — thumbnail image generation
- `bannerbear_client.py` — thumbnail templating

### Built Fresh
- **Pexels client** — `GET /v1/videos/search` — stock video/image search
- **Pixabay client** — `GET /api/videos/` — stock video fallback
- **YouTube Data API client** — trending videos, keyword research, channel data
- **ElevenLabs client** — `POST /v1/text-to-speech/{voice_id}` — narration audio
- **FFmpeg integration** — local CLI in Docker — video stitching, overlay, subtitle burn-in
- **Whisper integration** — via OpenAI API — audio → SRT subtitles

---

## Reused ZEULE Components

| Component | ZEULE File | Adaptation |
|-----------|-----------|------------|
| Base agent class | `app/agents/base.py` | Minimal |
| Orchestrator engine | `app/orchestrator/engine.py` | 6 phases instead of 8 |
| Orchestrator state | `app/orchestrator/state.py` | New phase names/agents |
| DB models pattern | `app/models/*.py` | New tables + same base pattern |
| Utils | `app/utils/*.py` | Copy as-is |
| Config/settings | `config/settings.py` | New env vars |
| Celery worker | `worker/*.py` | Same pattern, new tasks |
| Docker setup | `Dockerfile`, `docker-compose.yml` | Add FFmpeg, port 5002 |
| Frontend scaffold | `frontend/` | Copy React/Vite/Tailwind setup, rebuild UI |
| Prompt system | `config/prompts/*.yaml` | New prompts for video agents |

---

## Frontend Sections

1. **Channel Manager** — CRUD for 7 channels with niche, voice config
2. **Ideas Dashboard** — generated ideas with scores, approve/discard buttons
3. **Script Editor** — AI-generated script, title, description, tags — editable
4. **Media Gallery** — fetched stock clips + generated thumbnail preview, regenerate option
5. **Audio Player** — ElevenLabs draft narration playback
6. **Video Preview** — assembled video player + download
7. **Upload Checklist** — title, desc, tags, thumbnail, subtitle file, audience setting — all packaged for YouTube Studio

---

## Docker

- Base image: Python 3.11 + FFmpeg
- Services: web (Flask), worker (Celery), beat (scheduler), redis, postgres
- Port mapping: 5002 → 5000 (internal)
- Volumes: assets/ for generated media

---

## Key Risks & Mitigations

- **YouTube monetization**: AI voices won't monetize — ElevenLabs is for drafts, human voice upload option in UI
- **API costs at scale**: 7 channels × daily videos — cache results, rate limit, fallback between Pexels/Pixabay
- **FFmpeg complexity**: Video assembly is the hardest piece — start with simple scene stitching, add overlays incrementally
- **Content licensing**: Pexels/Pixabay require attribution — track in Assets metadata
