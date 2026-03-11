import pytest
from unittest.mock import patch, MagicMock

def test_segment_into_visual_beats():
    from app.services.visual_beat_segmenter import segment_into_visual_beats

    script = "The rain was falling. I held the baby close. The orphanage door appeared."
    word_timestamps = [
        {"word": "The", "start": 0.0, "end": 0.2},
        {"word": "rain", "start": 0.2, "end": 0.5},
        {"word": "was", "start": 0.5, "end": 0.7},
        {"word": "falling.", "start": 0.7, "end": 1.2},
        {"word": "I", "start": 1.3, "end": 1.4},
        {"word": "held", "start": 1.4, "end": 1.7},
        {"word": "the", "start": 1.7, "end": 1.8},
        {"word": "baby", "start": 1.8, "end": 2.1},
        {"word": "close.", "start": 2.1, "end": 2.5},
        {"word": "The", "start": 2.6, "end": 2.8},
        {"word": "orphanage", "start": 2.8, "end": 3.3},
        {"word": "door", "start": 3.3, "end": 3.6},
        {"word": "appeared.", "start": 3.6, "end": 4.2},
    ]

    with patch('app.services.visual_beat_segmenter._call_llm') as mock_llm:
        mock_llm.return_value = {
            "segments": [
                {"scene_id": 1, "text": "The rain was falling.", "start": 0.0, "end": 1.2, "visual_description": "Rain"},
                {"scene_id": 1, "text": "I held the baby close.", "start": 1.3, "end": 2.5, "visual_description": "Rain"},
                {"scene_id": 2, "text": "The orphanage door appeared.", "start": 2.6, "end": 4.2, "visual_description": "Door"},
            ]
        }

        result = segment_into_visual_beats(script, word_timestamps)

        assert "segments" in result
        assert len(result["segments"]) == 3
        assert result["segments"][0]["scene_id"] == 1
        assert result["segments"][2]["scene_id"] == 2
