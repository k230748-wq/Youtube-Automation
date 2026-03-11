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

    # Format word timestamps for prompt
    # For 8-min audio (~1200 words), we need all timestamps
    # Claude can handle ~100k tokens, so 1200 words is fine
    ts_str = json.dumps(word_timestamps, indent=2)

    # Replace placeholders in prompt (avoid format() due to JSON example in prompt)
    # Full script for 8-min video is ~1200 words (~7000 chars) - well within limits
    user_prompt = config["user"].replace("{script}", script).replace("{word_timestamps}", ts_str)

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
