# Audio-First Architecture Test Context

**Date:** 2026-03-11
**Status:** Test pipeline running on Railway

## Current Test Pipeline

**Pipeline ID:** `3bb500cc-f825-4893-a0bd-7f70119c1412`
**Topic:** "A homeless man returned my lost wallet. What I did next changed both our lives."

### Phase Progress

| Phase | Name | Status | Duration | Output |
|-------|------|--------|----------|--------|
| 1 | Ideas Discovery | completed | 37s | Ideas generated |
| 2 | Script Generation | completed | 193s (3.2m) | "He handed me my wallet... wearing my father's jacket", 7 sections |
| 3 | Voice Generation | completed | 147s (2.4m) | Audio: 1608s (26.8 min), **4178 word timestamps** |
| 4 | Media Collection | **running** | - | Using `chat_completion` fix |
| 5 | Video Assembly | pending | - | - |
| 6 | QA & Package | pending | - | - |

## What We're Testing

### The Audio-First Architecture

Previous pipeline order:
```
Phase 2: Script → Phase 3: Media → Phase 4: Voice → Phase 5: Assembly
```

New Audio-First order:
```
Phase 2: Script → Phase 3: Voice → Phase 4: Media → Phase 5: Assembly
```

**Key Change:** Generate audio FIRST, get Whisper timestamps, THEN generate images locked to those timestamps.

### The Fix Being Validated

Previous test pipeline `8a1cc77a` failed at Phase 4 with:
```
cannot import name 'chat_completion' from 'app.integrations.anthropic_client'
```

**Fix Applied:** Added `chat_completion()` wrapper function to `app/integrations/anthropic_client.py`:

```python
def chat_completion(
    messages: list,
    system: str = None,
    model: str = "claude-sonnet-4-5-20250929",
    json_mode: bool = False,
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> str | dict:
    """Chat completion wrapper for messages-style API calls."""
    user_content = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break

    return call_anthropic(
        prompt=user_content,
        system_prompt=system,
        model=model,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
    )
```

**Deployed to Railway:** web and worker SUCCESS at 12:39:41

## Key Files

- `app/integrations/anthropic_client.py` - Contains the `chat_completion` fix
- `app/services/visual_beat_segmenter.py` - Uses `chat_completion` for LLM-guided segmentation
- `app/agents/media_agent.py` - Phase 4 agent that calls visual beat segmenter
- `docs/superpowers/specs/2026-03-11-audio-first-alignment-design.md` - Design specification

## Background Monitor

A background monitor (`bec534`) is running with auto-approval to track pipeline progress.

To check status manually:
```bash
curl -s "https://web-production-b0ce2.up.railway.app/api/pipelines/3bb500cc-f825-4893-a0bd-7f70119c1412" | python3 -m json.tool
```

## Expected Outcomes

If Phase 4 completes successfully (no import error):
1. The `chat_completion` fix is validated
2. Visual beat segmentation will produce segments with exact timestamps
3. Images will be generated locked to narration timing
4. Visual-narration alignment should improve from ~70-75% to 90%+

## Next Steps

1. **Monitor pipeline completion** - Check if all 6 phases complete
2. **Verify Phase 4 output** - Should include `segments[]` with `scene_id` grouping
3. **Watch final video** - Evaluate visual-narration alignment quality
4. **If successful** - Audio-First Architecture is production-ready

## Railway Deployment Info

- **Project ID:** `657633a5-a4d9-48df-96ba-fa08345e8341`
- **Web URL:** `https://web-production-b0ce2.up.railway.app`
- **Channel ID:** `0738992a-9116-4f15-b09b-72f31043418f`

## Commands to Resume

Check pipeline status:
```bash
python3 -c "
import httpx, json

PIPELINE_ID = '3bb500cc-f825-4893-a0bd-7f70119c1412'
r = httpx.get(f'https://web-production-b0ce2.up.railway.app/api/pipelines/{PIPELINE_ID}', timeout=30)
p = r.json()

print(f'Status: {p.get(\"status\")} | Phase: {p.get(\"current_phase\")}')
for ph in p.get('phases', []):
    dur = ph.get('duration_seconds')
    dur_str = f'{dur:.0f}s' if dur else 'running...'
    print(f'  Phase {ph[\"phase_number\"]}: {ph.get(\"status\", \"-\"):12} ({dur_str})')

if p.get('error_message'):
    print(f'Error: {p[\"error_message\"][:500]}')
"
```

Start a new test pipeline:
```bash
CHANNEL_ID="0738992a-9116-4f15-b09b-72f31043418f"
python3 -c "
import httpx, json

r = httpx.post(
    'https://web-production-b0ce2.up.railway.app/api/pipelines/',
    json={
        'channel_id': '$CHANNEL_ID',
        'topic': 'Your story topic here',
        'config': {'mode': 'story', 'style': 'cinematic'},
        'auto_start': True
    },
    timeout=30
)
print(json.dumps(r.json(), indent=2))
"
```
