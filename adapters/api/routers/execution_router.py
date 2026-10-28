"""
Execution Router - Agent 3 API Endpoint

Handles multi-platform content generation using brand voice + content brief.
Supports auto-fetch mode (fetch profile + brief from DB) or manual mode (provide directly).

Endpoints:
- POST /execute - Generate content for selected platforms
- GET /execute/health - Health check

Flow:
1. Auto-fetch mode: Hydrate BrandVoiceProfile + ContentBrief from DB using brand_id
2. Manual mode: Accept direct JSON input
3. Inject brand voice examples into execution context
4. Call Agent 3 to generate platform content
5. Save output to generated_content table
6. Return platform-specific content JSON

Auto-Fetch (Quick Mode):
- Requires only: brand_id + platforms
- Fetches latest voice profile and content brief from DB

Manual Mode:
- Requires: brand_voice_profile + content_brief + platforms (full JSON)

Platforms:
- blog: 800-2000 words, H2 structure
- linkedin: 1300 chars ideal, hook->value->CTA
- twitter: Thread of 5-10 tweets, 280 chars each
- email: Subject (60 chars) + preview (50-100 chars) + body (200 words)

Called By: Frontend (templates/execution.html)
Calls: core/agents/v1/agent3_execution.py
"""
from fastapi import APIRouter, HTTPException
from domain.models.agent3_request import Agent3Request
from domain.models.agent3_response import Agent3Response, Agent3ErrorResponse
from core.agents.v1.agent3_execution import run_agent3 as run_agent3_v1
from core.agents.v2.agent3_execution import run_agent3 as run_agent3_v2
from data.repos.voice_profiles import VoiceProfilesRepo
from pydantic import BaseModel
from typing import Dict, Any, Optional, Union

class SaveContentRequest(BaseModel):
    brand_id: str
    voice_profile_id: str
    content_brief_id: Optional[str] = None
    output_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


router = APIRouter(prefix="/execute", tags=["agent3", "execution"])


@router.post("", response_model=Union[Agent3Response, Agent3ErrorResponse, Dict[str, Union[Agent3Response, Agent3ErrorResponse]]])
async def execute_content_generation(
    request: Agent3Request, 
    save_to_db: bool = True,
    session_id: str = None,
    regenerate: bool = False
):
    """
    Agent 3 - The Executor
    
    Generate platform-native marketing copy from brand voice profile and content brief.
    Supports:
    1. **Ephemeral (Session)**: Use session_id to get in-memory artifacts.
    2. **Auto-Fetch**: Provide `brand_id` to use DB artifacts.
    3. **Manual**: Provide full JSON.
    
    Args:
        regenerate (bool): If True, forces varied output (higher temperature).
    """
    try:
        # Set regeneration flag on request
        if regenerate:
            request.regenerate = True
            print(f"[EXECUTION_ROUTER] Regeneration requested. Temperature will be increased.")
        # ---------------------------------------------------------
        # HYDRATION LOGIC
        # ---------------------------------------------------------
        
        # CASE 1: Session Store (Ephemeral - Enterprise Compliant)
        if session_id:
            print(f"[EXECUTION_ROUTER] Hydrating from Session: {session_id}")
            from core.storage.session_store import SessionStore
            session = SessionStore.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
                
            agent1_out = session.get("agent1_output", {})
            agent2_out = session.get("agent2_output", {})
            
            if not agent1_out or not agent2_out:
                raise ValueError("Incomplete session data (Agent 1 or 2 missing)")
                
            # Hydrate Voice Profile (Agent 1)
            # Need to map Agent 1 output keys to BrandVoiceProfile
            # Agent 1 Output keys: raw_json (golden_record), profile_data, etc.
            p_data = agent1_out.get("profile_data", {})
            
            # Helper to extract tone
            tone_data = p_data.get("tone", {})

            from domain.models.agent3_request import BrandVoiceProfile
            request.brand_voice_profile = BrandVoiceProfile(
                profile_id=p_data.get("persona_id") or "temp-persona", # V2 Contract ID
                tone=tone_data,
                dos=p_data.get("rules", {}).get("dos", []),
                donts=p_data.get("rules", {}).get("donts", []),
                forbidden_phrases=p_data.get("rules", {}).get("forbidden_phrases", []),
                preferred_vocabulary=p_data.get("rules", {}).get("preferred_vocabulary", []),
                examples=p_data.get("example_snippets", [])
            )
            
            # Hydrate Content Brief (Agent 2)
            b_data = agent2_out.get("content_brief", {})
            if not isinstance(b_data, dict):
                b_data = {}
            ui_data = b_data.get("ui_presentation", {}) if isinstance(b_data, dict) else {}
            raw_data = b_data.get("raw_strategy", {}) if isinstance(b_data, dict) else {}
            existing_topic = request.content_brief.topic if request.content_brief else None
            
            from domain.models.agent3_request import ContentBrief
            request.content_brief = ContentBrief(
                topic=agent2_out.get("topic") or existing_topic or "Marketing Content",
                target_audience=(
                    ui_data.get("target_audience")
                    or b_data.get("target_audience")
                    or raw_data.get("target_audience")
                    or "General"
                ),
                key_messages=(
                    ui_data.get("key_takeaways")
                    or b_data.get("key_takeaways")
                    or raw_data.get("key_takeaways")
                    or []
                ),
                keywords=(
                    ui_data.get("seo_keywords")
                    or b_data.get("seo_keywords")
                    or raw_data.get("seo_keywords")
                    or []
                ),
                cta="Learn more",
                blog_outline=(
                    ui_data.get("h2_outline")
                    or b_data.get("h2_outline")
                    or raw_data.get("h2_outline")
                    or []
                ),
            )
            
            # Disable DB Save for Ephemeral Flow
            save_to_db = False


        # CASE 2: DB Auto-Fetch (Legacy/Direct)
        elif request.brand_id:
            print(f"[EXECUTION_ROUTER] Hydrating request for Brand ID: {request.brand_id}")
            
            # 1. Fetch Brand Voice Profile (Agent 1)
            voice_repo = __import__('data.repos.voice_profiles', fromlist=['VoiceProfilesRepo']).VoiceProfilesRepo
            voice_data = await voice_repo.get_profile_by_brand_id(request.brand_id)
            
            if not voice_data:
                raise ValueError(f"No Brand Voice Profile found for Brand ID: {request.brand_id}")
            
            # Parse Profile Logic
            import json
            # Parse Profile Logic
            # voice_data is the composite_data from Repo. It might NOT have 'profile_data' if flattened.
            profile_json = voice_data.get('profile_data') or voice_data
            
            import json
            if isinstance(profile_json, str):
                profile_json = json.loads(profile_json)
                
            # Convert to internal model
            from domain.models.agent3_request import BrandVoiceProfile
            
            # Helper to ensure tone description exists (legacy profiles may miss it)
            tone_data = profile_json.get('tone', {})
            if 'description' not in tone_data:
                primary = tone_data.get('primary', 'Professional')
                secondary = tone_data.get('secondary', [])
                if isinstance(secondary, list):
                    secondary_str = ", ".join(secondary)
                else:
                    secondary_str = str(secondary)
                tone_data['description'] = f"{primary} tone" + (f" with {secondary_str} nuances" if secondary_str else "")

            # Get profile_id from database column, or fallback to persona_id from JSON
            profile_id = voice_data.get('profile_id') or profile_json.get('persona_id') or voice_data.get('id')
            # V2 CONTRACT: persona_id must be explicitly set
            # ---------------------------------------------------------
            if request.execution_version == "v2" and not request.persona_id and not request.persona_ids:
                from data.repos.voice_personas import VoicePersonasRepo

                persona = await VoicePersonasRepo.get_latest_persona_by_brand(
                    brand_id=request.brand_id
                )

                if not persona:
                    raise ValueError(
                        f"No ACTIVE persona found for brand {request.brand_id}. "
                        f"Run Agent-1 V2 first."
                    )
                
                # Default to single execution
                request.persona_id = persona["persona_id"]

                print(
                    f"[EXECUTION_ROUTER] V2 persona auto-resolved: "
                    f"brand_id={request.brand_id}, persona_id={request.persona_id}"
                )


            
            # FAILSAFE: Ensure profile_id is never None
            if not profile_id:
                print(f"[EXECUTION_ROUTER] WARNING: profile_id resolution failed. Using fallback.")
                profile_id = f"gen-{request.brand_id}-fallback"

            print(f"[EXECUTION_ROUTER] Hydrated profile_id: {profile_id}")
            request.brand_voice_profile = BrandVoiceProfile(
                profile_id=profile_id,
                tone=tone_data,
                dos=profile_json.get('rules', {}).get('dos', []),
                donts=profile_json.get('rules', {}).get('donts', []),
                forbidden_phrases=profile_json.get('rules', {}).get('forbidden_phrases', []),
                preferred_vocabulary=profile_json.get('rules', {}).get('preferred_vocabulary', []),
                examples=profile_json.get('examples', [])  # Hydrate examples
            )
            print(f"[EXECUTION_ROUTER] BrandVoiceProfile Object Created. ID: {request.brand_voice_profile.profile_id}")

            # 2. Fetch Content Brief (Agent 2)
            briefs_repo = __import__('data.repos.content_briefs', fromlist=['ContentBriefsRepo']).ContentBriefsRepo
            
            if request.brief_id:
                # Specific brief
                brief_record = await briefs_repo.fetch_content_brief_by_id(request.brief_id)
                if not brief_record:
                    raise ValueError(f"Content Brief {request.brief_id} not found")
            else:
                # Latest brief
                briefs = await briefs_repo.fetch_content_briefs_by_brand_id(request.brand_id)
                if not briefs:
                    raise ValueError(f"No Content Briefs found for Brand ID: {request.brand_id}")
                brief_record = briefs[0] # Get latest
                request.brief_id = brief_record['brief_id'] # Ensure ID is passed to Agent 3
            
            # Parse Brief Logic (canonical source: content_brief_data).
            brief_data = brief_record.get('content_brief_data', {})
            if isinstance(brief_data, str):
                brief_data = json.loads(brief_data)
            if not isinstance(brief_data, dict):
                brief_data = {}
            ui_data = brief_data.get("ui_presentation", {}) if isinstance(brief_data, dict) else {}
            raw_data = brief_data.get("raw_strategy", {}) if isinstance(brief_data, dict) else {}
                
            # Convert to internal model
            from domain.models.agent3_request import ContentBrief
            
            topic = brief_record.get('topic', 'Topic not specified')
            
            request.content_brief = ContentBrief(
                topic=topic,
                target_audience=(
                    ui_data.get("target_audience")
                    or brief_data.get("target_audience")
                    or raw_data.get("target_audience")
                    or "General Audience"
                ),
                key_messages=(
                    ui_data.get("key_takeaways")
                    or brief_data.get("key_takeaways")
                    or raw_data.get("key_takeaways")
                    or []
                ),
                keywords=(
                    ui_data.get("seo_keywords")
                    or brief_data.get("seo_keywords")
                    or raw_data.get("seo_keywords")
                    or []
                ),
                cta=f"Learn more about {topic}",
                blog_outline=(
                    ui_data.get("h2_outline")
                    or brief_data.get("h2_outline")
                    or raw_data.get("h2_outline")
                    or []
                ),
            )
            print(f"[EXECUTION_ROUTER] Content Brief hydrated (Topic: {request.content_brief.topic})")

        # ---------------------------------------------------------
        # EXECUTION (VERSION-AWARE)
        # ---------------------------------------------------------

        print(f"[EXECUTION_ROUTER] Agent3 execution_version={request.execution_version}")

        if request.execution_version == "v2":
            # Handle Multi-Persona
            # Handle Multi-Persona
            if request.persona_ids:
                results = {}
                for pid in request.persona_ids:
                    # Clone request
                    sub_req = request.model_copy(update={"persona_id": pid, "persona_ids": None})
                    sub_output = await run_agent3_v2(
                        sub_req,
                        save_to_db=True # Force persistence
                    )
                    results[pid] = sub_output
                result = results
            else:
                result = await run_agent3_v2(request, save_to_db=True) # Force persistence
        else:
            result = await run_agent3_v1(request, save_to_db=save_to_db)
        
        # Check if result is an error
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail=result
            )

        # ---------------------------------------------------------
        # PERSISTENCE (Step 4 & 5)
        # ---------------------------------------------------------
        
        if session_id:
            # Store in Ephemeral Session
            from core.storage.session_store import SessionStore
            SessionStore.update_agent3(session_id, result)
            
        elif save_to_db:

            try:
                # -------------------------
                # V2 PERSISTENCE
                # -------------------------
                if request.execution_version == "v2":
                    # Agent 3 V2 handles its own persistence internally (per persona).
                    # We skip router-level persistence to avoid double-writes 
                    # and errors with multi-persona result maps.
                    pass

                # -------------------------
                # V1 PERSISTENCE (UNCHANGED)
                # -------------------------
                else:
                    from data.repos.generated_content import GeneratedContentRepo

                    metadata = {
                        "execution_mode": request.execution_mode,
                        "model": "gemini-1.5",
                        "platforms": request.platforms
                    }

                    saved_record = await GeneratedContentRepo.save_generation(
                        brand_id=request.brand_id or "00000000",
                        voice_profile_id=request.brand_voice_profile.profile_id,
                        output_data=result,
                        brief_id=request.brief_id,
                        metadata=metadata
                    )

                    print(f"[EXECUTION_ROUTER] V1 Output persisted: {saved_record['id']}")

            except Exception as e:
                print(f"[EXECUTION_ROUTER] Warning: Failed to persist output: {str(e)}")


        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[EXECUTION_ROUTER] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/save")
async def save_content_manually(payload: SaveContentRequest):
    """
    Manually save generated content to the database.
    Used when content is generated ephemerally (save_to_db=False) and then saved later.
    """
    try:
        gen_repo = __import__('data.repos.generated_content', fromlist=['GeneratedContentRepo']).GeneratedContentRepo
        
        saved_record = await gen_repo.save_generation(
            brand_id=payload.brand_id,
            voice_profile_id=payload.voice_profile_id,
            output_data=payload.output_data,
            brief_id=payload.content_brief_id,
            metadata=payload.metadata
        )
        print(f"[EXECUTION_ROUTER] Manual Save Success: {saved_record['id']}")
        return {"status": "success", "id": saved_record['id']}
        
    except Exception as e:
        print(f"[EXECUTION_ROUTER] Manual Save Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{brand_id}")
async def get_content_by_brand(
    brand_id: str,
    execution_version: Optional[str] = None,
    brief_id: Optional[str] = None
):
    """
    Retrieve generated content for a brand.
    Supports:
    - v1 (single voice)
    - v2 (multi-persona)
    - Auto-resolution (try v2, then v1)
    - Filtering by brief_id (optional)
    """
    try:
        records = []
        final_version = execution_version
        
        # Search Strategy:
        # 1. If explicit version requested, search only that.
        # 2. If no version (None), try V2 (Machine) first, then V1.
        
        search_v2 = (execution_version == "v2" or execution_version is None)
        search_v1 = (execution_version == "v1" or execution_version is None)
        
        # Attempt V2 Search
        if search_v2:
            try:
                from data.repos.generated_content_machine import GeneratedContentMachineRepo
                records = await GeneratedContentMachineRepo.fetch_generations_by_brand(
                    brand_id,
                    limit=1,
                    brief_id=brief_id
                )
                if records:
                    final_version = "v2"
            except ImportError:
                print("[EXECUTION_ROUTER] Warning: GeneratedContentMachineRepo not available")
            except Exception as e:
                 print(f"[EXECUTION_ROUTER] Warning: V2 fetch failed: {e}")

        # Attempt V1 Search (Fallback)
        if search_v1 and not records:
            from data.repos.generated_content import GeneratedContentRepo
            records = await GeneratedContentRepo.fetch_generations_by_brand(
                brand_id,
                limit=1,
                brief_id=brief_id
            )
            if records:
                final_version = "v1"

        if not records:
            return None

        record = records[0]

        # Parse JSON safely
        import json
        
        # V2 stores output in 'output_data', V1 in 'output_json' (usually)
        # But let's check keys dynamically or rely on Repo contract
        output = record.get("output_json") or record.get("output_data")
        
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except:
                pass # Keep as string if parse fails

        return {
            "id": record.get("id"),
            "execution_version": final_version,
            "output": output,
            "created_at": record.get("created_at")
        }

    except Exception as e:
        print(f"[EXECUTION_ROUTER] Error fetching content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check for Agent 3"""
    return {
        "status": "healthy",
        "agent": "Agent 3 - The Executor",
        "version": "1.0.0"
    }
