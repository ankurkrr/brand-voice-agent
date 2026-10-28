"""
Voice Rule Extractor - LLM-Powered Brand Voice Analysis

Analyzes brand text (PDFs, guidelines, web content) to extract explicit writing rules.
Uses Gemini LLM with structured prompts to identify tone, dos/donts, vocabulary preferences.

Key Functions:
- extract_rules_from_text(): Main extraction function (async, accepts injected LLM)
- RuleSchema: Pydantic model ensuring consistent LLM output structure

Depends On: prompts/rule_extraction.md, lib.utils.json_repair
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from pathlib import Path
import json


class RuleSchema(BaseModel):
    dos: list[str] = []
    donts: list[str] = []
    forbidden_phrases: list[str] = []
    preferred_vocabulary: list[str] = []
    tone: dict = {"primary": "", "secondary": []}


PROMPT_TEMPLATE = Path("prompts/rule_extraction.md").read_text(encoding="utf-8")


async def extract_rules_from_text(text: str, llm: any, pipeline_id: str = "unknown_pipeline", agent_name: str = "agent1_voice_v1") -> dict:
    prompt = PromptTemplate(
        input_variables=["INPUT_TEXT"],
        template=PROMPT_TEMPLATE.replace("<<<INPUT_TEXT>>>", "{INPUT_TEXT}")
    )

    # LLM is now injected (Dependency Injection)
    chain = prompt | llm

    import time
    import uuid
    from core.execution.token_tracker import TokenTracker
    tracker = TokenTracker()
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    raw = await chain.ainvoke({"INPUT_TEXT": text})

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    await tracker.track_llm_usage(
        request_id=request_id,
        pipeline_id=pipeline_id,
        agent_name=agent_name,
        provider="gemini",
        model=getattr(llm, "model", "gemini-2.5-flash"),
        response=raw,
        latency_ms=latency_ms
    )

    # Use robust JSON parsing utility
    from lib.utils.json_repair import safe_parse_json
    
    try:
        obj = safe_parse_json(raw.content)
        return RuleSchema(**obj).dict()
    except Exception as e:
        # LOGGING for debugging "noisy" data issues
        print(f"\n{'='*80}")
        print(f"[RULE_EXTRACTOR] FAILED TO PARSE JSON FROM LLM")
        print(f"Error: {e}")
        print(f"{'='*80}")
        print(f"RAW LLM RESPONSE (first 2000 chars):")
        print(raw.content[:2000])
        print(f"{'='*80}\n")
        
        # Try to provide a more helpful error message
        error_msg = f"Failed to extract JSON from LLM response: {str(e)}"
        
        # If it's a comma delimiter error, provide specific guidance
        if "Expecting ',' delimiter" in str(e):
            error_msg += "\n\nThe LLM returned malformed JSON with missing commas. "
            error_msg += "This is usually a temporary issue. Please try again."
        
        raise ValueError(error_msg)

