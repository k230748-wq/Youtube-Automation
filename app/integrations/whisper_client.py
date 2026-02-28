"""OpenAI Whisper integration — audio transcription for subtitles."""

from openai import OpenAI
from config.settings import settings


def transcribe(audio_path: str, output_format: str = "srt") -> str:
    """Transcribe audio to text or subtitle format."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format=output_format,
        )

    return transcript
