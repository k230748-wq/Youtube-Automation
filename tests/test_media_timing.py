# tests/test_media_timing.py
import pytest
from unittest.mock import patch, MagicMock

def test_media_agent_uses_exact_timing():
    from app.agents.media_agent import MediaAgent

    agent = MediaAgent()

    mock_input = {
        "pipeline_run_id": "test-123",
        "niche": "stories",
        "pipeline_config": {"mode": "story", "style": "cinematic"},
        "phase_2_output": {
            "script": "The rain was falling. I held the baby close.",
            "sections": [{"name": "Opening", "text": "The rain was falling. I held the baby close."}],
            "video_id": "vid-123",
            "selected_title": "Test Story",
        },
        "phase_3_output": {  # Now voice output (Phase 3)
            "audio_path": "/tmp/test/narration.mp3",
            "duration_seconds": 5.5,
            "word_timestamps": [
                {"word": "The", "start": 0.0, "end": 0.2},
                {"word": "rain", "start": 0.2, "end": 0.5},
            ],
            "clean_script": "The rain was falling. I held the baby close.",
        },
    }

    with patch.object(agent, '_segment_with_timing') as mock_seg, \
         patch.object(agent, '_generate_story_images') as mock_gen, \
         patch.object(agent, '_generate_thumbnail') as mock_thumb:

        mock_seg.return_value = [
            {"scene_id": 1, "start": 0.0, "end": 2.5, "visual_description": "Rain scene"},
            {"scene_id": 2, "start": 2.5, "end": 5.5, "visual_description": "Baby scene"},
        ]
        mock_gen.return_value = []
        mock_thumb.return_value = {}

        result = agent.run(mock_input, [])

        # Verify segmenter was called with word timestamps
        mock_seg.assert_called_once()
        call_args = mock_seg.call_args
        assert "word_timestamps" in str(call_args) or len(call_args[0]) > 1
