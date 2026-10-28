import pytest
from unittest.mock import AsyncMock
from core.agents.v1.agent2_ideation import run_agent2_ideation

@pytest.mark.asyncio
async def test_agent2_rejects_tone_leakage():
    """Architectural Invariant: Agent 2 must NOT receive voice/tone data."""
    with pytest.raises(ValueError, match="BOUNDARY VIOLATION"):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech",
            tone="Professional"  # ILLEGAL KWARG!
        )

    with pytest.raises(ValueError, match="BOUNDARY VIOLATION"):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech",
            dos=["Be friendly"]  # ILLEGAL KWARG!
        )
        
    with pytest.raises(ValueError, match="BOUNDARY VIOLATION"):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech",
            voice_profile={"some": "data"}  # ILLEGAL KWARG!
        )

@pytest.mark.asyncio
async def test_agent2_rejects_missing_brand(mocker):
    """Agent 2 requires a valid brand ID unless skip flag is True"""
    # Mock repos locally to the module being tested to avoid import shadowing
    mock_vp_repo = mocker.patch("core.agents.v1.agent2_ideation.VoiceProfilesRepo")
    mock_br_repo = mocker.patch("core.agents.v1.agent2_ideation.BrandsRepo")
    
    # Mock repo to return None (brand profile not found)
    mock_br_repo.get_brand_by_id = AsyncMock(return_value=None)
    mock_vp_repo.get_profile_by_brand_id = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="Brand not found for brand_id 123. Cannot run Agent 2."):
        await run_agent2_ideation(
            brand_id="123",
            topic="Blockchain Tech"
        )
