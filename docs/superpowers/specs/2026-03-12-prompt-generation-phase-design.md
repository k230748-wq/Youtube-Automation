# Prompt Generation Phase Design

**Date:** 2026-03-12
**Status:** Approved
**Author:** Claude Code

## Summary

Add a dedicated Phase 4 (Prompt Generation) to the YouTube automation pipeline. This phase generates rich, detailed image prompts with full story context before image generation, allowing user review and editing before spending money on AI image generation.

## Problem

Current implementation has prompt generation embedded in the media agent:
1. `visual_beat_segmenter.py` outputs basic `visual_description` for each scene
2. `media_agent._segment_with_timing()` creates `image_prompt` as a one-liner
3. No opportunity to review/edit prompts before image generation
4. Character consistency is attempted but not enforced
5. Random background people appear because prompts lack explicit exclusion

## Solution

Insert a new Phase 4 (Prompt Generation) between Voice (Phase 3) and Media (Phase 5):

```
Phase 1: Ideas Discovery
Phase 2: Script Generation
Phase 3: Voice Generation
Phase 4: Prompt Generation  ← NEW
Phase 5: Media Collection (was 4)
Phase 6: Video Assembly (was 5)
Phase 7: QA & Package (was 6)
```

## Architecture

### New Agent: `app/agents/prompt_agent.py`

```python
class PromptAgent(BaseAgent):
    agent_name = "prompt_agent"
    phase_number = 4

    def run(self, input_data, learning_context) -> dict:
        # Get inputs from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})

        script = phase_2.get("script", "")
        word_timestamps = phase_3.get("word_timestamps", [])
        style_key = input_data.get("pipeline_config", {}).get("style", "cinematic")

        # Step 1: Get scene segments from visual beat segmenter
        segments = self._segment_script(script, word_timestamps)

        # Step 2: Generate rich prompts with full context
        result = self._generate_prompts(script, segments, style_key)

        return {
            "characters": result["characters"],
            "scene_prompts": result["scene_prompts"],
            "total_scenes": len(result["scene_prompts"]),
        }
```

### Output Structure

```python
{
    "characters": {
        "protagonist": "38-year-old woman with shoulder-length auburn hair, fair skin, wearing dark green wool coat",
        "homeless_man": "55-year-old weathered man with gray stubble, deep wrinkles, worn navy jacket with faded patches"
    },
    "scene_prompts": [
        {
            "scene_id": 1,
            "start": 0.0,
            "end": 4.2,
            "narration_text": "The rain was falling hard that night.",
            "image_prompt": "38-year-old woman with shoulder-length auburn hair, fair skin, wearing dark green wool coat, walking alone on a rain-soaked city street at night, wet pavement reflecting neon signs, atmospheric fog",
            "camera": "Wide establishing shot, slightly low angle, deep focus showing empty street stretching into distance",
            "effect": "slow_zoom_in"
        }
    ]
}
```

### New Prompt Template: `config/prompts/image_prompt_generation.yaml`

The LLM prompt enforces:
1. **Character consistency**: Same physical description in every scene
2. **No extra people**: Only named/essential characters
3. **Camera direction**: Shot type, angle, depth of field
4. **Rich detail**: Textures, lighting, atmosphere
5. **Visual continuity**: Flow between consecutive scenes

### Phase Renumbering

Files requiring updates:

| File | Change |
|------|--------|
| `app/agents/prompt_agent.py` | NEW - Phase 4 |
| `app/agents/media_agent.py` | phase_number = 5, read from phase_4_output |
| `app/agents/video_agent.py` | phase_number = 6, update references |
| `app/agents/qa_agent.py` | phase_number = 7, update references |
| `app/orchestrator/pipeline.py` | Add PromptAgent to sequence |
| `seed.py` | Add Phase 4 toggle |
| `frontend/src/App.jsx` | Update phase labels |

### Media Agent Simplification

After this change, media agent:
- Removes `_segment_with_timing()` — moved to Prompt Agent
- Removes inline prompt construction
- Simply reads `scene_prompts` from Phase 4 and generates images

### Approval UI

Phase 4 approval shows editable fields:
- **Characters dict**: Edit master character descriptions
- **Per-scene image_prompt**: Full prompt text
- **Per-scene camera**: Shot type, angle, focus
- **Per-scene effect**: Ken Burns effect dropdown

Uses existing `edited_output` approval mechanism — no new API endpoints.

## Data Flow

```
Phase 2 → script, sections, title
    ↓
Phase 3 → audio_path, word_timestamps, duration
    ↓
Phase 4 → characters, scene_prompts (with timing, camera, effect)
    ↓
Phase 5 → reads scene_prompts, generates images, outputs scene_clips
    ↓
Phase 6 → assembles video from scene_clips + audio
    ↓
Phase 7 → adds subtitles, thumbnail, metadata
```

## Benefits

1. **Review before spending**: See all prompts before GPT-Image-1 API calls
2. **Edit capability**: Fix character descriptions or scene prompts before generation
3. **Full context**: LLM sees entire story when crafting prompts
4. **Consistency**: Character descriptions enforced across all scenes
5. **No random people**: Explicit instruction to exclude bystanders
6. **Camera direction**: Professional, intentional compositions

## Implementation Approach

Single LLM call with full context:
- Input: script, segments, style
- Output: characters dict + all scene_prompts
- Model: Claude Sonnet (handles 20-40 scenes easily)
- Cost: ~$0.02-0.05 per video (one API call)

## Files to Create

1. `app/agents/prompt_agent.py` — New agent
2. `config/prompts/image_prompt_generation.yaml` — LLM prompt

## Files to Modify

1. `app/agents/media_agent.py` — Phase 5, read from phase_4_output
2. `app/agents/video_agent.py` — Phase 6, update references
3. `app/agents/qa_agent.py` — Phase 7, update references
4. `app/orchestrator/pipeline.py` — Add PromptAgent
5. `seed.py` — Add Phase 4 toggle
6. `frontend/src/App.jsx` — Update phase labels
7. `CONTEXT.md` — Update phase documentation
