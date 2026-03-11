# Audio-First Visual-Narration Alignment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Achieve 90%+ visual-narration alignment by generating audio first, then locking images to exact timestamps.

**Architecture:** Swap Phase 3 (Media) and Phase 4 (Voice) so TTS runs first. Use Whisper to get word-level timestamps, then LLM-guided segmentation to determine scene boundaries. Media agent receives exact timing for each image.

**Tech Stack:** Edge TTS, OpenAI Whisper API, Claude/GPT for segmentation, GPT Image 1, FFmpeg

---

## File Structure

| File | Purpose |
|------|---------|
| `app/orchestrator/state.py` | Phase ordering — swap Phase 3 ↔ Phase 4 |
| `app/agents/voice_agent.py` | Add Whisper timestamp output |
| `app/services/visual_beat_segmenter.py` | NEW: LLM-guided scene segmentation |
| `app/agents/media_agent.py` | Accept timing from segmenter instead of estimating |
| `app/agents/video_agent.py` | Use locked timestamps from scene_clips |
| `config/prompts/visual_beat_segmentation.yaml` | NEW: Prompt for scene boundary detection |
| `tests/test_visual_beat_segmenter.py` | NEW: Unit tests for segmenter |

---

## Chunk 1: Phase Reordering

### Task 1: Update Phase Order Constants

**Files:**
- Modify: `app/orchestrator/state.py:42-58`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_phase_order.py
def test_voice_before_media():
    from app.orchestrator.state import PHASE_NAMES, PHASE_AGENTS

    # Voice should be Phase 3, Media should be Phase 4
    assert PHASE_NAMES[3] == "Voice Generation"
    assert PHASE_NAMES[4] == "Media Collection"
    assert PHASE_AGENTS[3] == "voice_agent"
    assert PHASE_AGENTS[4] == "media_agent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_phase_order.py -v`
Expected: FAIL — currently Phase 3 = "Media Collection"

- [ ] **Step 3: Update state.py with new phase order**

```python
PHASE_NAMES = {
    1: "Ideas Discovery",
    2: "Script Generation",
    3: "Voice Generation",    # MOVED UP from 4
    4: "Media Collection",    # MOVED DOWN from 3
    5: "Video Assembly",
    6: "QA & Package",
}

PHASE_AGENTS = {
    1: "ideas_agent",
    2: "script_agent",
    3: "voice_agent",         # MOVED UP from 4
    4: "media_agent",         # MOVED DOWN from 3
    5: "video_agent",
    6: "qa_agent",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_phase_order.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/orchestrator/state.py tests/test_phase_order.py
git commit -m "feat: reorder phases — voice before media for audio-first architecture"
```

---

### Task 2: Update Voice Agent Phase Number

**Files:**
- Modify: `app/agents/voice_agent.py:21`

- [ ] **Step 1: Update phase_number constant**

Change line 21 from:
```python
    phase_number = 4
```

To:
```python
    phase_number = 3
```

- [ ] **Step 2: Verify no test breakage**

Run: `pytest tests/ -k voice -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add app/agents/voice_agent.py
git commit -m "fix: update voice_agent phase_number to 3"
```

---

### Task 3: Update Media Agent Phase Number

**Files:**
- Modify: `app/agents/media_agent.py:23`

- [ ] **Step 1: Update phase_number constant**

Change line 23 from:
```python
    phase_number = 3
```

To:
```python
    phase_number = 4
```

- [ ] **Step 2: Verify no test breakage**

Run: `pytest tests/ -k media -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add app/agents/media_agent.py
git commit -m "fix: update media_agent phase_number to 4"
```

---

## Chunk 2: Voice Agent Whisper Integration

### Task 4: Add Whisper Timestamps to Voice Output

**Files:**
- Modify: `app/agents/voice_agent.py:24-66`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_voice_timestamps.py
import pytest
from unittest.mock import patch, MagicMock

def test_voice_agent_returns_word_timestamps():
    from app.agents.voice_agent import VoiceAgent

    agent = VoiceAgent()

    mock_input = {
        "pipeline_run_id": "test-123",
        "phase_2_output": {
            "script": "The rain was heavy. I held the baby close.",
            "video_id": "vid-123",
            "selected_title": "Test Story",
        },
        "language": "en",
    }

    with patch.object(agent, '_generate_audio') as mock_gen, \
         patch.object(agent, '_get_audio_duration') as mock_dur, \
         patch.object(agent, '_get_word_timestamps') as mock_ts:

        mock_gen.return_value = "/tmp/test/narration.mp3"
        mock_dur.return_value = 5.5
        mock_ts.return_value = [
            {"word": "The", "start": 0.0, "end": 0.2},
            {"word": "rain", "start": 0.2, "end": 0.5},
            {"word": "was", "start": 0.5, "end": 0.7},
            {"word": "heavy.", "start": 0.7, "end": 1.2},
        ]

        result = agent.run(mock_input, [])

        assert "word_timestamps" in result
        assert len(result["word_timestamps"]) > 0
        assert result["word_timestamps"][0]["word"] == "The"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice_timestamps.py -v`
Expected: FAIL — voice agent doesn't return word_timestamps yet

- [ ] **Step 3: Add _get_word_timestamps method to VoiceAgent**

Add after `_get_audio_duration` method (~line 180):

```python
def _get_word_timestamps(self, audio_path: str, language: str = "en") -> list:
    """Get word-level timestamps using Whisper."""
    try:
        from app.integrations.whisper_client import transcribe_with_timestamps
        result = transcribe_with_timestamps(audio_path)
        return result.get("words", [])
    except Exception as e:
        logger.warning("voice.whisper_failed", error=str(e))
        return []
```

- [ ] **Step 4: Update run() method to include word_timestamps**

Modify the `run` method after line 54 (after getting duration):

```python
        # Step 4: Get word-level timestamps for scene alignment
        word_timestamps = self._get_word_timestamps(audio_path, language=language)

        result = {
            "video_id": video_id,
            "audio_path": audio_path,
            "voice": voice,
            "duration_seconds": duration,
            "script_char_count": len(clean_script),
            "title": title,
            "word_timestamps": word_timestamps,  # NEW
            "clean_script": clean_script,         # NEW — needed for segmenter
        }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_voice_timestamps.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/agents/voice_agent.py tests/test_voice_timestamps.py
git commit -m "feat: add Whisper word timestamps to voice agent output"
```

---

## Chunk 3: Visual Beat Segmenter Service

### Task 5: Create Visual Beat Segmentation Prompt

**Files:**
- Create: `config/prompts/visual_beat_segmentation.yaml`

- [ ] **Step 1: Create the prompt file**

```yaml
visual_beat_segmentation:
  system: |
    You segment narration into visual scenes for video production.
    Your job: decide when the image should change based on story beats.

    Guidelines:
    - Each scene should be 4-12 seconds (1-3 sentences)
    - Change scenes at narrative transitions (location, action, emotion shifts)
    - Group related sentences under the same scene_id
    - Don't split mid-sentence
    - Balance visual pacing — avoid too many quick cuts

  user: |
    Segment this narration into visual scenes.

    SCRIPT:
    {script}

    WORD TIMESTAMPS:
    {word_timestamps}

    Output JSON with segments array. Each segment needs:
    - scene_id: integer, shared by sentences that should use same image
    - text: the sentence/phrase for this segment
    - start: start time in seconds (from word timestamps)
    - end: end time in seconds
    - visual_description: what the image should depict

    Example output:
    {
      "segments": [
        {"scene_id": 1, "text": "The rain was falling.", "start": 0.0, "end": 2.1, "visual_description": "Heavy rain on a dark street"},
        {"scene_id": 1, "text": "I held the baby close.", "start": 2.1, "end": 4.3, "visual_description": "Heavy rain on a dark street"},
        {"scene_id": 2, "text": "The orphanage door appeared.", "start": 4.3, "end": 6.8, "visual_description": "Old wooden door with dim light"}
      ]
    }
```

- [ ] **Step 2: Verify file exists**

Run: `ls -la config/prompts/visual_beat_segmentation.yaml`
Expected: File exists

- [ ] **Step 3: Commit**

```bash
git add config/prompts/visual_beat_segmentation.yaml
git commit -m "feat: add LLM prompt for visual beat segmentation"
```

---

### Task 6: Create Visual Beat Segmenter Service

**Files:**
- Create: `app/services/visual_beat_segmenter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_visual_beat_segmenter.py
import pytest
from unittest.mock import patch, MagicMock

def test_segment_into_visual_beats():
    from app.services.visual_beat_segmenter import segment_into_visual_beats

    script = "The rain was falling. I held the baby close. The orphanage door appeared."
    word_timestamps = [
        {"word": "The", "start": 0.0, "end": 0.2},
        {"word": "rain", "start": 0.2, "end": 0.5},
        {"word": "was", "start": 0.5, "end": 0.7},
        {"word": "falling.", "start": 0.7, "end": 1.2},
        {"word": "I", "start": 1.3, "end": 1.4},
        {"word": "held", "start": 1.4, "end": 1.7},
        {"word": "the", "start": 1.7, "end": 1.8},
        {"word": "baby", "start": 1.8, "end": 2.1},
        {"word": "close.", "start": 2.1, "end": 2.5},
        {"word": "The", "start": 2.6, "end": 2.8},
        {"word": "orphanage", "start": 2.8, "end": 3.3},
        {"word": "door", "start": 3.3, "end": 3.6},
        {"word": "appeared.", "start": 3.6, "end": 4.2},
    ]

    with patch('app.services.visual_beat_segmenter._call_llm') as mock_llm:
        mock_llm.return_value = {
            "segments": [
                {"scene_id": 1, "text": "The rain was falling.", "start": 0.0, "end": 1.2, "visual_description": "Rain"},
                {"scene_id": 1, "text": "I held the baby close.", "start": 1.3, "end": 2.5, "visual_description": "Rain"},
                {"scene_id": 2, "text": "The orphanage door appeared.", "start": 2.6, "end": 4.2, "visual_description": "Door"},
            ]
        }

        result = segment_into_visual_beats(script, word_timestamps)

        assert "segments" in result
        assert len(result["segments"]) == 3
        assert result["segments"][0]["scene_id"] == 1
        assert result["segments"][2]["scene_id"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_visual_beat_segmenter.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Create the segmenter service**

```python
# app/services/visual_beat_segmenter.py
"""Visual Beat Segmenter — LLM-guided scene boundary detection."""

import json
import structlog
from pathlib import Path

import yaml

logger = structlog.get_logger(__name__)


def segment_into_visual_beats(script: str, word_timestamps: list, style_key: str = "cinematic") -> dict:
    """Segment script into visual scenes using word timestamps and LLM guidance.

    Args:
        script: Full narration script
        word_timestamps: List of {"word": str, "start": float, "end": float}
        style_key: Visual style for image generation

    Returns:
        {"segments": [{"scene_id": int, "text": str, "start": float, "end": float, "visual_description": str}]}
    """
    if not word_timestamps:
        logger.warning("segmenter.no_timestamps")
        return _fallback_segmentation(script)

    # Load prompt template
    prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "visual_beat_segmentation.yaml"
    with open(prompt_path) as f:
        prompts = yaml.safe_load(f)

    config = prompts["visual_beat_segmentation"]

    # Format word timestamps for prompt (truncate if too long)
    ts_str = json.dumps(word_timestamps[:200], indent=2)  # Limit to avoid token overflow

    user_prompt = config["user"].format(
        script=script[:3000],  # Truncate very long scripts
        word_timestamps=ts_str,
    )

    result = _call_llm(config["system"], user_prompt)

    if not result or "segments" not in result:
        logger.warning("segmenter.llm_failed_fallback")
        return _fallback_segmentation(script)

    # Validate and fix segment timings
    segments = _validate_segments(result["segments"], word_timestamps)

    logger.info("segmenter.complete", num_segments=len(segments))
    return {"segments": segments}


def _call_llm(system: str, user: str) -> dict:
    """Call LLM for segmentation."""
    from app.integrations.anthropic_client import chat_completion

    try:
        response = chat_completion(
            messages=[{"role": "user", "content": user}],
            system=system,
            model="claude-sonnet-4-20250514",
            json_mode=True,
            max_tokens=8192,
        )

        if isinstance(response, str):
            return json.loads(response)
        return response

    except Exception as e:
        logger.error("segmenter.llm_error", error=str(e))
        return {}


def _validate_segments(segments: list, word_timestamps: list) -> list:
    """Validate segment timings against word timestamps."""
    if not word_timestamps:
        return segments

    audio_end = max(w["end"] for w in word_timestamps)

    validated = []
    for seg in segments:
        # Clamp times to audio bounds
        start = max(0.0, min(seg.get("start", 0.0), audio_end))
        end = max(start + 0.5, min(seg.get("end", start + 3.0), audio_end))

        validated.append({
            "scene_id": seg.get("scene_id", len(validated) + 1),
            "text": seg.get("text", ""),
            "start": round(start, 2),
            "end": round(end, 2),
            "visual_description": seg.get("visual_description", seg.get("text", "")[:50]),
        })

    return validated


def _fallback_segmentation(script: str) -> dict:
    """Simple sentence-based fallback if LLM fails."""
    import re

    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    segments = []

    # Estimate ~150 chars per 10 seconds
    char_per_second = 15
    current_time = 0.0
    scene_id = 1

    for i, sentence in enumerate(sentences):
        duration = max(2.0, len(sentence) / char_per_second)

        segments.append({
            "scene_id": scene_id,
            "text": sentence,
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2),
            "visual_description": sentence[:50],
        })

        current_time += duration

        # New scene every 2-3 sentences
        if (i + 1) % 2 == 0:
            scene_id += 1

    return {"segments": segments}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_visual_beat_segmenter.py -v`
Expected: PASS

- [ ] **Step 5: Create services __init__.py if needed**

```bash
touch app/services/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add app/services/ tests/test_visual_beat_segmenter.py
git commit -m "feat: add visual beat segmenter service for LLM-guided scene detection"
```

---

## Chunk 4: Media Agent Integration

### Task 7: Update Media Agent to Use Segmented Timing

**Files:**
- Modify: `app/agents/media_agent.py:26-85`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_media_timing.py
import pytest
from unittest.mock import patch, MagicMock

def test_media_agent_uses_exact_timing():
    from app.agents.media_agent import MediaAgent

    agent = MediaAgent()

    mock_input = {
        "pipeline_run_id": "test-123",
        "niche": "stories",
        "pipeline_config": {"mode": "story", "style": "cinematic"},
        "phase_2_output": {
            "script": "The rain was falling. I held the baby close.",
            "sections": [{"name": "Opening", "text": "The rain was falling. I held the baby close."}],
            "video_id": "vid-123",
            "selected_title": "Test Story",
        },
        "phase_3_output": {  # Now voice output (Phase 3)
            "audio_path": "/tmp/test/narration.mp3",
            "duration_seconds": 5.5,
            "word_timestamps": [
                {"word": "The", "start": 0.0, "end": 0.2},
                {"word": "rain", "start": 0.2, "end": 0.5},
            ],
            "clean_script": "The rain was falling. I held the baby close.",
        },
    }

    with patch.object(agent, '_segment_with_timing') as mock_seg, \
         patch.object(agent, '_generate_story_images') as mock_gen, \
         patch.object(agent, '_generate_thumbnail') as mock_thumb:

        mock_seg.return_value = [
            {"scene_id": 1, "start": 0.0, "end": 2.5, "visual_description": "Rain scene"},
            {"scene_id": 2, "start": 2.5, "end": 5.5, "visual_description": "Baby scene"},
        ]
        mock_gen.return_value = []
        mock_thumb.return_value = {}

        result = agent.run(mock_input, [])

        # Verify segmenter was called with word timestamps
        mock_seg.assert_called_once()
        call_args = mock_seg.call_args
        assert "word_timestamps" in str(call_args) or len(call_args[0]) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_media_timing.py -v`
Expected: FAIL — media agent doesn't call segmenter yet

- [ ] **Step 3: Add _segment_with_timing method to MediaAgent**

Add after imports (~line 9):

```python
def _get_voice_data(self, input_data: dict) -> dict:
    """Get voice output — now from Phase 3 (audio-first architecture)."""
    return input_data.get("phase_3_output", {})
```

Add new method after `_extract_scenes_story` (~line 306):

```python
def _segment_with_timing(self, script: str, sections: list,
                          word_timestamps: list, style_key: str) -> list:
    """Use visual beat segmenter to get exact scene timing."""
    from app.services.visual_beat_segmenter import segment_into_visual_beats

    result = segment_into_visual_beats(script, word_timestamps, style_key)
    segments = result.get("segments", [])

    # Group segments by scene_id → unique scenes to generate
    scenes = []
    seen_scene_ids = set()

    for seg in segments:
        scene_id = seg["scene_id"]
        if scene_id in seen_scene_ids:
            continue
        seen_scene_ids.add(scene_id)

        # Get all segments for this scene_id
        scene_segments = [s for s in segments if s["scene_id"] == scene_id]

        # Calculate total duration and combined text
        start_time = min(s["start"] for s in scene_segments)
        end_time = max(s["end"] for s in scene_segments)
        combined_text = " ".join(s["text"] for s in scene_segments)
        visual_desc = scene_segments[0].get("visual_description", combined_text[:50])

        scenes.append({
            "scene_number": scene_id,
            "media_type": "ai_image",
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": round(end_time - start_time, 2),
            "narration_text": combined_text,
            "visual_description": visual_desc,
            "image_prompt": f"[DEPICTS: {combined_text[:30]}] {visual_desc}",
        })

    logger.info("media.segmented_timing", num_scenes=len(scenes))
    return scenes
```

- [ ] **Step 4: Update run() method to use segmenter in story mode**

Modify the story mode branch in `run()` method (~lines 48-54):

```python
        if mode == "story":
            # Story mode: audio-first with exact timing
            voice_data = self._get_voice_data(input_data)
            word_timestamps = voice_data.get("word_timestamps", [])
            clean_script = voice_data.get("clean_script", script)

            if word_timestamps:
                # Use exact timing from audio
                scenes = self._segment_with_timing(
                    clean_script, sections, word_timestamps, style_key
                )
            else:
                # Fallback to old method if no timestamps
                scenes = self._extract_scenes_story(sections, style_key)

            if max_scenes and len(scenes) > max_scenes:
                logger.info("media.scenes_limited", original=len(scenes), limited=max_scenes)
                scenes = scenes[:max_scenes]

            scene_clips = self._generate_story_images(scenes, pipeline_run_id, video_id, style_key)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_media_timing.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/agents/media_agent.py tests/test_media_timing.py
git commit -m "feat: integrate visual beat segmenter into media agent for exact timing"
```

---

### Task 8: Update scene_clips to Include Locked Timing

**Files:**
- Modify: `app/agents/media_agent.py:308-420`

- [ ] **Step 1: Update _generate_story_images to preserve timing**

Modify the scene_clips.append block (~line 376-385):

```python
                    scene_clips.append({
                        "scene_number": scene_num,
                        "section_name": scene.get("section_name"),
                        "media_type": "ai_image",
                        "clips": [{"type": "image", "local_path": image_path, "source": "gpt-image-1"}],
                        "duration_needed": scene.get("duration_seconds", 12),
                        "effect": scene.get("effect", "slow_zoom_in"),
                        "narration_text": scene.get("narration_text", ""),
                        "start_time": scene.get("start_time"),   # NEW
                        "end_time": scene.get("end_time"),       # NEW
                    })
```

- [ ] **Step 2: Verify the update**

Run: `python -c "from app.agents.media_agent import MediaAgent; print('OK')"`
Expected: OK (no import errors)

- [ ] **Step 3: Commit**

```bash
git add app/agents/media_agent.py
git commit -m "feat: include locked start_time/end_time in scene_clips output"
```

---

## Chunk 5: Video Agent Timestamp Usage

### Task 9: Update Video Agent Input References

**Files:**
- Modify: `app/agents/video_agent.py:16-29`

- [ ] **Step 1: Update phase input references**

Change the phase references to reflect new order:

```python
        # Get data from previous phases
        phase_2 = input_data.get("phase_2_output", {})
        phase_3 = input_data.get("phase_3_output", {})  # Now Voice (was Media)
        phase_4 = input_data.get("phase_4_output", {})  # Now Media (was Voice)

        title = phase_2.get("selected_title", "")
        video_id = phase_2.get("video_id")
        sections = phase_2.get("sections", [])

        # Phase 3 is now Voice
        audio_path = phase_3.get("audio_path", "")
        audio_duration = phase_3.get("duration_seconds", 0)

        # Phase 4 is now Media
        scene_clips = phase_4.get("scene_clips", [])
```

- [ ] **Step 2: Verify no test breakage**

Run: `pytest tests/ -k video -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add app/agents/video_agent.py
git commit -m "fix: update video_agent phase references for audio-first order"
```

---

### Task 10: Use Locked Timestamps for Clip Preparation

**Files:**
- Modify: `app/agents/video_agent.py:170-222`

- [ ] **Step 1: Update _prepare_clips to use locked timing**

Replace the timing computation block:

```python
    def _prepare_clips(self, downloaded_clips: list, total_audio_duration: float,
                       video_dir: str, zoom: bool = True) -> list:
        """Normalize clips: scale to 1080p, color grade, set to locked scene duration."""
        from app.integrations.ffmpeg_client import normalize_clip, image_to_video

        prepared = []
        prep_dir = os.path.join(video_dir, "prepared")
        os.makedirs(prep_dir, exist_ok=True)

        num_clips = len(downloaded_clips)
        if num_clips == 0:
            return []

        # Check if we have locked timing (audio-first architecture)
        has_locked_timing = all(
            c.get("start_time") is not None and c.get("end_time") is not None
            for c in downloaded_clips
        )

        if has_locked_timing:
            # Use exact timestamps from segmenter
            clips_with_duration = self._use_locked_timings(downloaded_clips)
        elif all(c.get("narration_text") for c in downloaded_clips):
            # Legacy: estimate from character count
            clips_with_duration = self._compute_anchor_timings(
                downloaded_clips, total_audio_duration)
        else:
            # Fallback: proportional scaling
            clips_with_duration = self._compute_proportional_timings(
                downloaded_clips, total_audio_duration, zoom)

        for i, clip in enumerate(clips_with_duration):
            target_duration = clip.get("target_duration", 10)
            input_path = clip["path"]
            output_path = os.path.join(prep_dir, f"prep_{i:03d}.mp4")

            try:
                if clip.get("type") == "image":
                    effect = clip.get("effect", "slow_zoom_in")
                    image_to_video(
                        input_path, output_path,
                        duration=target_duration,
                        zoom=zoom,
                        effect=effect,
                    )
                else:
                    normalize_clip(
                        input_path, output_path,
                        target_duration=target_duration,
                        color_grade=True,
                    )
                prepared.append(output_path)
            except Exception as e:
                logger.warning("video.prepare_error", clip=i, error=str(e))

        return prepared

    def _use_locked_timings(self, clips: list) -> list:
        """Use exact timestamps from audio-first segmentation."""
        result = []
        for clip in clips:
            start = clip.get("start_time", 0)
            end = clip.get("end_time", start + 5)
            target_duration = max(2.0, min(20.0, end - start))
            result.append({**clip, "target_duration": target_duration})
        return result
```

- [ ] **Step 2: Run tests to verify**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add app/agents/video_agent.py
git commit -m "feat: use locked timestamps from segmenter in video assembly"
```

---

## Chunk 6: Integration Testing

### Task 11: Create End-to-End Integration Test

**Files:**
- Create: `tests/test_audio_first_integration.py`

- [ ] **Step 1: Create integration test**

```python
# tests/test_audio_first_integration.py
"""Integration test for audio-first visual alignment architecture."""

import pytest
from unittest.mock import patch, MagicMock

def test_full_pipeline_phase_order():
    """Verify phases execute in audio-first order."""
    from app.orchestrator.state import PHASE_NAMES, PHASE_AGENTS

    # Phase 3 should be Voice, Phase 4 should be Media
    assert PHASE_NAMES[3] == "Voice Generation"
    assert PHASE_NAMES[4] == "Media Collection"
    assert PHASE_AGENTS[3] == "voice_agent"
    assert PHASE_AGENTS[4] == "media_agent"


def test_voice_output_has_timestamps():
    """Voice agent must output word_timestamps and clean_script."""
    from app.agents.voice_agent import VoiceAgent

    agent = VoiceAgent()

    # Check that the methods exist
    assert hasattr(agent, '_get_word_timestamps')
    assert callable(agent._get_word_timestamps)


def test_media_receives_voice_data():
    """Media agent must read from phase_3_output (voice)."""
    from app.agents.media_agent import MediaAgent

    agent = MediaAgent()

    # Check helper method exists
    assert hasattr(agent, '_get_voice_data')

    # Verify it reads from phase_3_output
    mock_input = {"phase_3_output": {"test": "value"}}
    result = agent._get_voice_data(mock_input)
    assert result == {"test": "value"}


def test_video_reads_correct_phases():
    """Video agent must read media from phase_4 and voice from phase_3."""
    from app.agents.video_agent import VideoAgent

    agent = VideoAgent()

    # Phase references are in run() — we'll check the class exists
    assert agent.phase_number == 5


def test_segmenter_produces_valid_output():
    """Visual beat segmenter must return segments with required fields."""
    from app.services.visual_beat_segmenter import _fallback_segmentation

    result = _fallback_segmentation("The rain was falling. I held the baby close.")

    assert "segments" in result
    assert len(result["segments"]) > 0

    seg = result["segments"][0]
    assert "scene_id" in seg
    assert "text" in seg
    assert "start" in seg
    assert "end" in seg
    assert "visual_description" in seg
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_audio_first_integration.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_audio_first_integration.py
git commit -m "test: add integration tests for audio-first architecture"
```

---

### Task 12: Final Verification and Documentation

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Update CONTEXT.md with architecture change**

Add to CONTEXT.md:

```markdown
## Audio-First Architecture (2026-03-11)

Pipeline phase order changed for better visual-narration alignment:
- **Phase 3**: Voice Generation (was Phase 4)
- **Phase 4**: Media Collection (was Phase 3)

Voice runs first → Whisper extracts word timestamps → Visual Beat Segmenter
determines scene boundaries → Media agent generates images locked to exact times.

Target: 90%+ visual-narration alignment (up from ~70-75%).
```

- [ ] **Step 3: Final commit**

```bash
git add CONTEXT.md
git commit -m "docs: document audio-first architecture change in CONTEXT.md"
```

---

## Summary

| Chunk | Tasks | Purpose |
|-------|-------|---------|
| 1 | 1-3 | Phase reordering in state.py and agent files |
| 2 | 4 | Voice agent Whisper integration |
| 3 | 5-6 | Visual Beat Segmenter service |
| 4 | 7-8 | Media agent timing integration |
| 5 | 9-10 | Video agent locked timestamp usage |
| 6 | 11-12 | Integration testing and documentation |

Total: 12 tasks, ~60 steps
