# Audio-First Architecture for Visual-Narration Alignment

**Date:** 2026-03-11
**Status:** Approved
**Goal:** Achieve 90%+ visual-narration alignment in AI-generated story videos

## Problem Statement

Current pipeline generates images BEFORE knowing exact audio timing:
```
Phase 2: Script → Phase 3: Media (images) → Phase 4: Voice → Phase 5: Assembly
```

This causes alignment issues because:
1. TTS produces variable-length audio (word pacing, pauses differ per run)
2. Images are generated based on estimated durations
3. Assembly phase must stretch/compress images to fit audio
4. Result: images display when narration has moved on, or images change mid-sentence

### Current Alignment: ~70-75%
- Prison scenes mostly match prison narration
- Some scenes show wrong content (kitchen scene during bedroom narration)
- Timing drifts as video progresses

## Solution: Audio-First Architecture

### New Phase Order
```
Phase 1: Ideas Discovery
Phase 2: Script Generation
Phase 3: Voice Generation (MOVED UP from Phase 4)
Phase 4: Media Collection (MOVED DOWN from Phase 3)
Phase 5: Video Assembly
Phase 6: QA & Package
```

### Data Flow
```
Script → Voice → Segments with timestamps → Images per segment
```

### Key Insight
Generate audio FIRST, get exact timestamps via Whisper transcription, THEN generate images that are locked to those timestamps.

## Audio Segmentation Strategy

### LLM-Guided Visual Beat Segmentation (Recommended)

Use LLM to decide "when should the image change?" rather than mechanical sentence splitting.

**Input:** Full script + Whisper word timestamps
**Output:** Scene segments with exact timing

```json
{
  "segments": [
    {"text": "The rain was falling heavily that night.", "start": 0.0, "end": 3.2, "scene_id": 1},
    {"text": "I held the baby close to my chest.", "start": 3.2, "end": 5.8, "scene_id": 1},
    {"text": "The orphanage door loomed before me.", "start": 5.8, "end": 9.1, "scene_id": 2},
    {"text": "A single lamp flickered in the window.", "start": 9.1, "end": 12.4, "scene_id": 2},
    {"text": "I knocked three times.", "start": 12.4, "end": 14.0, "scene_id": 3}
  ]
}
```

**Benefits:**
- Multiple sentences can share one image (scene_id grouping)
- Visual pacing feels natural (4-8 second scenes)
- No jarring cuts mid-thought
- Reduces total images needed (cost savings)

### Image Generation Per Scene

For each unique `scene_id`:
1. Combine all segment texts sharing that scene_id
2. Generate image prompt with `[DEPICTS: combined_narration_text]` prefix
3. Lock image to timestamp range: `start` of first segment to `end` of last segment

## Implementation Components

### 1. Phase Reordering
- Move Voice generation before Media collection in orchestrator
- Update phase dependencies in pipeline engine

### 2. Whisper Integration (Phase 3)
- After TTS generates audio, run Whisper to get word-level timestamps
- Output: `audio_path` + `word_timestamps[]`

### 3. Visual Beat Segmenter (New Component)
- Input: script sections + word timestamps
- LLM call to segment into visual beats
- Output: `segments[]` with scene_id grouping

### 4. Media Agent Update (Phase 4)
- Input now includes exact segment timing
- Generate images per unique scene_id
- Image prompts include timestamp-locked narration text

### 5. Assembly Update (Phase 5)
- No duration guessing needed
- Each image has exact start/end from segments
- Ken Burns effects applied within timestamp bounds

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Visual-narration alignment | 70-75% | 90%+ |
| Timing drift at 3min mark | 5-10s | <1s |
| Content mismatch rate | ~25% | <10% |

## Tradeoffs

- **Slightly longer pipeline:** Voice must complete before media starts
- **More complex orchestration:** New component (Visual Beat Segmenter)
- **LLM cost:** Additional call for segmentation

These are acceptable given the significant quality improvement.
