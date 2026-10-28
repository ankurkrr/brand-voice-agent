"""
Signal Analyzer Layer (Agent 2)

Performs deterministic gap analysis on CompetitiveSignals.
Uses an LLM to semantically abstract headlines into core noun-phrase themes, 
preventing verbatim headline copying and accurately calculating saturation.
"""

from typing import List
from pydantic import BaseModel, Field

class GapAnalysis(BaseModel):
    dominant_themes: List[str] = Field(
        ..., description="The high-frequency, heavily represented themes in the SERP (e.g. 'Market growth projections')"
    )
    saturated_themes: List[str] = Field(
        ..., description="Themes that are repeated so often they offer no differentiation value."
    )
    underexplored_angles: List[str] = Field(
        ..., description="Strategic thematic gaps NOT heavily represented in the SERP (e.g. 'Data governance frameworks')"
    )

async def analyze_signals(llm, signals, pipeline_id: str = "unknown_pipeline") -> GapAnalysis:
    """Takes a CompetitiveSignals object and returns a semantic GapAnalysis via LLM"""
    headings = signals.competitor_angles
    
    if not headings:
        return GapAnalysis(dominant_themes=[], saturated_themes=[], underexplored_angles=[])

    # Convert to a readable string list for the LLM
    headings_str = "\n".join([f"- {h}" for h in headings])
    
    prompt = f"""
    You are a Senior SEO Strategist. 
    Review the following competitor page headings retrieved from the SERP.
    
    {headings_str}
    
    1. Extract the TRUE semantic themes (noun phrases, e.g. 'Market size', 'Use cases', 'Data governance').
       DO NOT just copy the literal headlines. Abstract them.
    2. Identify the 'dominant_themes' (high frequency patterns).
    3. Identify the 'saturated_themes' (repeated clusters that offer zero differentiation).
    4. Propose 3-5 'underexplored_angles' (highly specific, differentiated themes NOT heavily represented).
    
    Return the result strictly as JSON obeying the schema.
    """
    
    try:
        structured_llm = llm.with_structured_output(GapAnalysis, include_raw=True)
        
        import time
        import uuid
        from core.execution.token_tracker import TokenTracker
        tracker = TokenTracker()
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        result_wrapper = await structured_llm.ainvoke([{"role": "user", "content": prompt}])
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        await tracker.track_llm_usage(
            request_id=request_id,
            pipeline_id=pipeline_id,
            agent_name="agent2_ideation",
            provider="gemini",
            model=getattr(llm, "model", "gemini-2.5-flash"),
            response=result_wrapper["raw"],
            latency_ms=latency_ms
        )

        return result_wrapper["parsed"]
    except Exception as e:
        print(f"[SignalAnalyzer] LLM Semantic Extraction failed: {e}")
        return GapAnalysis(dominant_themes=[], saturated_themes=[], underexplored_angles=[])
