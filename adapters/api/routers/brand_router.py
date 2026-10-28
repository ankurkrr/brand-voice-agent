"""
Brand Router
API endpoint for brand management
"""
from fastapi import APIRouter, Form
from data.repos.brands import BrandsRepo

router = APIRouter(prefix="/brands", tags=["brands"])

@router.post("/create")
async def create_brand(name: str = Form(...), brand_id: str = Form(None)):
    """
    Create a new brand and return a brand_id.
    
    If brand_id is provided (e.g. platform's org_id), it will be used as-is.
    Otherwise, a new UUID is auto-generated.
    """
    if brand_id:
        created = await BrandsRepo.create_brand_with_id(brand_id, name)
    else:
        created = await BrandsRepo.create_brand(name)
    return created

@router.delete("/{brand_id}/resources")
async def delete_brand_resources(brand_id: str):
    """
    Delete all generated resources for a brand (Profiles, Briefs, Content).
    Does NOT delete the brand record itself (preserving the name/ID for restart).
    """
    print(f"🔥 [API] Discarding resources for brand: {brand_id}")
    try:
        # Import Repos (Lazy load to avoid circular deps if any)
        from data.repos.voice_profiles import VoiceProfilesRepo
        from data.repos.content_briefs import ContentBriefsRepo
        from data.repos.generated_content import GeneratedContentRepo
        from data.repos.generated_content_machine import GeneratedContentMachineRepo
        from data.repos.voice_personas import VoicePersonasRepo

        # Execute Deletions (Order: Content -> Briefs -> Personas -> Profiles)
        # 1. Content (V3/V2/V1)
        await GeneratedContentMachineRepo.delete_brand_content(brand_id)
        await GeneratedContentRepo.delete_brand_content(brand_id)
        
        # 2. Briefs
        await ContentBriefsRepo.delete_brand_briefs(brand_id)
        
        # 3. Personas (Overlay on Profiles)
        await VoicePersonasRepo.delete_brand_personas(brand_id)
        
        # 4. Profiles (Root)
        await VoiceProfilesRepo.delete_brand_profiles(brand_id)
        
        return {"status": "success", "message": "All brand resources discarded."}
        
    except Exception as e:
        print(f"❌ [API] Discard Failed: {e}")
        # Return success anyway to allow UI to proceed? No, error is better.
        # But for "Reset", partial success is better than getting stuck.
        # Log and return 500.
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
