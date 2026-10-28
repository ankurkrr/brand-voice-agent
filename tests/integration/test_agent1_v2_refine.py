
import asyncio
import uuid
import sys
import os
import json
from unittest.mock import MagicMock, AsyncMock

# 1. Mock dependencies BEFORE import
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["langchain.prompts"] = MagicMock()
sys.modules["langchain.output_parsers"] = MagicMock()

# Mock ChatGoogleGenerativeAI
mock_llm_instance = MagicMock()
sys.modules["langchain_google_genai"].ChatGoogleGenerativeAI.return_value = mock_llm_instance

# Mock PromptTemplate
mock_prompt = MagicMock()
sys.modules["langchain.prompts"].PromptTemplate.return_value = mock_prompt

# Setup Chain Mock
mock_chain = AsyncMock()
mock_prompt.__or__.return_value = mock_chain

# Prepare Fake LLM Response
fake_llm_response = {
  "refined_explicit_rules": {
    "tone": { "primary": "Professional", "secondary": ["Clear"], "description": "Refined tone." },
    "dos": ["Be clear"],
    "donts": ["No jargon"],
    "best_match_examples": []
  },
  "implicit_rules": {
    "avg_sentence_length": 12,
    "reading_level": "Grade 10",
    "formality_bias": "high",
    "emotional_intensity": "low"
  },
  "dimensional_scores": {
    "authority": 0.8,
    "empathy": 0.2,
    "innovation": 0.5,
    "urgency": 0.1
  }
}
mock_response_obj = MagicMock()
mock_response_obj.content = json.dumps(fake_llm_response)
mock_chain.ainvoke.return_value = mock_response_obj

# Now import the Agent
# We need to hack sys.path to ensure we find the core module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from core.agents.v2.agent1_voice import run_agent1

async def test_refinement():
    print("="*60)
    print("TESTING AGENT 1 V2 REFINEMENT (MOCKED LLM)")
    print("="*60)
    
    # Define V1 Input
    parent_profile = {
        "profile_id": str(uuid.uuid4()),
        "brand_id": str(uuid.uuid4()),
        "explicit_rules": {"tone": "raw"},
        "system_prompt": "You are a brand."
    }
    
    print("\n[TEST 1] Testing Valid Input...")
    try:
        result = await run_agent1(parent_profile=parent_profile)
        print("✅ Success! Result received:")
        print(json.dumps(result, indent=2))
        
        # Assertions
        assert "refined_explicit_rules" in result
        assert result["dimensional_scores"]["authority"] == 0.8
        assert "profile_id" not in result # Anti-drift check
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n[TEST 2] Testing Missing Input...")
    try:
        await run_agent1(parent_profile={})
        print("❌ Failed: Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Success: Caught expected error: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_refinement())
