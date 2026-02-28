"""Script Agent — generates video scripts, titles, descriptions, and tags."""

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class ScriptAgent(BaseAgent):
    agent_name = "script_agent"
    phase_number = 2

    def run(self, input_data: dict, learning_context: list) -> dict:
        niche = input_data.get("niche", "")
        channel_id = input_data.get("channel_id")
        config = input_data.get("pipeline_config", {})

        # Get ideas from Phase 1 output
        phase_1 = input_data.get("phase_1_output", {})
        ideas = phase_1.get("ideas", [])

        if not ideas:
            raise ValueError("No ideas from Phase 1 — cannot generate script")

        # Pick the top idea (highest score)
        top_idea = sorted(ideas, key=lambda x: x.get("score", 0), reverse=True)[0]
        topic = top_idea.get("topic", "")
        hook = top_idea.get("hook", "")
        target_length = top_idea.get("estimated_length", 10)
        keywords = top_idea.get("keywords", [])

        logger.info("script.start", topic=topic, target_length=target_length)

        # Step 1: Generate the full video script
        script_data = self._generate_script(niche, topic, hook, target_length, learning_context)

        # Step 2: Generate title options
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

        if learning_str:
            prompt += learning_str

        result = self.call_llm("anthropic", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        return {
            "script": parsed.get("script", ""),
            "sections": parsed.get("sections", []),
            "total_estimated_duration": parsed.get("total_estimated_duration", target_length * 60),
        }

    def _generate_titles(self, niche: str, topic: str, keywords: list) -> list:
        """Generate YouTube title options."""
        prompt = self.get_prompt(
            "generate_title",
            niche=niche,
            topic=topic,
        )

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
