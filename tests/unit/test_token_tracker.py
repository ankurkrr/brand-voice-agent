import pytest
import os
from unittest.mock import AsyncMock, patch
from core.execution.token_tracker import TokenTracker
from domain.models.token_usage import TokenUsage

@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    # Mock the save method
    repo.save = AsyncMock()
    return repo

@pytest.fixture
def tracker(mock_repo):
    return TokenTracker(repo=mock_repo)

def test_calculate_cost_default(tracker):
    # Test standard known models
    # gpt-4o: 0.005 prompt, 0.015 completion
    cost = tracker.calculate_cost("openai", "gpt-4o", 1000, 1000)
    assert cost == 0.020
    
    # gemini-1.5-flash: 0.000075 prompt, 0.0003 completion
    cost2 = tracker.calculate_cost("google", "gemini-1.5-flash", 2000, 500)
    expected = (2000 / 1000.0 * 0.000075) + (500 / 1000.0 * 0.0003)
    assert abs(cost2 - expected) < 1e-6

def test_calculate_cost_dynamic_env(tracker):
    # Test with environment variables override
    # PRICING_OPENAI_CUSTOM_MODEL=0.1,0.2
    with patch.dict(os.environ, {"PRICING_OPENAI_CUSTOM_MODEL": "0.1,0.2"}):
        cost = tracker.calculate_cost("openai", "custom-model", 1000, 2000)
        expected = (1.0 * 0.1) + (2.0 * 0.2)
        assert abs(cost - expected) < 1e-6

def test_calculate_cost_unknown_model(tracker):
    # Unknown models should default to 0.0, 0.0 unless env is set
    cost = tracker.calculate_cost("unknown", "model", 1000, 1000)
    assert cost == 0.0

@pytest.mark.asyncio
async def test_track_llm_usage(tracker, mock_repo):
    usage_dict = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    
    await tracker.track_llm_usage(
        pipeline_id="pipe_123",
        request_id="req_456",
        agent_name="agent_test",
        provider="google",
        model="gemini-1.5-flash",
        usage=usage_dict,
        latency_ms=1200
    )
    
    mock_repo.save.assert_called_once()
    saved_record = mock_repo.save.call_args[0][0]
    
    assert isinstance(saved_record, TokenUsage)
    assert saved_record.request_id == "req_456"
    assert saved_record.pipeline_id == "pipe_123"
    assert saved_record.agent_name == "agent_test"
    assert saved_record.prompt_tokens == 100
    assert saved_record.completion_tokens == 50
    assert saved_record.cost_usd > 0.0
    assert saved_record.latency_ms == 1200

@pytest.mark.asyncio
async def test_track_tavily_usage(tracker, mock_repo):
    await tracker.track_tavily_usage(
        pipeline_id="pipe_123",
        request_id="req_tav",
        agent_name="agent_search",
        usage={"tokens": 1},
        latency_ms=500
    )
    
    mock_repo.save.assert_called_once()
    saved_record = mock_repo.save.call_args[0][0]
    
    assert saved_record.provider == "tavily"
    assert saved_record.model == "search"
    assert saved_record.prompt_tokens == 1
    assert saved_record.cost_usd == 0.005 # 1 token * 5.0 / 1000 = 0.005

@pytest.mark.asyncio
async def test_track_embedding_usage(tracker, mock_repo):
    with patch.dict(os.environ, {"PRICING_GOOGLE_MODELS_EMBEDDING_001": "0.0001,0.0"}):
        await tracker.track_embedding_usage(
            pipeline_id="pipe_123",
            request_id="req_emb",
            agent_name="agent_embed",
            provider="google",
            model="models/embedding-001",
            tokens=5000,
            latency_ms=300
        )
        
        mock_repo.save.assert_called_once()
        saved_record = mock_repo.save.call_args[0][0]
        
        assert saved_record.prompt_tokens == 5000
        assert saved_record.completion_tokens == 0
        assert saved_record.cost_usd == 0.0005 # 5000/1000 * 0.0001
