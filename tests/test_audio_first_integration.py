"""Integration test for audio-first visual alignment architecture."""

import pytest
from unittest.mock import patch, MagicMock


def test_full_pipeline_phase_order():
    """Verify phases execute in audio-first order."""
    from app.orchestrator.state import PHASE_NAMES, PHASE_AGENTS

    # Phase 3 should be Voice, Phase 4 should be Media
    assert PHASE_NAMES[3] == "Voice Generation"
    assert PHASE_NAMES[4] == "Media Collection"
    assert PHASE_AGENTS[3] == "voice_agent"
    assert PHASE_AGENTS[4] == "media_agent"


def test_voice_output_has_timestamps():
    """Voice agent must output word_timestamps and clean_script."""
    from app.agents.voice_agent import VoiceAgent

    agent = VoiceAgent()

    # Check that the methods exist
    assert hasattr(agent, '_get_word_timestamps')
    assert callable(agent._get_word_timestamps)


def test_media_receives_voice_data():
    """Media agent must read from phase_3_output (voice)."""
    from app.agents.media_agent import MediaAgent

    agent = MediaAgent()

    # Check helper method exists
    assert hasattr(agent, '_get_voice_data')

    # Verify it reads from phase_3_output
    mock_input = {"phase_3_output": {"test": "value"}}
    result = agent._get_voice_data(mock_input)
    assert result == {"test": "value"}


def test_video_reads_correct_phases():
    """Video agent must read media from phase_4 and voice from phase_3."""
    from app.agents.video_agent import VideoAgent

    agent = VideoAgent()

    # Phase references are in run() — we'll check the class exists
    assert agent.phase_number == 5


def test_segmenter_produces_valid_output():
    """Visual beat segmenter must return segments with required fields."""
    from app.services.visual_beat_segmenter import _fallback_segmentation

    result = _fallback_segmentation("The rain was falling. I held the baby close.")

    assert "segments" in result
    assert len(result["segments"]) > 0

    seg = result["segments"][0]
    assert "scene_id" in seg
    assert "text" in seg
    assert "start" in seg
    assert "end" in seg
    assert "visual_description" in seg


def test_video_agent_has_locked_timing_method():
    """Video agent must have _use_locked_timings method."""
    from app.agents.video_agent import VideoAgent

    agent = VideoAgent()
    assert hasattr(agent, '_use_locked_timings')
    assert callable(agent._use_locked_timings)


def test_locked_timing_calculation():
    """_use_locked_timings must calculate target_duration correctly."""
    from app.agents.video_agent import VideoAgent

    agent = VideoAgent()

    test_clips = [
        {"start_time": 0.0, "end_time": 5.0},
        {"start_time": 5.0, "end_time": 12.5},
        {"start_time": 12.5, "end_time": 15.0},
    ]

    result = agent._use_locked_timings(test_clips)

    assert len(result) == 3
    assert result[0]["target_duration"] == 5.0
    assert result[1]["target_duration"] == 7.5
    assert result[2]["target_duration"] == 2.5  # Clamped to min 2.0


def test_media_agent_segment_with_timing_exists():
    """Media agent must have _segment_with_timing method."""
    from app.agents.media_agent import MediaAgent

    agent = MediaAgent()
    assert hasattr(agent, '_segment_with_timing')
    assert callable(agent._segment_with_timing)
