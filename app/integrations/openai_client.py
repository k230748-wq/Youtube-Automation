"""OpenAI API integration — GPT-4o for analysis and structuring."""

import json
from openai import OpenAI
from config.settings import settings

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def call_openai(
    prompt: str,
    system_prompt: str = None,
    model: str = "gpt-4o",
    json_mode: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str | dict:
    """Call OpenAI API with a prompt."""
    client = _get_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    if json_mode:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content

    return content
