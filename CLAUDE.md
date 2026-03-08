# YouTube Automation — Claude Code Instructions

## Project
YouTube Automation — multi-agent pipeline for automated YouTube video creation across faceless channels.
6-phase pipeline: Ideas Discovery → Script Generation → Media Collection → Voice Generation → Video Assembly → QA & Package.

## Context File
**Before starting any work, read `/Users/apple/Desktop/Zelu/youtube-automation/CONTEXT.md`** — it contains full project state, architecture, what's done, and all decisions made so far.

## Stack
- Backend: Flask, Celery 5.4 + Redis 7, PostgreSQL 16, Docker Compose
- AI: Anthropic Claude (sonnet-4-5), OpenAI GPT-4o, Perplexity
- Media: Pexels/Pixabay (stock), Ideogram (thumbnails), ElevenLabs (TTS), FFmpeg (assembly), Whisper (subtitles)
- Frontend: React 18 + Vite 6 + Tailwind 3 (port 3001, proxies to Flask 5002)

## Key Paths
- Project root: `/Users/apple/Desktop/Zelu/youtube-automation/`
- Agents: `app/agents/`
- Integrations: `app/integrations/`
- Prompts: `config/prompts/`
- Models: `app/models/`
- Orchestrator: `app/orchestrator/`
- API: `app/api/`
- Frontend: `frontend/src/App.jsx` (1,478-line single-file dashboard)

## Docker Commands
```bash
docker compose build web worker
docker compose up -d && docker compose restart worker beat
docker compose logs -f worker
docker compose exec web python seed.py
```

## API
- Pipeline API: `http://localhost:5002/api/pipelines/`
- Channels API: `http://localhost:5002/api/channels/`
- Videos API: `http://localhost:5002/api/videos/`
- Ideas API: `http://localhost:5002/api/ideas/`
- Approvals API: `http://localhost:5002/api/approvals/`
- Phase Toggles: `http://localhost:5002/api/phase-toggles/`
- Frontend dev: `cd frontend && npm run dev` → port 3001

## Ports (avoid conflicts with ZEULE)
- Flask: 5002 (ZEULE uses 5001)
- PostgreSQL: 5433 (ZEULE uses 5432)
- Redis: 6380 (ZEULE uses 6379)
- Frontend: 3001 (ZEULE uses 3000)

## Current Status (March 2, 2026)
- **Backend**: 100% complete — 6 agents, 13 integrations, 9 API blueprints (38 endpoints), 11 models, orchestrator with approval gates
- **Frontend**: 100% complete — full dashboard with 7 pages, dark mode, sidebar nav, all CRUD operations
- **Not yet tested**: End-to-end pipeline run, YouTube OAuth upload, ElevenLabs voice setup
- **Next**: Docker up → seed DB → test phases → configure voice IDs → end-to-end test

## Rules
- ALWAYS rebuild BOTH `web` and `worker` after code changes
- Frontend is single-file `App.jsx` — no routing library, state-based navigation
- Pipeline auto-polls every 5s when status is `running`
- Phase toggles control `is_enabled` and `requires_approval` per phase
- Approval decisions: `approved`, `rejected`, `edited` (edited requires `edited_output` JSON)
