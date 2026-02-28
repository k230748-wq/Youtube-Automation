"""Perplexity API integration — AI-powered research."""

import httpx
from config.settings import settings


def call_perplexity(
    prompt: str,
    system_prompt: str = None,
    model: str = "sonar",
    max_tokens: int = 4096,
) -> str:
    """Call Perplexity API for AI-powered search and research."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
