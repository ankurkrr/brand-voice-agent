from fastapi import APIRouter, HTTPException
from core.pipelines.voice_refinement import refine_voice_profile

router = APIRouter(prefix="/profiles", tags=["Voice Refinement"])


@router.post("/{profile_id}/refine")
async def refine_profile(profile_id: str):
    """
    Runs Agent-1 V2 refinement on an existing V1 voice profile.
    """
    try:
        print("🔥 [API] /profiles/{profile_id}/refine CALLED")
        print("🔥 [API] profile_id =", profile_id)

        result = await refine_voice_profile(profile_id)

        # 🔒 CONTRACT CHECKS (NON-NEGOTIABLE)
        if not result:
            raise RuntimeError("Refinement returned empty result")

        if "dimensional_scores" not in result:
            raise RuntimeError("V2 violation: dimensional_scores missing in refinement output")

        if "implicit_rules" not in result:
            raise RuntimeError("V2 violation: implicit_rules missing in refinement output")

        print("✅ [API] Refinement completed successfully")
        print("✅ [API] dimensional_scores keys =", list(result["dimensional_scores"].keys()))

        return {
            "status": "success",
            "profile_id": profile_id,
            "refinement": result
        }

    except Exception as e:
        print("❌ [API] Refinement failed:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

