"""Script Agent — generates video scripts, titles, descriptions, and tags."""

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)

LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
}


class ScriptAgent(BaseAgent):
    agent_name = "script_agent"
    phase_number = 2

    def run(self, input_data: dict, learning_context: list) -> dict:
        niche = input_data.get("niche", "")
        channel_id = input_data.get("channel_id")
        config = input_data.get("pipeline_config", {})
        mode = config.get("mode", "hybrid")
        self.language = input_data.get("language", "en")

        # Get ideas from Phase 1 output
        phase_1 = input_data.get("phase_1_output", {})
        ideas = phase_1.get("ideas", [])

        if not ideas:
            raise ValueError("No ideas from Phase 1 — cannot generate script")

        # Pick the top idea (highest score)
        top_idea = sorted(ideas, key=lambda x: int(x.get("score", 0)) if str(x.get("score", 0)).isdigit() else 0, reverse=True)[0]
        topic = top_idea.get("topic", "")
        hook = top_idea.get("hook", "")
        try:
            target_length = int(top_idea.get("estimated_length", 10))
        except (ValueError, TypeError):
            target_length = 10
        keywords = top_idea.get("keywords", [])

        logger.info("script.start", topic=topic, target_length=target_length, mode=mode)

        # Step 1: Generate the full video script
        if mode == "story":
            story_premise = top_idea.get("story_premise", "")
            target_length = max(8, min(target_length, 15))  # Story mode 8-15 min
            script_data = self._generate_story_script(topic, hook, target_length, story_premise)
            titles = self._generate_story_titles(topic)
        else:
            script_data = self._generate_script(niche, topic, hook, target_length, learning_context)
            titles = self._generate_titles(niche, topic, keywords)

        # Step 3: Generate description and tags
        desc_data = self._generate_description(niche, topic, titles[0] if titles else topic, keywords, script_data.get("sections", []))

        # Step 4: Save video record
        video_id = self._save_video(channel_id, top_idea, titles[0] if titles else topic, desc_data, script_data)

        result = {
            "video_id": video_id,
            "topic": topic,
            "script": script_data.get("script", ""),
            "sections": script_data.get("sections", []),
            "total_estimated_duration": script_data.get("total_estimated_duration", target_length * 60),
            "titles": titles,
            "selected_title": titles[0] if titles else topic,
            "description": desc_data.get("description", ""),
            "tags": desc_data.get("tags", keywords),
            "idea_used": top_idea,
        }

        logger.info("script.complete", topic=topic, sections=len(result["sections"]))
        return result

    def _generate_script(self, niche: str, topic: str, hook: str, target_length: int, learning_context: list) -> dict:
        """Generate a full narrated video script."""
        learning_str = ""
        if learning_context:
            learning_str = "\n\nPast successful scripts in this niche (learn from these):\n"
            for ctx in learning_context[:2]:
                learning_str += f"- {ctx.get('output_summary', '')[:300]}\n"

        prompt = self.get_prompt(
            "write_script",
            niche=niche,
            topic=topic,
            hook=hook or "Create an engaging hook",
            target_length=str(target_length),
        )

        if self.language != "en":
            prompt += f"\n\nIMPORTANT: Write the ENTIRE script in {LANGUAGE_NAMES.get(self.language, self.language)}. All narration, dialogue, and section names must be in {LANGUAGE_NAMES.get(self.language, self.language)}."

        if learning_str:
            prompt += learning_str

        result = self.call_llm("anthropic", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        return {
            "script": parsed.get("script", ""),
            "sections": parsed.get("sections", []),
            "total_estimated_duration": parsed.get("total_estimated_duration", target_length * 60),
        }

    def _generate_story_script(self, topic: str, hook: str, target_length: int,
                                story_premise: str) -> dict:
        """Generate a first-person emotional narrative script for story mode (two-step)."""
        import json as _json

        # Step 1: Generate the outline (section structure, summaries, durations)
        logger.info("script.story.outline_start")
        outline_prompt = self.get_prompt(
            "write_script_story_outline",
            topic=topic,
            hook=hook or "Create an emotionally gripping opening",
            target_length=str(target_length),
            story_premise=story_premise or "Develop the full story arc from the topic.",
        )
        if self.language != "en":
            lang_name = LANGUAGE_NAMES.get(self.language, self.language)
            outline_prompt += f"\n\nIMPORTANT: Write ALL section names and summaries in {lang_name}."
        outline_result = self.call_llm("anthropic", outline_prompt, json_mode=True)
        outline_parsed = self.parse_json_response(outline_result) if isinstance(outline_result, str) else outline_result
        sections_outline = outline_parsed.get("sections", [])
        total_duration = outline_parsed.get("total_estimated_duration", target_length * 60)
        logger.info("script.story.outline_done", sections=len(sections_outline))

        # Step 2: Write the full narration given the outline
        logger.info("script.story.narrate_start")
        outline_str = _json.dumps(sections_outline, indent=2)
        narrate_prompt = self.get_prompt(
            "write_script_story_narrate",
            topic=topic,
            hook=hook or "Create an emotionally gripping opening",
            outline=outline_str,
        )
        if self.language != "en":
            lang_name = LANGUAGE_NAMES.get(self.language, self.language)
            narrate_prompt += f"\n\nIMPORTANT: Write the ENTIRE narration in {lang_name}. All dialogue, inner thoughts, and descriptions must be in {lang_name}."
        narrate_result = self.call_llm("anthropic", narrate_prompt, json_mode=True, max_tokens=8192)
        narrate_parsed = self.parse_json_response(narrate_result) if isinstance(narrate_result, str) else narrate_result
        logger.info("script.story.narrate_done")

        # Merge outline durations into narration sections and build full script
        narrated_sections = narrate_parsed.get("sections", [])
        script_parts = []
        for i, section in enumerate(narrated_sections):
            if i < len(sections_outline):
                section["duration_estimate"] = sections_outline[i].get("duration_estimate", 120)
            else:
                section.setdefault("duration_estimate", 120)
            script_parts.append(section.get("text", ""))

        return {
            "script": "\n\n".join(script_parts),
            "sections": narrated_sections,
            "total_estimated_duration": total_duration,
        }

    def _generate_story_titles(self, topic: str) -> list:
        """Generate emotional first-person titles for story mode."""
        prompt = self.get_prompt("generate_title_story", topic=topic)
        if self.language != "en":
            prompt += f"\n\nIMPORTANT: Write ALL titles in {LANGUAGE_NAMES.get(self.language, self.language)}."

        result = self.call_llm("openai", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        titles = parsed.get("titles", [])
        return titles if titles else [topic]

    def _generate_titles(self, niche: str, topic: str, keywords: list) -> list:
        """Generate YouTube title options."""
        prompt = self.get_prompt(
            "generate_title",
            niche=niche,
            topic=topic,
        )
        if self.language != "en":
            prompt += f"\n\nIMPORTANT: Write ALL titles in {LANGUAGE_NAMES.get(self.language, self.language)}."

        result = self.call_llm("openai", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        titles = parsed.get("titles", [])
        return titles if titles else [topic]

    def _generate_description(self, niche: str, topic: str, title: str, keywords: list, sections: list) -> dict:
        """Generate YouTube description and tags."""
        # Format sections for timestamp generation
        sections_str = ""
        cumulative_time = 0
        for s in sections:
            minutes = cumulative_time // 60
            seconds = cumulative_time % 60
            sections_str += f"{minutes:02d}:{seconds:02d} - {s.get('name', 'Section')}\n"
            cumulative_time += s.get("duration_estimate", 120)

        prompt = self.get_prompt(
            "generate_description",
            title=title,
            topic=topic,
            keywords=", ".join(keywords) if keywords else niche,
            sections=sections_str if sections_str else "No timestamps available",
        )
        if self.language != "en":
            prompt += f"\n\nIMPORTANT: Write the description in {LANGUAGE_NAMES.get(self.language, self.language)}."

        result = self.call_llm("openai", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        return {
            "description": parsed.get("description", ""),
            "tags": parsed.get("tags", keywords),
        }

    def _save_video(self, channel_id: str, idea: dict, title: str, desc_data: dict, script_data: dict) -> str:
        """Create a Video record in the database."""
        try:
            from app import db
            from app.models.video import Video

            video = Video(
                channel_id=channel_id,
                title=title,
                description=desc_data.get("description", ""),
                script_text=script_data.get("script", ""),
                tags_list=desc_data.get("tags", []),
                status="draft",
                pipeline_run_id=None,  # will be set by orchestrator if needed
            )
            db.session.add(video)
            db.session.commit()

            logger.info("script.video_saved", video_id=video.id, title=title)
            return video.id
        except Exception as e:
            logger.warning("script.save_failed", error=str(e))
            return None
