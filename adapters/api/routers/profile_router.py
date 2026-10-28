"""
Profile Router - Voice Profile Management

Handles voice profile retrieval and updates.

Endpoints:
- POST /voice/{brand_id}/feedback - Submit user feedback (accept/reject/rewrite)
- POST /voice/{brand_id}/update-rules - Update voice rules

Called By: Frontend UI for voice profile management
"""
from fastapi import APIRouter, HTTPException
from domain.models.feedback_schemas import FeedbackRequest, UpdateRulesRequest
from data.repos.voice_profiles import VoiceProfilesRepo

# Changed prefix from /profiles to /voice as per User Request
router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/{brand_id}/feedback")
async def feedback(brand_id: str, req: FeedbackRequest):
    """
    Accept / Reject Feedback
    Payload: { "accepted": true | false }
    Behavior: Update stats.accepted
    """
    updated = await VoiceProfilesRepo.update_stats(brand_id, req.accepted)
    if not updated:
        raise HTTPException(404, "Brand not found")
        
    return {"status": "success", "accepted": req.accepted}

@router.patch("/{brand_id}/rules")
async def update_rules(brand_id: str, req: UpdateRulesRequest):
    """
    Edit Voice Profile
    Payload: { "tone": "string", "dos": [], "donts": [] }
    Behavior: Creates a NEW version of the voice profile (DRAFT status) with updated rules.
    """
    # 1. Fetch current latest profile to get base data
    current_profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
    if not current_profile:
        raise HTTPException(404, "Brand profile not found")
        
    # 2. Prepare updated data
    import json
    
    # Reconstruct profile_data for manipulation from flattened profile
    # The new get_profile_by_brand_id returns keys at top level (not in profile_data blob)
    profile_data = {
        "system_prompt": current_profile.get("system_prompt"),
        "rules": current_profile.get("rules", {}) or {},
        "tone": current_profile.get("tone", {}) or {},
        # Preserve other fields if needed, but save_profile mainly cares about these
    }
        
    # Update fields
    if "rules" not in profile_data:
        profile_data["rules"] = {}
        
    profile_data["rules"]["dos"] = req.dos
    profile_data["rules"]["donts"] = req.donts
    profile_data["tone"] = req.tone
    
    # Reset stats if present (unlock, unaccept) for new version
    # Since we are creating a fresh dict from explicit rules, stats are implicitly reset unless we copy them.
    # We want a fresh start for a new version, so no stats is correct.
    profile_data["stats"] = {
        "accepted": False,
        "locked": False
    }

    # 3. Save as NEW version (Repo defaults status='DRAFT')
    saved = await VoiceProfilesRepo.save_profile(brand_id, profile_data)
    
    print(f"[PROFILE_ROUTER] Created new draft version {saved['version']} for brand {brand_id}")
    return {"status": "success", "message": "Profile updated", "version": saved["version"]}


@router.get("/{brand_id}/personas")
async def list_personas(brand_id: str):
    """
    List all V2 personas for a brand.
    """
    try:
        from core.voice.persona_manager import PersonaManager
        personas = await PersonaManager.get_personas_by_brand(brand_id)
        return {
            "status": "success",
            "brand_id": brand_id,
            "count": len(personas),
            "personas": personas
        }
    except Exception as e:
        print(f"[PROFILE_ROUTER] Failed to list personas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
