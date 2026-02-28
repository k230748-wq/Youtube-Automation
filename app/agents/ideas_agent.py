"""Ideas Agent — discovers trending video topics for a channel."""

from app.agents.base import BaseAgent


class IdeasAgent(BaseAgent):
    agent_name = "ideas_agent"
    phase_number = 1

    def run(self, input_data: dict, learning_context: list) -> dict:
        # TODO: Implement ideas discovery
        # 1. Get channel niche from input_data
        # 2. Call SerpAPI for Google Trends
        # 3. Call YouTube Data API for trending videos
        # 4. Score and rank ideas
        # 5. Return list of ideas
        return {"ideas": [], "status": "stub"}
