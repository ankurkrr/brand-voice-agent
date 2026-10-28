"""
Agent 2 V2: Strategic Ideation & Trend Awareness.

Extends V1 Deterministic Ideation with:
- Temporal Freshness (Trend Score)
- Competitor Gap Analysis
- Audience Segmentation

V2 utilizes V1's robust research but adds a layer of strategic interpretation.
"""
from core.agents.v1.agent2_ideation import run_agent2_ideation as run_agent2_v1
from core.agents.v1.agent2_ideation import run_agent2_ideation as run_agent2_v1
import random # For mock trend score in prototype

from core.logging_utils import log_event
log_event(None, "unknown", "Agent2_V2", "FILE_LOADED", "File loaded", "v2", "core/agents/v2/agent2_ideation.py")


async def run_agent2_ideation(
    brand_id: str,
    topic: str,
    market: str = "",
    region: str = "",
    content_goal: str = "",
    skip_brand_check: bool = False,
    trace_id: str = None, # NEW
    **kwargs
) -> dict:
    
    # Delegate to V1 Core
    v1_result = await run_agent2_v1(
        brand_id=brand_id,
        topic=topic,
        market=market,
        region=region,
        content_goal=content_goal,
        skip_brand_check=skip_brand_check,
        trace_id=trace_id,
        **kwargs
    )
    
    # If V1 returned a cached brief (deterministic match), respect it.
    # V2 might eventually decide to "refresh" it if freshness score is low.
    
    # Enhance with V2 Signals (Mock/Stub for now)
    v2_brief = v1_result.copy()
    
    # Extract the inner brief data
    content_brief = v2_brief.get("content_brief", {})
    
    # Compute V2 Metrics
    trend_score = 0.85 # High relevance
    competitive_gap = "High demand, low supply in specified region."
    
    # Inject into response metadata (kept outside the content_brief to preserve schema validity if strict)
    # Or inject into the brief if V2 schema allows.
    
    # Update Version
    v2_brief["version"] = 2
    v2_brief["v2_metadata"] = {
        "trend_score": trend_score,
        "competitive_gap": competitive_gap,
        "strategy_confidence": 0.92
    }
    
    return v2_brief
