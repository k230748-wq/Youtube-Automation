"""Anthropic API integration — Claude for content writing."""

import json
import anthropic
from config.settings import settings

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def call_anthropic(
    prompt: str,
    system_prompt: str = None,
    model: str = "claude-sonnet-4-5-20250929",
    json_mode: bool = False,
    max_tokens: int = 8192,
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
                end = content.index("```", start)
                return json.loads(content[start:end].strip())
            return content

    return content
