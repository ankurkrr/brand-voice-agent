from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request
from data.repos.voice_profiles import VoiceProfilesRepo
from data.repos.brands import BrandsRepo

from core.orchestration.pipeline_runner import PipelineRunner
from core.orchestration.pipeline_state import PipelineState
from core.pipelines.ingestion import generate_voice_profile

router = APIRouter(prefix="/pipeline", tags=["orchestration"])

class ApprovalPayload(BaseModel):
    feedback: Optional[str] = None

@router.post("/start", response_model=PipelineState)
async def start_pipeline(brand_id: str, mode: Literal["v1", "v2"] = "v1"):
    """
    Step 0: Initialize a new pipeline for a brand.
    Returns the initial PipelineState.
    """
    try:
        # Await async call
        state = await PipelineRunner.create_pipeline(brand_id, mode=mode)
        return state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{pipeline_id}/state", response_model=PipelineState)
async def get_pipeline_state(pipeline_id: str):
    """
    Get the current state of a pipeline.
    """
    # Await async call
    state = await PipelineRunner.get_pipeline(pipeline_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return state

@router.post("/{pipeline_id}/step/{step_name}")
async def run_pipeline_step(pipeline_id: str, step_name: str, payload: dict):
    """
    Trigger a specific step in the pipeline.
    Enforces server-side order and dependencies.
    """
    try:
        # Validate Pipeline Exists
        state = await PipelineRunner.get_pipeline(pipeline_id)
        if not state:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        # Execute Step (Synchronously for now, can be async background task)
        updated_state = await PipelineRunner.run_step(pipeline_id, step_name, payload)
        return updated_state

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{pipeline_id}/approve/{step_name}")
async def approve_step(pipeline_id: str, step_name: str, payload: ApprovalPayload = None):
    """
    Approve an artifact (Voice Profile or Content Brief).
    Transition: DRAFT -> APPROVED
    """
    try:
        feedback = payload.feedback if payload else None
        state = await PipelineRunner.approve_step(pipeline_id, step_name, feedback)
        return state
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{pipeline_id}/reject/{step_name}")
async def reject_step(pipeline_id: str, step_name: str, payload: ApprovalPayload = None):
    """
    Reject an artifact.
    Transition: DRAFT -> REJECTED
    """
    try:
        feedback = payload.feedback if payload else None
        state = await PipelineRunner.reject_step(pipeline_id, step_name, feedback)
        return state
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/regenerate/{incoming_id}")
async def regenerate_profile(incoming_id: str, request: Request):
    """
    Regenerate a voice profile (Flow A).
    
    Rules:
    1. Resolve ID: Input could be profile_id OR brand_id.
    2. Check for Active/Draft profile (Source of truth: get_latest_active_profile).
    3. Generate New Version.
    4. Return new profile.
    """
    try:
        # [CHECKPOINT 1] Regeneration API Entry
        print(f"[REGEN][API][ENTRY] incoming_id={incoming_id} request_url={request.url} request_method={request.method} session_id={request.query_params.get('session_id')}")
        
        brand_id = None
        
        # 1. Resolve Brand ID
        # Try as Profile ID first
        print(f"[REGEN][RESOLVE][PROFILE_ID] Attempting resolution as profile_id with incoming_id={incoming_id}")
        profile = await VoiceProfilesRepo.get_profile(incoming_id)
        
        if profile:
            brand_id = profile["brand_id"]
            print(f"[REGEN][RESOLVE][PROFILE_ID] Result=FOUND resolved_brand_id={brand_id}")
        else:
            print(f"[REGEN][RESOLVE][PROFILE_ID] Result=NOT FOUND, attempting as brand_id")
            # Fallback: Try as Brand ID
            print(f"[REGEN][RESOLVE][BRAND_ID] Treating incoming_id as brand_id, attempting fetch")
            brand = await BrandsRepo.get_brand_by_id(incoming_id)

            if brand:
                brand_id = incoming_id
                print(f"[REGEN][RESOLVE][BRAND_ID] Result=FOUND brand_id={brand_id}")
            else:
                print(f"[REGEN][RESOLVE][BRAND_ID] Result=NOT FOUND")
                print(f"[REGEN][ERROR][CAUSE] incoming_id={incoming_id} could_not_resolve_to=profile_or_brand resolved_brand_id=None")
                raise HTTPException(status_code=404, detail="Profile or Brand not found")

        # Canonical resolution log
        print(f"[REGEN][RESOLVE] incoming_id={incoming_id} -> resolved_brand_id={brand_id}")

        # 2. Check for Existing Profile (Source of Truth for "Can we regenerate?")
        # Post-fix: get_latest_active_profile returns ANY profile (Source of Truth for Existence)
        print(f"[REGEN][EXISTENCE_CHECK][INPUT] brand_id={brand_id}")
        active_profile = await VoiceProfilesRepo.get_active_profile(brand_id)
        
        if not active_profile:
            # Requirement: Fail ONLY if no human profile exists at all
            print(f"[REGEN][ERROR][CAUSE] incoming_id={incoming_id} resolved_brand_id={brand_id} profile_existence_result=NONE")
            raise HTTPException(
                status_code=400,
                detail="Cannot regenerate: No voice profile history exists. Please ingest content first."
            )

        old_active_id = active_profile["profile_id"]
        print(f"[REGEN][ACTIVE_CHECK] Previous Active Profile: profile_id={old_active_id} status={active_profile['status']} version={active_profile['version']}")

        # Source log required by ARD
        print(f"[REGEN][SOURCE] brand_id={brand_id}, profile_id={old_active_id}, version={active_profile['version']}, status={active_profile['status']}")

        # 3. Get Brand Name (for Generation)
        brand = await BrandsRepo.get_brand_by_id(brand_id)
        if not brand:
            print(f"[REGEN][ERROR][CAUSE] incoming_id={incoming_id} resolved_brand_id={brand_id} active_profile_result={old_active_id} brand_data_missing=True")
            raise HTTPException(status_code=500, detail=f"Brand data missing for ID {brand_id}")
        
        brand_name = brand["name"]
        print(f"[REGEN][GEN][START] brand_name={brand_name} brand_id={brand_id} previous_profile_id={old_active_id}")
        
        try:
            # 4. Generate (brand-scoped only)
            result = await generate_voice_profile(
                brand_id=brand_id,
                brand_name=brand_name,
                regenerate=True
            )

            # Canonicalize new profile info
            new_profile_id = None
            new_version = None
            if isinstance(result, dict):
                new_profile_id = result.get('profile_id') or result.get('id')
                new_version = result.get('version')

            print(f"[REGEN][SUCCESS] incoming_id={incoming_id} resolved_brand_id={brand_id} previous_profile_id={old_active_id} new_profile_id={new_profile_id} new_version={new_version}")
            
            # ARD Compliance: Lineage Audit Log
            print(f"[REGEN][LINEAGE] brand_id={brand_id} source_profile_id={old_active_id} source_version={active_profile['version']} source_status={active_profile['status']} new_profile_id={new_profile_id} new_version={new_version}")

            return {
                "brand_id": brand_id,
                "previous_profile_id": old_active_id,
                "new_profile": {
                    "profile_id": new_profile_id,
                    "version": new_version
                }
            }

        except Exception as e:
            print(f"[REGEN][ERROR][CAUSE] incoming_id={incoming_id} resolved_brand_id={brand_id} active_profile_result={old_active_id} generation_exception={str(e)}")
            raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")
    
    except HTTPException:
        # Re-raise HTTPExceptions as-is (already logged)
        raise
    except Exception as e:
        # Catch any unexpected errors and log them to terminal
        import traceback
        error_trace = traceback.format_exc()
        print(f"[REGEN][ERROR][UNEXPECTED] Uncaught exception in regenerate_profile")
        print(f"[REGEN][ERROR][TRACEBACK]\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
