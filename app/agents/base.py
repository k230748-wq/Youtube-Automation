"""Base agent class — shared logic for all pipeline agents."""

import json
from abc import ABC, abstractmethod

import structlog
import yaml

from app import db
from app.models.prompt_template import PromptTemplate
from app.models.learning import LearningLog

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all YouTube pipeline agents."""

    agent_name: str = "base"
    phase_number: int = 0

    def __init__(self):
        self.logger = structlog.get_logger(agent=self.agent_name, phase=self.phase_number)

    def execute(self, pipeline_run_id: str, input_data: dict, phase_result_id: str) -> dict:
        """Main execution method — called by the orchestrator."""
        self.logger.info("agent.execute.start", pipeline_run_id=pipeline_run_id)

        # Inject pipeline_run_id into input_data so agents can access it
        input_data["pipeline_run_id"] = pipeline_run_id

        # Store language from pipeline config for prompt injection
        self.language = input_data.get("pipeline_config", {}).get("language", "English")

        # Get relevant learning context from past runs
        learning_context = self._get_learning_context(input_data.get("niche", ""))

        # Run the agent's main logic
        result = self.run(input_data, learning_context)

        self.logger.info("agent.execute.complete", pipeline_run_id=pipeline_run_id)
        return result

    @abstractmethod
    def run(self, input_data: dict, learning_context: list) -> dict:
        """Agent-specific logic — must be implemented by each agent."""
        pass

    def get_prompt(self, template_key: str, **variables) -> str:
        """Load and render a prompt template from the database."""
        # Try database first (user-edited prompts)
        template = PromptTemplate.query.filter_by(
            template_key=template_key,
            is_active=True,
        ).order_by(PromptTemplate.version.desc()).first()

        if template:
            prompt = template.render(**variables)
        else:
            # Fall back to YAML defaults
            prompt = self._load_yaml_prompt(template_key, **variables)

        # Auto-inject language requirement for non-English pipelines
        language = getattr(self, "language", "English")
        if language and language != "English":
            prompt += (
                f"\n\nCRITICAL LANGUAGE REQUIREMENT: Write ALL content in {language}. "
                f"Every title, heading, description, sentence, and word must be in {language}. "
                f"Do not use English."
            )

        return prompt

    def _load_yaml_prompt(self, template_key: str, **variables) -> str:
        """Load a prompt from the default YAML config files."""
        import os
        prompts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config", "prompts")

        for filename in os.listdir(prompts_dir):
            if not filename.endswith(".yaml"):
                continue
            filepath = os.path.join(prompts_dir, filename)
            with open(filepath, "r") as f:
                config = yaml.safe_load(f)

            templates = config.get("templates", {})
            if template_key in templates:
                prompt = templates[template_key]
                for key, value in variables.items():
                    prompt = prompt.replace("{{" + key + "}}", str(value))
                return prompt

        raise ValueError(f"Prompt template '{template_key}' not found")

    def _get_learning_context(self, niche: str) -> list:
        """Retrieve relevant learning logs from past successful runs."""
        if not niche:
            return []

        logs = LearningLog.query.filter(
            LearningLog.niche == niche,
            LearningLog.phase_number == self.phase_number,
            LearningLog.feedback.in_(["approved", "edited"]),
        ).order_by(LearningLog.performance_score.desc().nullslast()).limit(5).all()

        return [
            {
                "output_summary": log.output_summary,
                "feedback": log.feedback,
                "performance_score": log.performance_score,
                "tags": log.tags,
            }
            for log in logs
        ]

    def call_llm(self, provider: str, prompt: str, system_prompt: str = None, json_mode: bool = True) -> dict | str:
        """Call an LLM provider (openai, anthropic, perplexity)."""
        if provider == "openai":
            from app.integrations.openai_client import call_openai
            return call_openai(prompt, system_prompt=system_prompt, json_mode=json_mode)
        elif provider == "anthropic":
            from app.integrations.anthropic_client import call_anthropic
            return call_anthropic(prompt, system_prompt=system_prompt, json_mode=json_mode)
        elif provider == "perplexity":
            from app.integrations.perplexity_client import call_perplexity
            return call_perplexity(prompt, system_prompt=system_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def parse_json_response(self, response: str) -> dict:
        """Safely parse a JSON response from an LLM."""
        if isinstance(response, (dict, list)):
            return response

        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            return json.loads(response[start:end].strip())

        if "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            return json.loads(response[start:end].strip())

        raise ValueError(f"Could not parse JSON from response: {response[:200]}")
