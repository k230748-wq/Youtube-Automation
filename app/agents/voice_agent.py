"""Voice Agent — generates narration audio using OpenAI TTS (or ElevenLabs)."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)

# OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
DEFAULT_VOICE = "onyx"

# Edge TTS voice mapping per language (male narrator voices)
EDGE_TTS_VOICES = {
    "en": "en-US-GuyNeural",
    "es": "es-MX-JorgeNeural",
}


class VoiceAgent(BaseAgent):
    agent_name = "voice_agent"
    phase_number = 4

    def run(self, input_data: dict, learning_context: list) -> dict:
        config = input_data.get("pipeline_config", {})
        channel_id = input_data.get("channel_id")
        pipeline_run_id = input_data.get("pipeline_run_id", "")

        # Get script from Phase 2
        phase_2 = input_data.get("phase_2_output", {})
        script = phase_2.get("script", "")
        video_id = phase_2.get("video_id")
        title = phase_2.get("selected_title", "")

        if not script:
            raise ValueError("No script from Phase 2 — cannot generate voice")

        # Get voice from config or channel, default to "onyx"
        voice = config.get("voice", DEFAULT_VOICE)
        if channel_id:
            voice = self._get_channel_voice(channel_id) or voice

        language = input_data.get("language", "en")

        logger.info("voice.start", title=title, voice=voice, language=language, script_length=len(script))

        # Step 1: Clean the script for TTS (remove [SCENE:] markers, etc.)
        clean_script = self._clean_script_for_tts(script)

        # Step 2: Generate audio via Edge TTS (language-aware)
        audio_path = self._generate_audio(clean_script, voice, pipeline_run_id, language=language)

        # Step 3: Get audio duration
        duration = self._get_audio_duration(audio_path)

        result = {
            "video_id": video_id,
            "audio_path": audio_path,
            "voice": voice,
            "duration_seconds": duration,
            "script_char_count": len(clean_script),
            "title": title,
        }

        logger.info("voice.complete", duration=duration, audio_path=audio_path)
        return result

    def _get_channel_voice(self, channel_id: str) -> str:
        """Get the configured voice for a channel."""
        try:
            from app.models.channel import Channel
            channel = Channel.query.get(channel_id)
            return channel.voice_id if channel and channel.voice_id else None
        except Exception:
            return None

    def _clean_script_for_tts(self, script: str) -> str:
        """Remove visual markers and formatting not meant to be spoken."""
        import re

        clean = script

        # Remove [SCENE: ...] markers
        clean = re.sub(r'\[SCENE:.*?\]', '', clean)

        # Remove [SECTION: ...] markers
        clean = re.sub(r'\[SECTION:.*?\]', '', clean)

        # Remove markdown-style formatting
        clean = clean.replace('**', '').replace('__', '')

        # Remove multiple newlines
        clean = re.sub(r'\n{3,}', '\n\n', clean)

        # Remove leading/trailing whitespace
        clean = clean.strip()

        return clean

    def _generate_audio(self, text: str, voice: str, pipeline_run_id: str, language: str = "en") -> str:
        """Generate TTS audio using Edge TTS with language-appropriate voice."""
        from app.utils.file_manager import get_video_dir

        video_dir = get_video_dir(pipeline_run_id)

        audio_path = self._generate_chunked_audio(text, voice, video_dir, language=language)
        return audio_path

    def _generate_chunked_audio(self, text: str, voice: str, video_dir: str, language: str = "en") -> str:
        """Generate audio using Edge TTS with the correct language voice."""
        import asyncio
        import edge_tts

        edge_voice = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES["en"])

        logger.info("voice.generating_edge_tts", total_chars=len(text), voice=edge_voice, language=language)

        # Generate full audio in one go (edge-tts has no char limit)
        chunk_path = os.path.join(video_dir, "narration_chunk_000.mp3")
        chunk_paths = [chunk_path]

        async def _generate():
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(chunk_path)

        asyncio.run(_generate())
        logger.info("voice.chunk_done", chunk=1, total=1)

        # Single chunk — just rename
        if len(chunk_paths) == 1:
            final_path = os.path.join(video_dir, "narration.mp3")
            os.rename(chunk_paths[0], final_path)
            return final_path

        # Concatenate chunks using FFmpeg
        final_path = os.path.join(video_dir, "narration.mp3")
        concat_file = os.path.join(video_dir, "audio_concat.txt")
        with open(concat_file, "w") as f:
            for cp in chunk_paths:
                f.write(f"file '{os.path.abspath(cp)}'\n")

        import subprocess
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            final_path,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # Cleanup chunk files
        for cp in chunk_paths:
            if os.path.exists(cp):
                os.remove(cp)
        if os.path.exists(concat_file):
            os.remove(concat_file)

        return final_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of the generated audio."""
        try:
            from app.integrations.ffmpeg_client import get_duration
            return get_duration(audio_path)
        except Exception as e:
            logger.warning("voice.duration_failed", error=str(e))
            return 0.0
