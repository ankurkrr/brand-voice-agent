import pytest
import uuid
from unittest.mock import patch, AsyncMock
from core.orchestration.pipeline_runner import PipelineRunner
from core.orchestration.pipeline_state import PipelineState, PipelineStepStatus
from data.repos.pipeline_state import PipelineStateRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from data.repos.content_briefs import ContentBriefsRepo

@pytest.mark.asyncio
async def test_runner_logic_mocks():
    """
    Unit test for PipelineRunner logic using mocks for everything including Repos.
    """
    brand_id = "b_1"
    pipeline_id = "p_1"
    vp_id = "vp_1"
    cb_id = "cb_1"
    
    # Mock Repos
    with patch("core.orchestration.pipeline_runner.PipelineStateRepo") as MockPipelineRepo, \
         patch("core.orchestration.pipeline_runner.VoiceProfilesRepo") as MockVoiceRepo, \
         patch("core.orchestration.pipeline_runner.ContentBriefsRepo") as MockBriefRepo, \
         patch("core.orchestration.pipeline_runner.route_agent1", new_callable=AsyncMock) as mock_route1, \
         patch("core.orchestration.pipeline_runner.route_agent2", new_callable=AsyncMock) as mock_route2, \
         patch("core.orchestration.pipeline_runner.route_agent3", new_callable=AsyncMock) as mock_route3:
        
        # Setup initial state
        initial_state = PipelineState(
            pipeline_id=pipeline_id, 
            brand_id=brand_id,
            steps={"voice_profiling": "PENDING", "ideation": "PENDING", "execution": "PENDING"}
        )
        MockPipelineRepo.get_pipeline = AsyncMock(return_value=initial_state)
        MockPipelineRepo.update_agent_status = AsyncMock()
        
        # 1. Run Voice
        mock_route1.return_value = {"persona_id": vp_id}
        await PipelineRunner.run_step(pipeline_id, "voice_profiling", {})
        
        # Verify update called with DRAFT
        MockPipelineRepo.update_agent_status.assert_called_with(pipeline_id, "agent1", "DRAFT", artifact_id=vp_id)
        
        # 2. Try Ideation (Fail)
        # Setup state to have voice_profile_id but NOT approved
        state_after_voice = initial_state.model_copy(update={
            "voice_profile_id": vp_id, 
            "steps": {"voice_profiling": "DRAFT", "ideation": "PENDING", "execution": "PENDING"}
        })
        MockPipelineRepo.get_pipeline.return_value = state_after_voice
        MockVoiceRepo.is_approved = AsyncMock(return_value=False)
        
        try:
            await PipelineRunner.run_step(pipeline_id, "ideation", {})
            assert False, "Should fail"
        except ValueError as e:
            assert "Voice Profile must be APPROVED" in str(e)
            
        # 3. Approve Voice
        # Simulate approval action
        MockVoiceRepo.update_status = AsyncMock()
        await PipelineRunner.approve_step(pipeline_id, "voice_profiling")
        MockVoiceRepo.update_status.assert_called_with(vp_id, "APPROVED")
        MockPipelineRepo.update_agent_status.assert_called_with(pipeline_id, "agent1", "APPROVED")
        
        # 4. Run Ideation (Success)
        MockVoiceRepo.is_approved.return_value = True
        state_voice_approved = state_after_voice # Logic checks Step or Repo. Runner checks Repo.
        MockPipelineRepo.get_pipeline.return_value = state_voice_approved 
        
        mock_route2.return_value = {"brief_id": cb_id}
        await PipelineRunner.run_step(pipeline_id, "ideation", {})
        
        MockPipelineRepo.update_agent_status.assert_called_with(pipeline_id, "agent2", "DRAFT", artifact_id=cb_id)
        
        # 5. Try Execution (Fail)
        state_after_ideation = state_voice_approved.model_copy(update={
            "brief_id": cb_id,
            "steps": {"voice_profiling": "APPROVED", "ideation": "DRAFT", "execution": "PENDING"}
        })
        MockPipelineRepo.get_pipeline.return_value = state_after_ideation
        MockBriefRepo.is_approved = AsyncMock(return_value=False)
        
        try:
            await PipelineRunner.run_step(pipeline_id, "execution", {})
            assert False, "Should fail"
        except ValueError as e:
            assert "Content Brief must be APPROVED" in str(e)
            
        # 6. Approve Brief
        MockBriefRepo.update_status = AsyncMock()
        await PipelineRunner.approve_step(pipeline_id, "ideation")
        MockBriefRepo.update_status.assert_called_with(cb_id, "APPROVED")
        
        # 7. Run Execution
        MockBriefRepo.is_approved.return_value = True
        mock_route3.return_value = {"execution_id": "exec_1"}
        await PipelineRunner.run_step(pipeline_id, "execution", {})
        
        MockPipelineRepo.update_agent_status.assert_called_with(pipeline_id, "agent3", "COMPLETED", artifact_id="exec_1")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_runner_logic_mocks())
