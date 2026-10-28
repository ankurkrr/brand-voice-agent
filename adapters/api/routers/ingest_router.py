"""
Ingest Router - Agent 1 API Endpoint

Handles content ingestion for brand voice extraction.
Supports multiple input formats: PDF, DOCX, URL, raw text.

Endpoints:
- POST /ingest - Upload file or provide URL/text for voice profile creation

Flow:
1. Validate input (file upload OR url OR raw text)
2. Load content using appropriate loader (PDF/DOCX/Web)
3. Store chunks in ChromaDB for vector search
4. Call Agent 1 to extract voice rules
5. Compose and save Voice Profile to DB
6. Return profile_id and summary statistics

Input Formats:
- File Upload: PDF, DOCX (multipart/form-data)
- URL: Web page scraping
- Raw Text: Direct text input

Output:
- profile_id: UUID for the created voice profile
- examples_count: Number of text chunks stored
- tone: Extracted tone summary

Called By: Frontend (templates/index.html)
"""
from fastapi import APIRouter, UploadFile, Form, HTTPException, Request
from typing import Optional, Dict, Any
import uuid
import tempfile
import os

from domain.models.ingest_request import IngestRequest
from domain.models.ingest_response import IngestResponse
from core.pipelines.ingestion import ingest_content, generate_voice_profile
from data.repos.brands import BrandsRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from lib.loaders.file import load_pdf, load_docx
from lib.text.chunker import chunk_documents
from core.storage.vector import upsert_chunks_to_chroma
from lib.text.preprocess import join_documents
# from core.worker.tasks import ingest_content_task  # Disabled for Cloud Run


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest_unified(request: Request):
    """
    Unified ingestion endpoint.
    Accepts multipart/form-data (for file uploads) or application/json (for text/URL).
    """
    print(f"🔥 [API] /ingest request received")
    content_type = request.headers.get("content-type", "")
    
    try:
        # Handle Multipart (File Upload - PDF/DOCX)
        if "multipart/form-data" in content_type:
            form = await request.form()
            brand_name = form.get("brand_name")
            brand_id = form.get("brand_id")
            skip_generation = form.get("skip_generation") == 'true'  # NEW: Check for skip flag
            file = form.get("file")
            
            if not file:
                raise HTTPException(status_code=400, detail="file is required for multipart request")
            
            # Read file content
            file_content = await file.read()
            
            # Determine file type from extension
            filename = file.filename or ""
            parts = filename.split(".")
            ext = parts[-1].lower() if parts else ""
            
            if ext == "pdf":
                input_type = "pdf"
            elif ext in ["docx", "doc"]:
                input_type = "docx"
            elif ext in ["mp3", "wav", "m4a", "mp4", "mov", "avi"]:
                 input_type = "file" # generic file type, ingestion pipeline handles detection
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
            
            # Process ingestion
            result = await ingest_content(
                brand_name=brand_name,
                brand_id=brand_id,
                input_type=input_type,
                input_value="",  # Not used for file uploads
                file_content=file_content,
                file_extension=ext,
                skip_generation=skip_generation  # NEW: Pass flag
            )
            
            return IngestResponse(**result)
        
        # Handle JSON (Text/URL)
        elif "application/json" in content_type:
            body = await request.json()
            req = IngestRequest(**body)
            
            if req.input_type not in ["text", "url"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input_type: {req.input_type}. Must be 'text' or 'url'"
                )
            
            # Process ingestion
            result = await ingest_content(
                brand_name=req.brand_name,
                brand_id=getattr(req, 'brand_id', None),
                input_type=req.input_type,
                input_value=req.input_value,
                skip_generation=getattr(req, 'skip_generation', False)  # NEW: Pass flag from JSON
            )

            
            return IngestResponse(**result)
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Content-Type must be application/json or multipart/form-data"
            )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/upload")
async def ingest_upload(
    file: UploadFile,
    brand_id: str = Form(...),
    brand_name: Optional[str] = Form(None),
    skip_generation: bool = Form(False)  # NEW param
):
    # Validate brand_id or Create
    brand = await BrandsRepo.get_brand_by_id(brand_id)
    if not brand:
        # Auto-create if not exists
        final_name = brand_name or f"Brand {brand_id[:8]}"
        print(f"[API] Auto-creating brand {brand_id} ({final_name})")
        brand = await BrandsRepo.create_brand_with_id(brand_id, final_name)
    
    # Save uploaded file to a temp location
    tmp = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_{file.filename}")
    with open(tmp, "wb") as f:
        f.write(await file.read())

    # Load documents

    if file.content_type == "application/pdf":
        docs = load_pdf(tmp)
    elif file.content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]:
        docs = load_docx(tmp)
    elif file.content_type.startswith("audio/") or file.content_type.startswith("video/"):
        # For this endpoint, we might need to delegate to ingestion pipeline 
        # But this endpoint seems legacy/specific. 
        # Let's route it to ingest_content logic if possible or just fail if not unified.
        # The unified endpoint handles it better.
        # BUT to be safe for existing calls:
        from core.pipelines.ingestion import ingest_content
        # We can't easily jump to ingestion pipeline from here without refactoring.
        # Recommending user use /ingest unified endpoint for multi-modal.
        # But let's allow it if we can. 
        # Actually, let's just raise a helpful error or redirect.
        # Given strict instructions: "MultiModal Ingestion... orphaned... no API/UI".
        # I should probably make this work or point to unified.
        # Let's add a simple check to redirect logic or just support it.
        pass # Pipeline handles it via ingest_content which calls MultiModalAnalyzer
        # Wait, this function `ingest_upload` does explicit `load_pdf`/`load_docx`.
        # It does NOT call `ingest_content`. It implements its own logic.
        # I should NOT rewrite this entire legacy function unless I have to.
        # The unified `/ingest` is the modern one.
        # I will leave this as is but add a comment/error if tempted.
        # Actually, let's just support it by calling the analyzer directly? 
        # No, that duplicates logic.
        # BETTER: Just allow the unified endpoint to be the primary one.
        # The prompt said "Accept YouTube URLs, MP4...".
        # Unified endpoint does that.
        # I will just skip this legacy endpoint modification to avoid regressions.
        raise HTTPException(400, "Unsupported file type. For Audio/Video, use POST /ingest endpoint.")

    chunks = chunk_documents(docs)

    # Upsert chunks to ChromaDB

    collection_name = f"brand_{brand_id}"
    upsert_chunks_to_chroma(chunks, collection_name)


    # Extract rules and compose voice profile
    rules_input = join_documents(docs)

    # 🚨 IMPORTANT:
    # Ingest router ONLY ingests + embeds.
    # Voice profile generation happens via PipelineRunner (V1 Strict).

    profile = None



    if skip_generation:
        return {
            "brand_id": brand_id,
            "status": "ingested_only",
            "message": "Content uploaded and embedded. Generation skipped."
        }

    return {
        "brand_id": brand_id,
        "status": "ingested_only", 
        "message": "Content uploaded and embedded. Call /ingest/generate (if it existed) or use full flow."
    }


@router.post("/generate/{brand_id}")
async def generate_profile_endpoint(brand_id: str):
    """
    Trigger Voice Profile Generation for an existing brand.
    Used when ingestion skipped generation (staged flow).
    """
    print(f"🔥 [API] /ingest/generate/{brand_id} Triggered")
    
    # Verify brand exists
    brand = await BrandsRepo.get_brand_by_id(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    try:
        # Call generation pipeline
        # Source docs are fetched from Chroma inside the function if passed as None
        result = await generate_voice_profile(
            brand_id=brand_id,
            brand_name=brand['name']
        )
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ [API] Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/async", response_model=Dict[str, str])
async def ingest_async(req: IngestRequest):
    """
    Async Ingestion Endpoint - DISABLED FOR CLOUD RUN
    
    This endpoint requires Celery worker + Redis infrastructure which is not 
    configured in the Cloud Run test deployment.
    
    Use the synchronous POST /ingest endpoint instead for all ingestion operations.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Async ingestion disabled in Cloud Run deployment. "
            "Redis/Celery infrastructure not available. "
            "Use POST /ingest for synchronous processing instead."
        )
    )




@router.get("/profile/{profile_id}")
async def get_voice_profile(profile_id: str):
    """
    Retrieve a voice profile by ID.
    Returns the complete voice profile including system_prompt and rules.
    """
    try:
        profile = await VoiceProfilesRepo.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail=f"Voice profile {profile_id} not found")
        
        # Parse JSON field if needed
        import json
        if isinstance(profile.get('profile_data'), str):
            profile['profile_data'] = json.loads(profile['profile_data'])
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        print(f"[INGEST_ROUTER] Error fetching profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/brand/{brand_id}")
async def get_brand_voice_profiles(brand_id: str):
    """
    Retrieve voice profile for a specific brand.
    Returns the most recent voice profile for the brand.
    """
    try:
        profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
        
        # DIAGNOSTIC LOGGING
        print(f"\n{'='*60}")
        print(f"[INGEST_ROUTER] GET /profiles/brand/{brand_id}")
        print(f"[INGEST_ROUTER] Profile found: {profile is not None}")
        if profile:
            print(f"[INGEST_ROUTER] Profile ID: {profile.get('id')}")
            print(f"[INGEST_ROUTER] Version: {profile.get('version')}")
            print(f"[INGEST_ROUTER] Status: {profile.get('status')}")
            print(f"[INGEST_ROUTER] Created: {profile.get('created_at')}")
        print(f"{'='*60}\n")
        
        if not profile:
            raise HTTPException(
                status_code=404, 
                detail=f"No voice profile found for brand {brand_id}. Please ingest content first."
            )
        
        # Parse JSON field if needed
        import json
        if isinstance(profile.get('profile_data'), str):
            profile['profile_data'] = json.loads(profile['profile_data'])
        
        return profile
    except HTTPException:
        raise
    except Exception as e:
        print(f"[INGEST_ROUTER] Error fetching brand profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))





@router.post("/approve/{profile_id}")
async def approve_profile(profile_id: str):
    """
    Promote a specific profile version from DRAFT to APPROVED.
    This is the authoritative 'Save' action.
    """
    try:
        # Validate existence
        profile = await VoiceProfilesRepo.get_profile(profile_id)
        if not profile:
             raise HTTPException(404, "Profile not found")
             
        # Update status
        updated = await VoiceProfilesRepo.update_status(profile_id, 'APPROVED')
        
        # Also lock it - Tier 2 Requirement
        await VoiceProfilesRepo.update_stats(profile['brand_id'], True)
        
        print(f"[INGEST_ROUTER] Profile {profile_id} APPROVED.")
        return {"status": "success", "profile_id": profile_id, "state": "APPROVED"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INGEST_ROUTER] Error approving profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profile/{profile_id}/update")
async def update_profile_human(profile_id: str, request: Request):
    """
    Update Phase 1 (Human) data for a profile.
    Allows editing system prompt and explicit rules.
    """
    try:
        body = await request.json()
        
        # Security/Logic Check: Ensure profile exists
        profile = await VoiceProfilesRepo.get_profile(profile_id)
        if not profile:
             raise HTTPException(404, "Profile not found")
             
        # Call Repo to update human table
        success = await VoiceProfilesRepo.update_human_profile(profile_id, body)
        
        if success:
             return {"status": "success", "profile_id": profile_id, "message": "Phase 1 data updated"}
        else:
             raise HTTPException(500, "Failed to update profile")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[INGEST_ROUTER] Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

