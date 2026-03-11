import pytest
from unittest.mock import patch, MagicMock

def test_voice_agent_returns_word_timestamps():
    from app.agents.voice_agent import VoiceAgent

    agent = VoiceAgent()

    mock_input = {
        "pipeline_run_id": "test-123",
        "phase_2_output": {
            "script": "The rain was heavy. I held the baby close.",
            "video_id": "vid-123",
            "selected_title": "Test Story",
        },
        "language": "en",
    }

    with patch.object(agent, '_generate_audio') as mock_gen, \
         patch.object(agent, '_get_audio_duration') as mock_dur, \
         patch.object(agent, '_get_word_timestamps') as mock_ts:

        mock_gen.return_value = "/tmp/test/narration.mp3"
        mock_dur.return_value = 5.5
        mock_ts.return_value = [
            {"word": "The", "start": 0.0, "end": 0.2},
            {"word": "rain", "start": 0.2, "end": 0.5},
            {"word": "was", "start": 0.5, "end": 0.7},
            {"word": "heavy.", "start": 0.7, "end": 1.2},
        ]

        result = agent.run(mock_input, [])

        assert "word_timestamps" in result
        assert len(result["word_timestamps"]) > 0
        assert result["word_timestamps"][0]["word"] == "The"
