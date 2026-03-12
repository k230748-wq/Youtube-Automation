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
            system_prompt=config["system"],
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
