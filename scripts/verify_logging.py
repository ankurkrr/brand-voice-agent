import sys
import os
import asyncio
import json
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Repos to avoid DB calls
sys.modules['data.repos.pipeline_state'] = MagicMock()
sys.modules['data.repos.voice_profiles'] = MagicMock()
sys.modules['data.repos.content_briefs'] = MagicMock()
sys.modules['data.repos.brands'] = MagicMock()

# Mocking LangChain to avoid API key errors if environment is not set
sys.modules['langchain_google_genai'] = MagicMock()

from core.orchestration.pipeline_runner import PipelineRunner
from core.orchestration.pipeline_state import PipelineState
from core.logging_utils import log_event

# Setup Logging Capture
log_capture = []

def mock_log_event(*args, **kwargs):
    # Capture log arguments
    entry = {
        "trace_id": kwargs.get("trace_id", args[0] if args else None),
        "stage": kwargs.get("stage", args[3] if len(args) > 3 else "UNKNOWN"),
        "message": kwargs.get("message", args[4] if len(args) > 4 else ""),
        "payload": kwargs
    }
    log_capture.append(entry)
    print(f"CAPTURED LOG: {json.dumps(entry, default=str)}")

@patch('core.logging_utils.log_event', side_effect=mock_log_event)
@patch('core.orchestration.pipeline_runner.PipelineStateRepo')
async def run_verification(mock_repo, mock_log):
    print("--- STARTING VERIFICATION ---")
    
    # 1. Verify Pipeline Creation (V1)
    brand_id = "test_brand_123"
    
    # Mock create_pipeline return
    mock_state = PipelineState(brand_id=brand_id, mode="v1")
    mock_repo.create_pipeline.return_value = mock_state
    
    print(f"\n[Test] Creating V1 Pipeline...")
    state_v1 = await PipelineRunner.create_pipeline(brand_id, mode="v1")
    
    # Check if PIPELINE_SELECTED was logged
    selection_logs = [l for l in log_capture if l["stage"] == "PIPELINE_SELECTED"]
    if selection_logs:
        print(f"✅ PASSED: Found PIPELINE_SELECTED log with trace_id={selection_logs[0]['trace_id']}")
    else:
        print(f"❌ FAILED: PIPELINE_SELECTED log not found")

    # 2. Verify Agent 1 Trigger
    mock_repo.get_pipeline.return_value = state_v1
    
    # Mocking route_agent1 to return success
    with patch('core.orchestration.pipeline_runner.route_agent1') as mock_route:
        mock_route.return_value = {"profile_id": "pid_123"}
        
        print(f"\n[Test] Running Voice Profiling Step...")
        await PipelineRunner.run_step(state_v1.pipeline_id, "voice_profiling", {"parent_profile": {}})
        
        # Check STEP_STARTED
        step_logs = [l for l in log_capture if l["stage"] == "STEP_STARTED"]
        if step_logs:
             print(f"✅ PASSED: Found STEP_STARTED log")
        else:
             print(f"❌ FAILED: STEP_STARTED log not found")

    print("\n--- VERIFICATION EXECUTION COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(run_verification())
