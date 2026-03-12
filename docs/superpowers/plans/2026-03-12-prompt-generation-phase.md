# Prompt Generation Phase Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Phase 4 (Prompt Generation) to create rich, reviewable image prompts before image generation.

**Architecture:** New PromptAgent calls visual_beat_segmenter for scene boundaries, then makes a single LLM call with full story context to generate detailed image prompts with character consistency, camera direction, and Ken Burns effects. Media agent is simplified to just read prompts and generate images.

**Tech Stack:** Python, Claude Sonnet API, YAML prompt templates, Flask/SQLAlchemy

---

## File Structure

### Files to Create
| File | Responsibility |
|------|----------------|
| `app/agents/prompt_agent.py` | New Phase 4 agent - generates image prompts |
| `config/prompts/image_prompt_generation.yaml` | LLM prompt template |

### Files to Modify
| File | Changes |
|------|---------|
| `app/orchestrator/state.py` | Update PHASE_NAMES, PHASE_AGENTS, TOTAL_PHASES |
| `app/orchestrator/engine.py` | Add prompt_agent import |
| `app/models/phase_toggle.py` | Update seed_defaults for 7 phases |
| `app/agents/media_agent.py` | Change to phase 5, read from phase_4_output |
| `app/agents/video_agent.py` | Change to phase 6, update phase references |
| `app/agents/qa_agent.py` | Change to phase 7, update phase references |
| `frontend/src/App.jsx` | Update phase labels |
| `CONTEXT.md` | Update documentation |

---

## Chunk 1: Core Infrastructure

### Task 1: Update Orchestrator State

**Files:**
- Modify: `app/orchestrator/state.py:42-60`

- [ ] **Step 1: Update PHASE_NAMES dict**

```python
PHASE_NAMES = {
    1: "Ideas Discovery",
    2: "Script Generation",
    3: "Voice Generation",
    4: "Prompt Generation",      # NEW
    5: "Media Collection",       # was 4
    6: "Video Assembly",         # was 5
    7: "QA & Package",           # was 6
}
```

- [ ] **Step 2: Update PHASE_AGENTS dict**

```python
PHASE_AGENTS = {
    1: "ideas_agent",
    2: "script_agent",
    3: "voice_agent",
    4: "prompt_agent",           # NEW
    5: "media_agent",            # was 4
    6: "video_agent",            # was 5
    7: "qa_agent",               # was 6
}
```

- [ ] **Step 3: Update TOTAL_PHASES**

```python
TOTAL_PHASES = 7
```

- [ ] **Step 4: Commit**

```bash
git add app/orchestrator/state.py
git commit -m "feat: update orchestrator state for 7-phase pipeline"
```

---

### Task 2: Update PhaseToggle Seed Defaults

**Files:**
- Modify: `app/models/phase_toggle.py:24-31`

- [ ] **Step 1: Update defaults list**

```python
@staticmethod
def seed_defaults(db_session):
    defaults = [
        (1, "Ideas Discovery"),
        (2, "Script Generation"),
        (3, "Voice Generation"),
        (4, "Prompt Generation"),    # NEW
        (5, "Media Collection"),     # was 3
        (6, "Video Assembly"),       # was 5
        (7, "QA & Package"),         # was 6
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

- [ ] **Step 2: Commit**

```bash
git add app/models/phase_toggle.py
git commit -m "feat: add Phase 4 (Prompt Generation) to seed defaults"
```

---

### Task 3: Create Image Prompt Generation YAML Template

**Files:**
- Create: `config/prompts/image_prompt_generation.yaml`

- [ ] **Step 1: Create the prompt template file**

```yaml
image_prompt_generation:
  system: |
    You are a cinematic image prompt engineer for AI image generation.
    Your job: craft detailed, consistent image prompts for each scene of a story.

    CRITICAL RULES:
    1. CHARACTER CONSISTENCY: Use the EXACT same physical description for each
       character in EVERY scene they appear. Never change hair, clothing, age, etc.
    2. NO EXTRA PEOPLE: Only include characters who are NAMED or ESSENTIAL.
       No crowds, bystanders, or background figures unless narration explicitly mentions them.
    3. CAMERA DIRECTION: Include specific shot type, angle, and depth of field for each scene.
    4. RICH DETAIL: Include textures, lighting conditions, atmosphere, small environmental details.
    5. VISUAL CONTINUITY: Ensure smooth visual flow between consecutive scenes.
    6. SINGLE IMAGE ONLY: No collages, grids, or split screens unless narration covers many events quickly.

    CAMERA OPTIONS:
    - Shot types: extreme close-up, close-up, medium close-up, medium shot, medium wide, wide shot, extreme wide
    - Angles: eye level, low angle (heroic), high angle (vulnerable), bird's eye, dutch angle (tension)
    - Focus: shallow DOF (subject sharp, background blur), deep focus (all sharp), rack focus

    EFFECT OPTIONS (Ken Burns for video):
    - slow_zoom_in: gentle push toward subject (builds intimacy/tension)
    - slow_zoom_out: gentle pull back (reveals context/scale)
    - pan_left / pan_right: horizontal movement (following action)
    - tilt_up / tilt_down: vertical movement
    - static: no movement (for impactful/emotional moments)

    COLLAGE SCENES (use sparingly, max 1-2 per video):
    - Only for time-passing montages ("years went by", "memories flooded back")
    - Prefix with "4-PANEL COLLAGE:" to trigger montage treatment
    - Example: "4-PANEL COLLAGE: top-left shows boy learning to ride bike, top-right shows fishing trip..."

  user: |
    Generate detailed image prompts for this story video.

    FULL SCRIPT:
    {script}

    SCENE SEGMENTS (with exact timing from audio):
    {segments_json}

    VISUAL STYLE TO APPLY:
    {style_description}

    STEP 1: Identify all characters and assign FIXED physical appearances.
    - Include: age, hair color/style, skin tone, distinguishing features, clothing
    - These descriptions will be used VERBATIM in every scene

    STEP 2: For each scene segment, generate a rich image prompt that includes:
    - The EXACT character description from Step 1 (copy-paste, don't paraphrase)
    - Setting details: location, time of day, weather, atmosphere
    - Lighting: natural/artificial, direction, quality (soft/harsh)
    - Camera: shot type, angle, depth of field
    - Ken Burns effect choice based on emotional beat
    - Small details that add realism (textures, imperfections, environmental elements)

    Output JSON (no markdown, pure JSON):
    {
      "characters": {
        "protagonist": "exact physical description with age, hair, skin, clothing...",
        "character_name": "exact physical description..."
      },
      "scene_prompts": [
        {
          "scene_id": 1,
          "start": 0.0,
          "end": 4.2,
          "narration_text": "The exact narration for this scene...",
          "image_prompt": "Full detailed prompt including character description, setting, lighting, atmosphere...",
          "camera": "Wide establishing shot, eye level, deep focus",
          "effect": "slow_zoom_in"
        }
      ]
    }
```

- [ ] **Step 2: Commit**

```bash
git add config/prompts/image_prompt_generation.yaml
git commit -m "feat: add image prompt generation LLM template"
```

---

## Chunk 2: Prompt Agent Implementation

### Task 4: Create PromptAgent

**Files:**
- Create: `app/agents/prompt_agent.py`

- [ ] **Step 1: Create the agent file with imports and class definition**

```python
"""Prompt Agent — generates rich image prompts with full story context."""

import json
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)

STYLE_MAP = {
    "cinematic": "Photorealistic photograph of REAL HUMANS with normal human features, shot on 35mm film. RICH DETAIL: visible skin texture, fabric weave, environmental details like dust particles in light beams. Natural muted color palette with warm accents. Shallow depth of field with cinematic bokeh, slight film grain. Looks like a still from an A24 independent drama. Realistic imperfect lighting. NO fantasy elements, NO elf ears, NO supernatural features.",
    "anime": "Japanese anime art style, vibrant cel-shaded colors, clean linework, expressive characters, Studio Ghibli influenced, warm color palette, detailed backgrounds.",
    "watercolor": "Soft watercolor painting style, flowing washes of color, visible brush strokes, dreamy atmosphere, paper texture, warm muted tones.",
    "comic": "Bold comic book illustration, thick ink outlines, halftone dots, dynamic composition, vibrant flat colors, expressive faces.",
    "gothic": "Dark gothic aesthetic, deep shadows, moody atmosphere, desaturated colors with crimson accents, dramatic chiaroscuro lighting.",
    "minimalist": "Clean minimalist design, flat vector colors, simple geometric shapes, solid backgrounds, bold negative space.",
    "retro": "Retro 1970s aesthetic, warm faded color palette, film grain, vintage photography feel, Kodachrome colors.",
    "fantasy": "Ethereal fantasy art, magical glowing elements, rich saturated colors, detailed digital painting style.",
}


class PromptAgent(BaseAgent):
    agent_name = "prompt_agent"
    phase_number = 4

    def run(self, input_data: dict, learning_context: list) -> dict:
        config = input_data.get("pipeline_config", {})

        # Get inputs from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})

        script = phase_2.get("script", "")
        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")

        word_timestamps = phase_3.get("word_timestamps", [])
        clean_script = phase_3.get("clean_script", script)

        style_key = config.get("style", "cinematic")

        if not script:
            raise ValueError("No script from Phase 2 — cannot generate prompts")

        logger.info("prompt.start", title=title, style=style_key,
                    has_timestamps=bool(word_timestamps))

        # Step 1: Get scene segments with timing
        segments = self._segment_script(clean_script, word_timestamps)

        # Step 2: Generate rich prompts with full context
        result = self._generate_prompts(clean_script, segments, style_key)

        characters = result.get("characters", {})
        scene_prompts = result.get("scene_prompts", [])

        logger.info("prompt.complete", num_scenes=len(scene_prompts),
                    num_characters=len(characters))

        return {
            "video_id": video_id,
            "characters": characters,
            "scene_prompts": scene_prompts,
            "total_scenes": len(scene_prompts),
            "style": style_key,
        }

    def _segment_script(self, script: str, word_timestamps: list) -> list:
        """Get scene segments using visual beat segmenter."""
        from app.services.visual_beat_segmenter import segment_into_visual_beats

        result = segment_into_visual_beats(script, word_timestamps)
        segments = result.get("segments", [])

        logger.info("prompt.segments_created", count=len(segments))
        return segments

    def _generate_prompts(self, script: str, segments: list, style_key: str) -> dict:
        """Generate rich image prompts with full story context."""
        from pathlib import Path
        import yaml

        # Load prompt template
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "image_prompt_generation.yaml"
        with open(prompt_path) as f:
            prompts = yaml.safe_load(f)

        config = prompts["image_prompt_generation"]
        style_description = STYLE_MAP.get(style_key, STYLE_MAP["cinematic"])

        # Format segments for prompt
        segments_json = json.dumps(segments, indent=2)

        # Build user prompt
        user_prompt = config["user"].replace(
            "{script}", script
        ).replace(
            "{segments_json}", segments_json
        ).replace(
            "{style_description}", style_description
        )

        # Call LLM
        result = self.call_llm(
            "anthropic",
            user_prompt,
            system=config["system"],
            json_mode=True,
            max_tokens=16384,
        )

        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        # Validate and enrich prompts
        scene_prompts = self._validate_prompts(
            parsed.get("scene_prompts", []),
            parsed.get("characters", {}),
            segments
        )

        return {
            "characters": parsed.get("characters", {}),
            "scene_prompts": scene_prompts,
        }

    def _validate_prompts(self, scene_prompts: list, characters: dict,
                          segments: list) -> list:
        """Validate prompts have required fields, fill in missing data from segments."""
        validated = []

        # Build segment lookup by scene_id
        segment_lookup = {s.get("scene_id", i): s for i, s in enumerate(segments)}

        for prompt in scene_prompts:
            scene_id = prompt.get("scene_id", len(validated) + 1)
            segment = segment_lookup.get(scene_id, {})

            validated.append({
                "scene_id": scene_id,
                "start": prompt.get("start", segment.get("start", 0.0)),
                "end": prompt.get("end", segment.get("end", 5.0)),
                "narration_text": prompt.get("narration_text", segment.get("text", "")),
                "image_prompt": prompt.get("image_prompt", segment.get("visual_description", "")),
                "camera": prompt.get("camera", "Medium shot, eye level, shallow DOF"),
                "effect": prompt.get("effect", "slow_zoom_in"),
            })

        return validated
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/prompt_agent.py
git commit -m "feat: add PromptAgent for Phase 4 image prompt generation"
```

---

### Task 5: Register PromptAgent in Orchestrator Engine

**Files:**
- Modify: `app/orchestrator/engine.py:151-170`

- [ ] **Step 1: Add import for PromptAgent**

Find the `_get_agent` method and update the imports and agents dict:

```python
def _get_agent(self, agent_name: str):
    from app.agents.ideas_agent import IdeasAgent
    from app.agents.script_agent import ScriptAgent
    from app.agents.prompt_agent import PromptAgent  # NEW
    from app.agents.media_agent import MediaAgent
    from app.agents.voice_agent import VoiceAgent
    from app.agents.video_agent import VideoAgent
    from app.agents.qa_agent import QAAgent

    agents = {
        "ideas_agent": IdeasAgent,
        "script_agent": ScriptAgent,
        "prompt_agent": PromptAgent,  # NEW
        "media_agent": MediaAgent,
        "voice_agent": VoiceAgent,
        "video_agent": VideoAgent,
        "qa_agent": QAAgent,
    }
    agent_class = agents.get(agent_name)
    if not agent_class:
        raise ValueError(f"Unknown agent: {agent_name}")
    return agent_class()
```

- [ ] **Step 2: Commit**

```bash
git add app/orchestrator/engine.py
git commit -m "feat: register PromptAgent in orchestrator engine"
```

---

## Chunk 3: Update Downstream Agents

### Task 6: Update MediaAgent to Phase 5

**Files:**
- Modify: `app/agents/media_agent.py`

- [ ] **Step 1: Update phase_number**

Change line 24:
```python
class MediaAgent(BaseAgent):
    agent_name = "media_agent"
    phase_number = 5  # was 4
```

- [ ] **Step 2: Update run() to read from phase_4_output**

In the `run()` method, add reading from phase_4_output (the new Prompt phase):

```python
def run(self, input_data: dict, learning_context: list) -> dict:
    niche = input_data.get("niche", "")
    config = input_data.get("pipeline_config", {})

    # Get script data from Phase 2
    phase_2 = input_data.get("phase_2_output", {})
    script = phase_2.get("script", "")
    sections = phase_2.get("sections", [])
    title = phase_2.get("selected_title", "")
    video_id = phase_2.get("video_id")

    # Get voice data from Phase 3
    phase_3 = input_data.get("phase_3_output", {})
    word_timestamps = phase_3.get("word_timestamps", [])

    # Get prompts from Phase 4 (NEW)
    phase_4 = input_data.get("phase_4_output", {})
    scene_prompts = phase_4.get("scene_prompts", [])
    characters = phase_4.get("characters", {})

    if not script:
        raise ValueError("No script from Phase 2 — cannot collect media")

    pipeline_run_id = input_data.get("pipeline_run_id", "")
    mode = config.get("mode", "hybrid")
    style_key = config.get("style", "cinematic")
    max_scenes = config.get("max_scenes")

    logger.info("media.start", title=title, mode=mode,
                has_prompts=bool(scene_prompts), max_scenes=max_scenes)

    if mode == "story" and scene_prompts:
        # Story mode with pre-generated prompts from Phase 4
        scenes = self._build_scenes_from_prompts(scene_prompts)

        if max_scenes and len(scenes) > max_scenes:
            logger.info("media.scenes_limited", original=len(scenes), limited=max_scenes)
            scenes = scenes[:max_scenes]

        scene_clips = self._generate_story_images(scenes, pipeline_run_id, video_id, style_key)
    elif mode == "story":
        # Fallback: story mode without prompts (legacy path)
        voice_data = self._get_voice_data(input_data)
        word_timestamps = voice_data.get("word_timestamps", [])
        clean_script = voice_data.get("clean_script", script)

        if word_timestamps:
            scenes = self._segment_with_timing(clean_script, sections, word_timestamps, style_key)
        else:
            scenes = self._extract_scenes_story(sections, style_key)

        if max_scenes and len(scenes) > max_scenes:
            scenes = scenes[:max_scenes]

        scene_clips = self._generate_story_images(scenes, pipeline_run_id, video_id, style_key)
    else:
        # Hybrid mode (unchanged)
        scenes = self._extract_scenes(sections)
        if max_scenes and len(scenes) > max_scenes:
            scenes = scenes[:max_scenes]

        stock_scenes = [s for s in scenes if s.get("media_type") != "ai_image"]
        ai_scenes = [s for s in scenes if s.get("media_type") == "ai_image"]

        stock_clips = self._fetch_stock_clips(stock_scenes, pipeline_run_id, video_id) if stock_scenes else []
        ai_clips = self._generate_scene_images(ai_scenes, pipeline_run_id, video_id) if ai_scenes else []

        scene_clips = sorted(stock_clips + ai_clips, key=lambda x: x.get("scene_number", 0))

    # Generate thumbnail
    thumbnail = self._generate_thumbnail(niche, title, pipeline_run_id)

    result = {
        "video_id": video_id,
        "scenes": scenes,
        "scene_clips": scene_clips,
        "thumbnail": thumbnail,
        "total_scenes": len(scenes),
        "clips_found": sum(1 for sc in scene_clips if sc.get("clips")),
    }

    logger.info("media.complete", scenes=len(scenes), clips_found=result["clips_found"])
    return result
```

- [ ] **Step 3: Add _build_scenes_from_prompts method**

Add this new method to MediaAgent:

```python
def _build_scenes_from_prompts(self, scene_prompts: list) -> list:
    """Convert Phase 4 scene_prompts to scene format for image generation."""
    scenes = []
    for prompt in scene_prompts:
        scenes.append({
            "scene_number": prompt.get("scene_id", len(scenes) + 1),
            "media_type": "ai_image",
            "start_time": prompt.get("start", 0.0),
            "end_time": prompt.get("end", 5.0),
            "duration_seconds": round(prompt.get("end", 5.0) - prompt.get("start", 0.0), 2),
            "narration_text": prompt.get("narration_text", ""),
            "image_prompt": prompt.get("image_prompt", ""),
            "visual_description": prompt.get("image_prompt", ""),  # For compatibility
            "effect": prompt.get("effect", "slow_zoom_in"),
            "camera": prompt.get("camera", ""),
        })

    logger.info("media.scenes_from_prompts", count=len(scenes))
    return scenes
```

- [ ] **Step 4: Commit**

```bash
git add app/agents/media_agent.py
git commit -m "feat: update MediaAgent to Phase 5, read prompts from Phase 4"
```

---

### Task 7: Update VideoAgent to Phase 6

**Files:**
- Modify: `app/agents/video_agent.py:11-33`

- [ ] **Step 1: Update phase_number and phase references**

```python
class VideoAgent(BaseAgent):
    agent_name = "video_agent"
    phase_number = 6  # was 5

    def run(self, input_data: dict, learning_context: list) -> dict:
        pipeline_run_id = input_data.get("pipeline_run_id", "")
        config = input_data.get("pipeline_config", {})

        # Get data from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})  # Voice
        phase_5 = input_data.get("phase_5_output", {})  # Media (was phase_4)

        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")
        sections = phase_2.get("sections", [])

        # Phase 3 is Voice
        audio_path = phase_3.get("audio_path", "")
        audio_duration = phase_3.get("duration_seconds", 0)

        # Phase 5 is Media (was Phase 4)
        scene_clips = phase_5.get("scene_clips", [])
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/video_agent.py
git commit -m "feat: update VideoAgent to Phase 6, fix phase references"
```

---

### Task 8: Update QAAgent to Phase 7

**Files:**
- Modify: `app/agents/qa_agent.py:11-33`

- [ ] **Step 1: Update phase_number and phase references**

```python
class QAAgent(BaseAgent):
    agent_name = "qa_agent"
    phase_number = 7  # was 6

    def run(self, input_data: dict, learning_context: list) -> dict:
        pipeline_run_id = input_data.get("pipeline_run_id", "")
        config = input_data.get("pipeline_config", {})

        # Gather outputs from all previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})  # Voice
        phase_5 = input_data.get("phase_5_output", {})  # Media (was phase_4)
        phase_6 = input_data.get("phase_6_output", {})  # Video (was phase_5)

        title = phase_2.get("selected_title", "")
        description = phase_2.get("description", "")
        script = phase_2.get("script", "")
        tags = phase_2.get("tags", [])
        video_id = phase_2.get("video_id")

        # Phase 3 = Voice, Phase 5 = Media
        audio_path = phase_3.get("audio_path", "")
        thumbnail = phase_5.get("thumbnail", {})
        video_path = phase_6.get("video_path", "")
```

- [ ] **Step 2: Commit**

```bash
git add app/agents/qa_agent.py
git commit -m "feat: update QAAgent to Phase 7, fix phase references"
```

---

## Chunk 4: Frontend Updates

### Task 9: Update Frontend Phase Labels

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Search for phase label definitions and update**

Find the phase labels (likely in a PHASES constant or similar) and update:

```javascript
const PHASES = [
  { number: 1, name: "Ideas Discovery" },
  { number: 2, name: "Script Generation" },
  { number: 3, name: "Voice Generation" },
  { number: 4, name: "Prompt Generation" },   // NEW
  { number: 5, name: "Media Collection" },    // was 4
  { number: 6, name: "Video Assembly" },      // was 5
  { number: 7, name: "QA & Package" },        // was 6
];
```

- [ ] **Step 2: Update any phase number references in UI logic**

Search for hardcoded phase numbers (e.g., `phase === 6`, `currentPhase >= 5`) and increment by 1 for phases 4-6.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: update frontend for 7-phase pipeline"
```

---

## Chunk 5: Documentation & Testing

### Task 10: Update CONTEXT.md

**Files:**
- Modify: `CONTEXT.md`

- [ ] **Step 1: Update phase documentation**

Update the pipeline phases section to reflect the new 7-phase architecture:

```markdown
## Pipeline Phases

1. **Ideas Discovery** — Find trending story topics from Reddit/Perplexity
2. **Script Generation** — Write narration script with hooks/payoffs
3. **Voice Generation** — Generate TTS audio + word timestamps via ElevenLabs/Whisper
4. **Prompt Generation** — Generate rich image prompts with character consistency (NEW)
5. **Media Collection** — Generate AI images using prompts from Phase 4
6. **Video Assembly** — Stitch clips with Ken Burns effects + narration
7. **QA & Package** — Add subtitles, generate thumbnail, package metadata
```

- [ ] **Step 2: Commit**

```bash
git add CONTEXT.md
git commit -m "docs: update CONTEXT.md for 7-phase pipeline"
```

---

### Task 11: Database Migration (if needed)

- [ ] **Step 1: Check if phase_toggles table needs update**

```bash
docker compose exec web python -c "
from app import create_app, db
from app.models.phase_toggle import PhaseToggle
app = create_app()
with app.app_context():
    # Add Phase 4 toggle if missing
    existing = PhaseToggle.query.filter_by(phase_number=4).first()
    if existing and existing.phase_name != 'Prompt Generation':
        # Need to update existing toggles
        print('Need to update phase toggles')
    else:
        print('Phase toggles OK or need seeding')
"
```

- [ ] **Step 2: Run seed to add new phase toggle**

```bash
docker compose exec web python seed.py
```

- [ ] **Step 3: Verify all 7 phases exist**

```bash
docker compose exec web python -c "
from app import create_app
from app.models.phase_toggle import PhaseToggle
app = create_app()
with app.app_context():
    toggles = PhaseToggle.query.order_by(PhaseToggle.phase_number).all()
    for t in toggles:
        print(f'Phase {t.phase_number}: {t.phase_name}')
"
```

---

### Task 12: Build and Deploy

- [ ] **Step 1: Build containers**

```bash
docker compose build web worker
```

- [ ] **Step 2: Restart services**

```bash
docker compose up -d && docker compose restart worker beat
```

- [ ] **Step 3: Run seed for new phase toggle**

```bash
docker compose exec web python seed.py
```

- [ ] **Step 4: Verify deployment**

```bash
docker compose logs -f worker --tail=50
```

- [ ] **Step 5: Final commit and push**

```bash
git add -A
git commit -m "feat: complete Phase 4 (Prompt Generation) implementation"
git push railway main
```

---

## Verification Checklist

After implementation, verify:

- [ ] Pipeline runs with 7 phases
- [ ] Phase 4 generates character dict + scene_prompts
- [ ] Phase 4 pauses for approval (if requires_approval=true)
- [ ] Editing prompts in approval UI works
- [ ] Phase 5 (Media) reads prompts from phase_4_output
- [ ] Phase 6 (Video) correctly references phase_5_output
- [ ] Phase 7 (QA) correctly references phase_5 and phase_6 outputs
- [ ] Frontend shows all 7 phases correctly
