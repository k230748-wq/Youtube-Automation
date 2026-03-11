# Video Duration Fix Context

**Date:** 2026-03-11
**Status:** Deployed to Railway, ready for testing

## Problem

Videos were 26.8 minutes long. User wants videos under 14 minutes.

## Root Cause

Prompts specified "8-15 minutes" with no strict word count enforcement. At ~150 words/minute, scripts were generating 4000+ words.

## Fix Applied

### 1. `config/prompts/ideas_discovery.yaml`
- Changed "8-15 minutes" → "8-12 minutes (STRICTLY under 12 minutes / 1800 words max)"
- Changed "estimated_length: 8-15" → "estimated_length: 8-12 (NEVER exceed 12 minutes)"

### 2. `config/prompts/script_generation.yaml`

**write_script_story_outline:**
- Added `CRITICAL LENGTH CONSTRAINT` section
- Added `word_estimate` field per section
- Total must be ≤ 1800 words
- Max 720 seconds (12 min)

**write_script_story_narrate:**
- Added 1200-1800 word hard limit
- Added `word_count` per section in output JSON
- "Keep it CONCISE — every sentence must earn its place"

### 3. `app/agents/script_agent.py` line 48
```python
# Before:
target_length = max(8, min(target_length, 15))  # Story mode 8-15 min

# After:
target_length = max(8, min(target_length, 12))  # Story mode 8-12 min (max 1800 words)
```

## Deployment

- **Commit:** `dddaa71`
- **Pushed:** To GitHub `main` branch
- **Railway:** Auto-deploys from main, should be live in ~2 min

## Test Command

After Railway deploys, start a new pipeline:

```bash
CHANNEL_ID="0738992a-9116-4f15-b09b-72f31043418f"
curl -s -X POST "https://web-production-b0ce2.up.railway.app/api/pipelines/" \
  -H "Content-Type: application/json" \
  -d "{
    \"channel_id\": \"$CHANNEL_ID\",
    \"topic\": \"She found a letter in her grandmother's attic. It changed everything she knew about her family.\",
    \"config\": {\"mode\": \"story\", \"style\": \"cinematic\"},
    \"auto_start\": true
  }"
```

## Expected Results

- Phase 3 (Voice) audio duration: 480-720 seconds (8-12 min)
- Final video: Under 14 minutes
- Word count per section visible in Phase 2 output

## Key Metrics to Watch

When the test pipeline completes Phase 3 (Voice), check:
```
Audio: XXXs (X.Xm)
```

Should be 480-720 seconds. Previous pipeline was 1608 seconds (26.8 min).
