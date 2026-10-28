import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from domain.models.agent3_request import Agent3Request, BrandVoiceProfile, ContentBrief
from core.agents.v1.agent3_execution import run_agent3

# Mock LLM Response (Deterministic)
MOCK_LLM_RESPONSE = """
{
    "blog": "This is a deterministic blog post.",
    "linkedin": "This is a deterministic linkedin post.",
    "twitter": ["Tweet 1", "Tweet 2"],
    "email": "Subject: Deterministic Email"
}
"""

@pytest.mark.asyncio
async def test_agent3_determinism():
    """
    Verify that Agent 3 produces identical output for identical inputs.
    This relies on temperature=0.0 and no random logic in the agent.
    """
    
    # 1. Setup deterministic inputs
    profile = BrandVoiceProfile(
        profile_id="voice-123",
        tone={"primary": "Professional", "secondary": ["Helpful"]},
        dos=["Be clear"],
        donts=["Don't be vague"],
        forbidden_phrases=["synergy"],
        preferred_vocabulary=["collaboration"],
        examples=["Example text"]
    )
    
    brief = ContentBrief(
        topic="Determinism in AI",
        target_audience="Engineers",
        key_messages=["Determinism is good", "Randomness is bad"],
        keywords=["AI", "Testing"],
        cta="Test your code",
        blog_outline=["Intro", "Why Determinism", "Conclusion"]
    )
    
    request = Agent3Request(
        brand_voice_profile=profile,
        content_brief=brief,
        platforms=["blog", "linkedin"]
    )
    
    # 2. Run Agent 3 twice
    # Note: We are using the REAL Agent 3 logic, but preventing DB saves
    # To truly test full system determinism including LLM, we'd need a live LLM or a recorded cassette.
    # For unit testing the *logic* (prompt construction + flow), we mock the LLM to return constant output.
    # The crucial part is that the PROMPT sent to the LLM must be identical.
    
    # Mocking `ChatGoogleGenerativeAI` inside `agent3` is hard without dependency injection.
    # However, `run_agent3` instantiates it internally.
    # Ideally, we should refactor `run_agent3` to accept an LLM instance for testing.
    # For now, we will monkeypatch `ChatGoogleGenerativeAI`.
    
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Create a mock that behaves like the real LLM but returns fixed content
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content=MOCK_LLM_RESPONSE)
    
    # Monkeypatch the constructor to return our mock
    with pytest.MonkeyPatch.context() as m:
        m.setattr("core.agents.agent3.ChatGoogleGenerativeAI", lambda **kwargs: mock_llm)
        
        # Run 1
        result1 = await run_agent3(request, save_to_db=False)
        
        # Run 2
        result2 = await run_agent3(request, save_to_db=False)
        
        # 3. Assert Prompts were Identical
        # We check the arguments passed to ainvoke
        call_args_list = mock_llm.ainvoke.call_args_list
        assert len(call_args_list) == 2
        prompt1 = call_args_list[0][0][0]
        prompt2 = call_args_list[1][0][0]
        
        assert prompt1 == prompt2, "Non-deterministic prompt construction detected!"
        
        # 4. Assert Outputs are Identical
        import json
        json1 = json.dumps(result1, sort_keys=True)
        json2 = json.dumps(result2, sort_keys=True)
        
        assert json1 == json2, "Non-deterministic output detected!"
        
        print("\n✅ Determinism Test Passed: Inputs produced identical Prompts and Outputs.")

if __name__ == "__main__":
    asyncio.run(test_agent3_determinism())
