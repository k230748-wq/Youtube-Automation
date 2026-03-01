"""Ideas Agent — discovers trending video topics for a channel's niche."""

import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class IdeasAgent(BaseAgent):
    agent_name = "ideas_agent"
    phase_number = 1

    def run(self, input_data: dict, learning_context: list) -> dict:
        niche = input_data.get("niche", "")
        channel_id = input_data.get("channel_id")
        config = input_data.get("pipeline_config", {})

        logger.info("ideas.start", niche=niche, channel_id=channel_id)

        # Step 1: Get Google Trends data via SerpAPI
        trends_data = self._get_trends(niche)

        # Step 2: Get YouTube trending/search data
        youtube_data = self._get_youtube_data(niche)

        # Step 3: Use LLM to analyze trends and generate ranked ideas
        ideas = self._generate_ideas(niche, trends_data, youtube_data, learning_context, channel_id)

        logger.info("ideas.complete", count=len(ideas))

        return {
            "ideas": ideas,
            "trends_data_summary": trends_data.get("summary", ""),
            "youtube_data_summary": youtube_data.get("summary", ""),
            "niche": niche,
            "channel_id": channel_id,
        }

    def _get_trends(self, niche: str) -> dict:
        """Fetch Google Trends data via SerpAPI."""
        try:
            from app.integrations.serpapi_client import get_google_trends, get_related_searches, get_autocomplete

            trends = get_google_trends(niche)
            related = get_related_searches(niche)
            autocomplete = get_autocomplete(niche)

            return {
                "trends": trends,
                "related_searches": related.get("related_searches", []),
                "related_questions": related.get("related_questions", []),
                "autocomplete": autocomplete,
                "summary": f"Found {len(related.get('related_searches', []))} related searches, {len(related.get('related_questions', []))} questions",
            }
        except Exception as e:
            logger.warning("ideas.trends_failed", error=str(e))
            return {"trends": {}, "related_searches": [], "related_questions": [], "autocomplete": [], "summary": "Trends data unavailable"}

    def _get_youtube_data(self, niche: str) -> dict:
        """Fetch YouTube trending and search data."""
        try:
            from app.integrations.youtube_data_client import search_videos, get_trending

            # Search for recent videos in this niche
            search_results = search_videos(niche, max_results=10, order="date")

            # Get trending videos (general — will filter by relevance in LLM)
            trending = get_trending(max_results=10)

            return {
                "search_results": search_results,
                "trending": trending,
                "summary": f"Found {len(search_results)} niche videos, {len(trending)} trending videos",
            }
        except Exception as e:
            logger.warning("ideas.youtube_failed", error=str(e))
            return {"search_results": [], "trending": [], "summary": "YouTube data unavailable"}

    def _generate_ideas(self, niche: str, trends_data: dict, youtube_data: dict, learning_context: list, channel_id: str = None) -> list:
        """Use LLM to analyze data and generate ranked video ideas."""
        # Format trends data for the prompt
        trends_summary = []
        for q in trends_data.get("related_questions", [])[:10]:
            trends_summary.append(f"- Question: {q.get('question', q.get('title', str(q)))}")
        for s in trends_data.get("related_searches", [])[:10]:
            trends_summary.append(f"- Search: {s.get('query', str(s))}")
        for a in trends_data.get("autocomplete", [])[:10]:
            trends_summary.append(f"- Autocomplete: {a.get('value', str(a))}")

        # Format YouTube data
        yt_summary = []
        for v in youtube_data.get("search_results", [])[:10]:
            yt_summary.append(f"- [{v.get('title', 'Untitled')}] by {v.get('channel_title', 'Unknown')}")
        for v in youtube_data.get("trending", [])[:5]:
            yt_summary.append(f"- TRENDING: [{v.get('title', 'Untitled')}] ({v.get('view_count', '?')} views)")

        # Format learning context
        learning_str = ""
        if learning_context:
            learning_str = "\n\nPast successful ideas in this niche:\n"
            for ctx in learning_context[:3]:
                learning_str += f"- {ctx.get('output_summary', '')[:200]}\n"

        prompt = self.get_prompt(
            "analyze_trends",
            niche=niche,
            trends_data="\n".join(trends_summary) if trends_summary else "No trends data available — use your knowledge of current trends.",
            youtube_data="\n".join(yt_summary) if yt_summary else "No YouTube data available — use your knowledge of popular video topics.",
        )

        if learning_str:
            prompt += learning_str

        result = self.call_llm("anthropic", prompt, json_mode=True)
        parsed = self.parse_json_response(result) if isinstance(result, str) else result

        ideas = parsed.get("ideas", parsed.get("ranked_ideas", []))

        # Store ideas in the database
        self._save_ideas(ideas, niche, input_data_channel_id=channel_id)

        return ideas

    def _save_ideas(self, ideas: list, niche: str, input_data_channel_id: str = None):
        """Save generated ideas to the Ideas table."""
        try:
            from app import db
            from app.models.idea import Idea

            for idea in ideas:
                db_idea = Idea(
                    channel_id=input_data_channel_id,
                    topic=idea.get("topic", str(idea)),
                    score=idea.get("score"),
                    source="ai_generated",
                    status="pending",
                    meta_json=idea,
                )
                db.session.add(db_idea)
            db.session.commit()
        except Exception as e:
            logger.warning("ideas.save_failed", error=str(e))
