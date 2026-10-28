import pytest
from core.orchestration.pipeline_runner import PipelineRunner
from core.orchestration.pipeline_state import PipelineStatus
from core.orchestration.version_router import route_agent1
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_pipeline_mode_initialization():
    """Test that pipeline creates state with correct mode."""
    # Test V1 Default
    state_v1 = PipelineRunner.create_pipeline("brand-123", mode="v1")
    assert state_v1.mode == "v1"
    
    # Test V2 Explicit
    state_v2 = PipelineRunner.create_pipeline("brand-123", mode="v2")
    assert state_v2.mode == "v2"

@pytest.mark.asyncio
async def test_router_dispatch_v1():
    """Verify router calls V1 agent when mode is v1."""
    with patch("core.orchestration.version_router.run_agent1_v1", new_callable=AsyncMock) as mock_v1:
        mock_v1.return_value = {"persona_id": "v1-id", "version": 1}
        
        # Call router directly
        result = await route_agent1("v1", {"some": "payload"})
        
        assert mock_v1.called
        assert result["version"] == 1

@pytest.mark.asyncio
async def test_router_dispatch_v2():
    """Verify router calls V2 agent when mode is v2."""
    with patch("core.orchestration.version_router.run_agent1_v2", new_callable=AsyncMock) as mock_v2:
        mock_v2.return_value = {"persona_id": "v2-id", "version": 2}
        
        # Call router directly
        result = await route_agent1("v2", {"some": "payload"})
        
        assert mock_v2.called
        assert result["version"] == 2

@pytest.mark.asyncio
async def test_pipeline_runner_integration_v2():
    """Verify PipelineRunner executes V2 path end-to-end (mocked agents)."""
    state = PipelineRunner.create_pipeline("brand-123", mode="v2")
    
    # Mock V2 Agent 1
    with patch("core.orchestration.version_router.run_agent1_v2", new_callable=AsyncMock) as mock_agent1:
        mock_agent1.return_value = {"persona_id": "v2-persona-id", "version": 2}
        
        # Run Step
        updated_state = await PipelineRunner.run_step(state.pipeline_id, "voice_profiling", {})
        
        # Assertions
        assert mock_agent1.called
        assert updated_state.voice_profile_id == "v2-persona-id"
        assert updated_state.steps["voice_profiling"] == "COMPLETED"
