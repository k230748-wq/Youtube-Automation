"""Anthropic API integration — Claude for content writing."""

import json
import anthropic
from config.settings import settings

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=1800.0,
        )
    return _client


def call_anthropic(
    prompt: str,
    system_prompt: str = None,
    model: str = "claude-sonnet-4-5-20250929",
    json_mode: bool = False,
    max_tokens: int = 16384,
    temperature: float = 0.7,
) -> str | dict:
    """Call Anthropic Claude API."""
    client = _get_client()

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }

    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)
    content = response.content[0].text

    if json_mode:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try extracting from code blocks
            if "```json" in content:
                start = content.index("```json") + 7
                try:
                    end = content.index("```", start)
                except ValueError:
                    end = len(content)
                return json.loads(content[start:end].strip())
            # Try finding raw JSON object
            first_brace = content.find("{")
            last_brace = content.rfind("}")
            if first_brace != -1 and last_brace > first_brace:
                return json.loads(content[first_brace:last_brace + 1])
            return content

    return content
