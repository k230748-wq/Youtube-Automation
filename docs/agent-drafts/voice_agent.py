"""Voice Agent — generates narration audio using ElevenLabs TTS."""

import os
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


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
        sections = phase_2.get("sections", [])
        video_id = phase_2.get("video_id")
        title = phase_2.get("selected_title", "")

        if not script:
            raise ValueError("No script from Phase 2 — cannot generate voice")

        # Get voice_id from channel config or pipeline config
        voice_id = config.get("voice_id")
        if not voice_id and channel_id:
            voice_id = self._get_channel_voice(channel_id)
        if not voice_id:
            voice_id = self._get_default_voice()

        logger.info("voice.start", title=title, voice_id=voice_id, script_length=len(script))

        # Step 1: Clean the script for TTS (remove [SCENE:] markers, etc.)
        clean_script = self._clean_script_for_tts(script)

        # Step 2: Generate audio via ElevenLabs
        audio_path = self._generate_audio(clean_script, voice_id, pipeline_run_id)

        # Step 3: Get audio duration
        duration = self._get_audio_duration(audio_path)

        result = {
            "video_id": video_id,
            "audio_path": audio_path,
            "voice_id": voice_id,
            "duration_seconds": duration,
            "script_char_count": len(clean_script),
            "title": title,
        }

        logger.info("voice.complete", duration=duration, audio_path=audio_path)
        return result

    def _get_channel_voice(self, channel_id: str) -> str:
        """Get the configured ElevenLabs voice_id for a channel."""
        try:
            from app.models.channel import Channel
            channel = Channel.query.get(channel_id)
            return channel.voice_id if channel else None
        except Exception:
            return None

    def _get_default_voice(self) -> str:
        """Get a default ElevenLabs voice if none configured."""
        try:
            from app.integrations.elevenlabs_client import list_voices
            voices = list_voices()
            # Prefer a male narrative voice
            for v in voices:
                labels = v.get("labels", {})
                if labels.get("use_case") == "narration" or labels.get("description") == "narrative":
                    return v["voice_id"]
            # Fallback to first available voice
            return voices[0]["voice_id"] if voices else None
        except Exception as e:
            logger.error("voice.default_voice_failed", error=str(e))
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
        clean = clean.replace('*', '').replace('_', '')

        # Remove multiple newlines
        clean = re.sub(r'\n{3,}', '\n\n', clean)

        # Remove leading/trailing whitespace
        clean = clean.strip()

        return clean

    def _generate_audio(self, text: str, voice_id: str, pipeline_run_id: str) -> str:
        """Generate TTS audio using ElevenLabs."""
        from app.integrations.elevenlabs_client import text_to_speech
        from app.utils.file_manager import get_video_dir

        video_dir = get_video_dir(pipeline_run_id)
        audio_path = os.path.join(video_dir, "narration.mp3")

        # ElevenLabs has a character limit per request (~5000 chars)
        # If script is longer, split into chunks and concatenate
        if len(text) > 4500:
            audio_path = self._generate_chunked_audio(text, voice_id, video_dir)
        else:
            text_to_speech(text, voice_id, audio_path)

        return audio_path

    def _generate_chunked_audio(self, text: str, voice_id: str, video_dir: str) -> str:
        """Split long text into chunks and concatenate audio."""
        from app.integrations.elevenlabs_client import text_to_speech

        # Split at paragraph boundaries
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > 4500:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # Generate audio for each chunk
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(video_dir, f"narration_chunk_{i:03d}.mp3")
            text_to_speech(chunk, voice_id, chunk_path)
            chunk_paths.append(chunk_path)

        # Concatenate chunks using FFmpeg
        if len(chunk_paths) == 1:
            final_path = os.path.join(video_dir, "narration.mp3")
            os.rename(chunk_paths[0], final_path)
            return final_path

        from app.integrations.ffmpeg_client import stitch_clips
        final_path = os.path.join(video_dir, "narration.mp3")

        # Create concat file for audio
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
            os.remove(cp)
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
