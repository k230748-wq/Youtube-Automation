def test_voice_before_media():
    from app.orchestrator.state import PHASE_NAMES, PHASE_AGENTS

    # Voice should be Phase 3, Media should be Phase 4
    assert PHASE_NAMES[3] == "Voice Generation"
    assert PHASE_NAMES[4] == "Media Collection"
    assert PHASE_AGENTS[3] == "voice_agent"
    assert PHASE_AGENTS[4] == "media_agent"
