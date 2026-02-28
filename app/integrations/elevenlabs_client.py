"""ElevenLabs API integration — text-to-speech for video narration."""

import httpx
from config.settings import settings

BASE_URL = "https://api.elevenlabs.io/v1"


def text_to_speech(text: str, voice_id: str, output_path: str, model_id: str = "eleven_monolingual_v1") -> str:
    """Generate speech audio from text and save to file."""
    response = httpx.post(
        f"{BASE_URL}/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        },
        timeout=120,
    )
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def list_voices() -> list:
    """List available ElevenLabs voices."""
    response = httpx.get(
        f"{BASE_URL}/voices",
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category"),
            "labels": v.get("labels", {}),
        }
        for v in data.get("voices", [])
    ]
