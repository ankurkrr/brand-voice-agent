"""
Version Router
Routes requests to the appropriate agent version (V1/V2).
Enforces isolation between tracks.
"""
from typing import Literal, Dict, Any, Union
from core.agents.v1.agent1_voice import run_agent1 as run_agent1_v1
from core.agents.v1.agent2_ideation import run_agent2_ideation as run_agent2_v1
from core.agents.v1.agent3_execution import run_agent3 as run_agent3_v1

# V2 Imports
from core.agents.v2.agent1_voice import run_agent1 as run_agent1_v2
from core.agents.v2.agent2_ideation import run_agent2_ideation as run_agent2_v2
from core.agents.v2.agent3_execution import run_agent3 as run_agent3_v2

from domain.models.agent3_request import Agent3Request

from core.logging_utils import log_event
log_event(None, "unknown", "VersionRouter", "FILE_LOADED", "File loaded", "unknown", "core/orchestration/version_router.py")


async def route_agent1(mode: Literal["v1", "v2"], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route to Agent 1 (Voice Profiler)"""
    if mode == "v1":
        return await run_agent1_v1(**payload)
    elif mode == "v2":
        return await run_agent1_v2(**payload)
    else:
        raise ValueError(f"Unknown mode: {mode}")

async def route_agent2(mode: Literal["v1", "v2"], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Route to Agent 2 (Ideation)"""
    if mode == "v1":
        return await run_agent2_v1(**payload)
    elif mode == "v2":
        return await run_agent2_v2(**payload)
    else:
        raise ValueError(f"Unknown mode: {mode}")

async def route_agent3(mode: Literal["v1", "v2"], request: Agent3Request) -> Dict[str, Any]:
    """Route to Agent 3 (Execution)"""
    # Request object might not have trace_id field defined in schema, 
    # but we can try to pass it if we update schema or pass separately.
    # For now, let's assume Agent3Request needs update or we handle it inside agent.
    # Actually, let's see if we can pass it.
    if mode == "v1":
        return await run_agent3_v1(request)
    elif mode == "v2":
        return await run_agent3_v2(request)
    else:
        raise ValueError(f"Unknown mode: {mode}")
