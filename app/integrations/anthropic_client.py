"""Anthropic API integration — Claude for content writing."""

import json
import re
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
        return _parse_json_robust(content)

    return content


def _repair_json(text: str) -> str:
    """Repair common JSON issues from LLM output."""
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # Try to close truncated JSON — count open/close brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    # If truncated mid-string, close the string first
    if open_braces > 0 or open_brackets > 0:
        # Check if we're inside an unclosed string
        stripped = text.rstrip()
        if stripped and stripped[-1] not in '"}],':
            # Likely truncated mid-value — close the string
            text = text.rstrip()
            if text[-1] == '\\':
                text = text[:-1]
            text += '"'
    # Close remaining open brackets/braces
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    text += ']' * max(0, open_brackets)
    text += '}' * max(0, open_braces)
    return text


def chat_completion(
    messages: list,
    system: str = None,
    model: str = "claude-sonnet-4-5-20250929",
    json_mode: bool = False,
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> str | dict:
    """Chat completion wrapper for messages-style API calls."""
    # Extract user message from messages list
    user_content = ""
    for msg in messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break

    return call_anthropic(
        prompt=user_content,
        system_prompt=system,
        model=model,
        json_mode=json_mode,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def _parse_json_robust(content: str) -> dict:
    """Parse JSON with multiple fallback strategies."""
    # Strategy 1: Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code blocks
    if "```json" in content:
        start = content.index("```json") + 7
        try:
            end = content.index("```", start)
        except ValueError:
            end = len(content)
        extracted = content[start:end].strip()
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            # Try repairing the extracted JSON
            try:
                return json.loads(_repair_json(extracted))
            except json.JSONDecodeError:
                pass

    # Strategy 3: Find raw JSON object
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        raw = content[first_brace:last_brace + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            try:
                return json.loads(_repair_json(raw))
            except json.JSONDecodeError:
                pass

    # Strategy 4: Repair entire content
    try:
        return json.loads(_repair_json(content))
    except json.JSONDecodeError:
        pass

    return content
