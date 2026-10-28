import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.agents.v2.agent1_voice import run_agent1, Agent1V2Response

@pytest.mark.asyncio
@pytest.mark.v2
async def test_agent1_v2_enforces_brand_id():
    """Architectural Invariant: Agent 1 V2 MUST require a brand_id."""
    v1_mock_profile = {
        "system_prompt": "Mock prompt",
        "explicit_rules": {}
        # Notice: No brand_id
    }
    
    with pytest.raises(ValueError, match="requires brand_id to create persona"):
        await run_agent1(parent_profile=v1_mock_profile)


@pytest.mark.asyncio
@pytest.mark.v2
async def test_agent1_v2_persona_persistence(mocker, mock_llm):
    # Setup - mock the PersonaManager to bypass DB checks
    mocker.patch("core.voice.persona_manager.PersonaManager.ensure_default_personas", new_callable=AsyncMock)
    
    # Patch the repository exactly where it is used
    mock_local_personas_repo = mocker.patch("core.agents.v2.agent1_voice.VoicePersonasRepo")
    mock_local_personas_repo.create_persona = AsyncMock()

    v1_mock_profile = {
        "brand_id": "brand-123",
        "system_prompt": "Mock prompt",
        "explicit_rules": {"tone": {"primary": "Witty"}}
    }
    
    # Mock DimensionalScorer
    mock_scorer = mocker.patch("core.voice.dimensional_scorer.DimensionalScorer.score_dimensions", new_callable=AsyncMock, return_value={
        "Humor": 0.8, "Empathy": 0.5, "Authority": 0.6, "Formality": 0.2, "Urgency": 0.3
    })
    
    # Mock the Langchain prompt execution because PydanticOutputParser is hard to mock cleanly
    class MockDataObj:
        def dict(self):
            return {
                "refined_explicit_rules": {"tone": {"primary": "Witty"}, "dos": [], "donts": [], "best_match_examples": []},
                "implicit_rules": {"avg_sentence_length": 15, "reading_level": "Grade 8", "formality_bias": "low", "emotional_intensity": "high"},
                "dimensional_scores": {"authority": 0.6, "empathy": 0.5, "innovation": 0.8, "urgency": 0.3}
            }
            
    # Setup custom chain mock that allows `await chain.ainvoke` to succeed
    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(return_value=MockDataObj())
    
    # Mock PromptTemplate so its `|` operator just returns the ready-to-await chain
    mock_prompt = MagicMock()
    mock_prompt.__or__.return_value.__or__.return_value = mock_chain
    mocker.patch("core.agents.v2.agent1_voice.PromptTemplate", return_value=mock_prompt)
    
    # Execute
    result = await run_agent1(
        parent_profile=v1_mock_profile,
        source_text_for_rules="Some text for scoring"
    )
    
    # Assert correct structure is returned
    assert result["version"] == 2
    assert "persona_id" in result
    assert result["brand_id"] == "brand-123"
    
    # Assert DB saving was called
    mock_local_personas_repo.create_persona.assert_called_once()
    saved_args = mock_local_personas_repo.create_persona.call_args[1]
    assert saved_args["brand_id"] == "brand-123"
    assert "Humor" in saved_args["dimensional_scores"]
