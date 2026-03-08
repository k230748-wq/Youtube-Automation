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


def generate_image(
    prompt: str,
    size: str = "1536x1024",
    quality: str = "medium",
    n: int = 1,
) -> bytes:
    """Generate an image using GPT Image 1. Returns raw PNG bytes."""
    import base64

    client = _get_client()
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
        quality=quality,
        n=n,
    )
    return base64.b64decode(response.data[0].b64_json)


def text_to_speech(
    text: str,
    output_path: str,
    voice: str = "onyx",
    model: str = "tts-1",
    speed: float = 1.0,
) -> str:
    """Generate speech audio from text using OpenAI TTS.

    Voices: alloy, echo, fable, onyx, nova, shimmer
    Models: tts-1 (fast), tts-1-hd (higher quality)
    """
    client = _get_client()

    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        speed=speed,
    )

    response.stream_to_file(output_path)
    return output_path
