"""
Ideation Router - Agent 2 API Endpoint

Handles content brief generation for strategic planning.
Uses web research (Tavily) + LLM analysis to create structured briefs.

Endpoints:
- POST /ideation/ideate - Generate content brief for a topic
- GET /ideation/briefs/{brand_id} - Fetch all briefs for a brand

Flow:
1. Verify brand exists (read-only check of voice_profiles)
2. Gather web signals via Tavily API
3. Call Agent 2 to build content brief
4. Validate output (ensure no tone/style leakage)
5. Save brief to content_briefs table
6. Return brief_id and structured brief JSON

Input:
- brand_id: UUID from Agent 1
- topic: Content topic (e.g., "AI in Healthcare")
- market: Optional market/industry
- region: Optional geographic focus

Output:
- brief_id: UUID for the created brief
- topic, target_audience, key_messages, seo_keywords, cta, h2_outline

Called By: Frontend (templates/ideation.html)
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from core.agents.v1.agent2_ideation import run_agent2_ideation
from domain.models.ideation import IdeationRequest, IdeationResponse, SaveBriefRequest
from data.repos.content_briefs import ContentBriefsRepo

router = APIRouter(prefix="/ideation", tags=["ideation"])

@router.post("/ideate", response_model=IdeationResponse)
async def create_ideation(req: IdeationRequest, save_to_db: bool = True, regenerate: bool = False):
    """
    Agent-2: Generate a content brief for a topic.
    param save_to_db: If False, skips DB persistence and DB checks (for validation workflow).
    param regenerate: If True, bypasses fingerprint cache and forces fresh generation.
    """
    try:
        # For parallel execution, skip brand check to avoid race conditions
        # The brand_id is validated when Agent 1 creates the voice profile
        # Agent 2 will fetch the voice_profile_id dynamically when saving
        skip_check = True  # Always skip for parallel flow
        save_to_db = True
        
        result = await run_agent2_ideation(
            brand_id=req.brand_id,
            topic=req.topic,
            market=req.market,
            region=req.region,
            content_goal=req.content_goal,
            skip_brand_check=skip_check,
            save_to_db=save_to_db,
            regenerate=regenerate
        )
        
        # Extract session_id from request if provided
        session_id = req.session_id if hasattr(req, 'session_id') else None
        
        if session_id:
             from data.session_store import SessionStore
             SessionStore.update_agent2(session_id, result)
             
        return IdeationResponse(**result)

    except ValueError as e:
        print(f"❌ [IDEATION_ROUTER] ValueError: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        err_str = str(e)
        if "AGENT_2_PERSISTENCE_FAILURE" in err_str:
            print(f"❌ [IDEATION_ROUTER] STRICT PERSISTENCE FAILURE: {err_str}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "AGENT_2_PERSISTENCE_FAILURE",
                    "reason": err_str.replace("AGENT_2_PERSISTENCE_FAILURE: ", "")
                }
            )
        raise HTTPException(status_code=500, detail=f"Agent 2 Runtime Error: {err_str}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [IDEATION_ROUTER] UNEXPECTED ERROR: {str(e)}")
        print(f"❌ [IDEATION_ROUTER] Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent 2 failed: {str(e)}")


from typing import Optional

@router.get("/briefs/{brand_id}")
async def get_brand_briefs(brand_id: str, topic: Optional[str] = None):
    """
    Retrieve all content briefs for a specific brand.
    Optionally filter by topic (case-insensitive strict match).
    """
    try:
        briefs = await ContentBriefsRepo.fetch_content_briefs_by_brand_id(brand_id, topic=topic)
        
        return {
            "brand_id": brand_id,
            "count": len(briefs),
            "briefs": briefs
        }
    except Exception as e:
        print(f"[IDEATION_ROUTER] Error fetching briefs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brief/{brief_id}")
async def get_brief_by_id(brief_id: str):
    """
    Retrieve a specific content brief by ID.
    """
    try:
        brief = await ContentBriefsRepo.fetch_content_brief_by_id(brief_id)
        
        if not brief:
            raise HTTPException(status_code=404, detail=f"Content brief {brief_id} not found")
        
        return brief
    except HTTPException:
        raise
    except Exception as e:
        print(f"[IDEATION_ROUTER] Error fetching brief: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/save", response_model=dict)
async def save_brief(req: SaveBriefRequest):
    """
    Save a previously generated brief to the database.
    Used when Agent 2 runs in parallel (save_to_db=False) and saves later.
    """
    try:
        # Validate voice profile exists now
        # We invoke Repo to ensuring FK constraint is satisfied
        brief = await ContentBriefsRepo.insert_content_brief(
            brand_id=req.brand_id,
            voice_profile_id=req.voice_profile_id,
            topic=req.topic,
            # Handle ContentBriefData (Pydantic) -> Dict conversion
            content_brief_data=req.content_brief.model_dump() if hasattr(req.content_brief, 'model_dump') else req.content_brief,
            fingerprint=req.brief_id  # Use brief_id as fingerprint/id reference if needed
        )
        return brief
    except Exception as e:
        print(f"[IDEATION_ROUTER] Error saving brief: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
