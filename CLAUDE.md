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
