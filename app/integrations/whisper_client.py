"""OpenAI Whisper integration — audio transcription for subtitles."""

import structlog
from openai import OpenAI
from config.settings import settings

logger = structlog.get_logger(__name__)


def transcribe(audio_path: str, output_format: str = "srt", language: str = None) -> str:
    """Transcribe audio to text or subtitle format.

    Args:
        audio_path: Path to audio file (mp3, wav, etc.)
        output_format: One of 'srt', 'vtt', 'text', 'json', 'verbose_json'
        language: ISO-639-1 language code (e.g. 'en', 'es') for better accuracy

    Returns:
        Transcription content as string (SRT/VTT/text).
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    kwargs = {"model": "whisper-1", "response_format": output_format}
    if language:
        kwargs["language"] = language

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            **kwargs,
        )

    logger.info("whisper.transcribed", format=output_format,
                length=len(transcript) if isinstance(transcript, str) else 0)
    return transcript


def transcribe_with_timestamps(audio_path: str) -> dict:
    """Transcribe audio with word-level timestamps.

    Returns dict with 'text', 'segments', and 'words' (if available).
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"],
        )

    result = {
        "text": transcript.text,
        "duration": transcript.duration,
        "segments": [],
        "words": [],
    }

    if hasattr(transcript, "segments") and transcript.segments:
        result["segments"] = [
            {
                "id": seg.id,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            }
            for seg in transcript.segments
        ]

    if hasattr(transcript, "words") and transcript.words:
        result["words"] = [
            {
                "word": w.word,
                "start": w.start,
                "end": w.end,
            }
            for w in transcript.words
        ]

    logger.info("whisper.timestamps", segments=len(result["segments"]),
                words=len(result["words"]))
    return result


def segments_to_srt(segments: list) -> str:
    """Convert Whisper segments to SRT format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
