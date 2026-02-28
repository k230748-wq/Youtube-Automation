"""Voice Agent — generates narration audio via ElevenLabs TTS."""

from app.agents.base import BaseAgent


class VoiceAgent(BaseAgent):
    agent_name = "voice_agent"
    phase_number = 4

    def run(self, input_data: dict, learning_context: list) -> dict:
        # TODO: Implement voice generation
        # 1. Get script text from phase 2 output
        # 2. Split into sections for TTS
        # 3. Call ElevenLabs for each section
        # 4. Generate subtitles via Whisper
        # 5. Return audio paths + subtitle file
        return {"audio_paths": [], "subtitle_path": None, "status": "stub"}
