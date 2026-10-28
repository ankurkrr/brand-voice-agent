"""
Agent 3: Multi-Channel Executor (The Writer)

This module implements the final stage of the 3-agent marketing content pipeline.
Agent 3's job is to take the Voice Profile (Agent 1) + Content Brief (Agent 2) and
generate platform-native copy for Blog, LinkedIn, Twitter, and Email.

Core Responsibilities:
- Generate multi-platform content in a single execution (Pure Executor)
- Enforce strict input validation (Pre-Generation)

STRICT MODE ENFORCEMENT:
Agent 3 operates as a "pure executor" - it does NOT:
- Research topics
- Invent information
- Negotiate with users
- Compromise on voice rules
- Retry or Rewrite (Deterministic Execution)

Integration Points:
- Input: Called by `adapters/api/routers/execution_router.py`
- Output: Saves to `generated_content` table
"""
from typing import Dict
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from domain.models.agent3_request import Agent3Request, BrandVoiceProfile, ContentBrief
from domain.models.agent3_response import Agent3Response
from core.execution.input_validator import validate_all_inputs
from core.execution.platform_rules import PLATFORM_RULES, UNIVERSAL_CONSTRAINTS
from core.execution.metadata_logger import (
    ExecutionMetadata, hash_voice_profile, hash_content_brief, log_execution_metadata
)
from lib.utils.json_repair import safe_parse_json

from core.logging_utils import log_event
log_event(None, "unknown", "Agent3_V1", "FILE_LOADED", "File loaded", "v1", "core/agents/v1/agent3_execution.py")



# Constants
MODEL_NAME = "gemini-2.5-flash"

# Load system prompt
SYSTEM_PROMPT = Path("prompts/agent3_executor.md").read_text(encoding="utf-8")


async def run_agent3(request: Agent3Request, save_to_db: bool = True) -> Dict:
    """
    Agent 3 - The Executor (Pure)
    
    Converts brand voice profile + content brief into platform-native marketing copy.
    Pure execution: No retries, no internal validation loops.
    """
    from core.logging_utils import log_event
    trace_id = request.trace_id
    
    # LOG: TRIGGERED
    log_event(trace_id, "v1", "Agent3", "AGENT_TRIGGERED", "Agent 3 V1 Triggered", "v1", "core/agents/v1/agent3_execution.py", "run_agent3")
    
    # Step 0: Auto-Fetch (If inputs missing but brand_id provided)
    if request.brand_id and (not request.brand_voice_profile or not request.content_brief):
        from data.repos.voice_profiles import VoiceProfilesRepo
        from data.repos.content_briefs import ContentBriefsRepo
        
        log_event(trace_id, "v1", "Agent3", "AUTO_FETCH_STARTED", "Fetching artifacts from DB", "v1")
        
        # 1. Fetch Voice Profile
        if not request.brand_voice_profile:
            # Prefer explicit profile ID if we could pass it, but Request model doesn't support it top-level yet.
            # We assume ACTIVE profile for the brand.
            # TODO: Add profile_id to Agent3Request for safer pipeline execution
            profile_data = await VoiceProfilesRepo.get_active_profile(request.brand_id)
            
            if not profile_data:
                raise ValueError(f"No active voice profile found for brand {request.brand_id}")
            
            # Map DB -> Model
            # DB returns dict with 'rules', 'class', etc.
            # We need to be careful about structure.
            # VoiceProfilesRepo.get_profile returns flattened 'rules' key.
            # But get_active_profile returns flat structure (dos, donts top level). We handle both.
            rules = profile_data.get('rules', {})
            tone = profile_data.get('tone') or rules.get('tone', {})
            
            request.brand_voice_profile = BrandVoiceProfile(
                profile_id=profile_data.get('profile_id') or profile_data.get('id'),
                tone=tone,
                dos=profile_data.get('dos') or rules.get('dos', []),
                donts=profile_data.get('donts') or rules.get('donts', []),
                forbidden_phrases=profile_data.get('forbidden_phrases') or rules.get('forbidden_phrases', []),
                preferred_vocabulary=profile_data.get('preferred_vocabulary') or rules.get('preferred_vocabulary', []),
                examples=profile_data.get('examples', [])
            )
            log_event(trace_id, "v1", "Agent3", "FETCH_PROFILE_SUCCESS", f"Fetched profile {request.brand_voice_profile.profile_id}", "v1")

        # 2. Fetch Content Brief
        if not request.content_brief:
            if not request.brief_id:
                 # Try to find latest? Or invalid?
                 # Pipeline should usually pass brief_id
                 raise ValueError("brief_id required for auto-fetch")
                 
            brief_row = await ContentBriefsRepo.get_brief(request.brief_id)
            if not brief_row:
                 raise ValueError(f"Content Brief {request.brief_id} not found")
            
            # ContentBriefsRepo.get_brief returns a normalized dict matching ContentBrief fields.
            # No need to extract "brief_data" key.
            # Map DB -> Model
            request.content_brief = ContentBrief(**brief_row)
            log_event(trace_id, "v1", "Agent3", "FETCH_BRIEF_SUCCESS", f"Fetched brief {request.brief_id}", "v1")

    # Initialize metadata tracking
    metadata = ExecutionMetadata(
        model=MODEL_NAME,
        voice_profile_hash=hash_voice_profile(request.brand_voice_profile),
        content_brief_hash=hash_content_brief(request.content_brief)
    )

    # Step 1: Pre-Generation Validation (MANDATORY)
    # Fail fast if inputs are invalid.
    is_valid, error_message = validate_all_inputs(
        request.brand_voice_profile,
        request.content_brief,
        request.platforms
    )
    
    if not is_valid:
        log_event(trace_id, "v1", "Agent3", "VALIDATION_FAILED", f"Input validation failed: {error_message}", "v1", level="ERROR")
        return {
            "error": "VALIDATION_FAILED",
            "message": error_message,
            "field": error_message.split(":")[0] if ":" in error_message else ""
        }
    
    log_event(trace_id, "v1", "Agent3", "PROFILE_AND_BRIEF_RECEIVED", "Inputs validated", "v1")

    # Step 2: Prepare execution context (Prompt Engineering)
    execution_context = _build_execution_context(
        request.brand_voice_profile,
        request.content_brief,
        request.platforms
    )
    
    
    log_event(trace_id, "v1", "Agent3", "PLATFORM_RULES_MERGED", "Prompt context built", "v1")
    
    # DEBUG: Print prompt snippet
    print("--------------------------------------------------")
    print("[AGENT3] GENERATED PROMPT SNIPPET (Voice Section):")
    print(execution_context[:500]) # First 500 chars should contain the voice profile section
    print("--------------------------------------------------")

    # Instantiate LLM
    # If regenerating, use higher temperature for variation. Otherwise, strict determinism.
    temperature = 0.7 if getattr(request, "regenerate", False) else 0.0
    
    if getattr(request, "regenerate", False):
        log_event(trace_id, "v1", "Agent3", "REGENERATION_MODE", "Regenerating with temperature=0.7", "v1")

    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=temperature
    )
    
    # Step 3: Execute (Pure Generation)
    try:
        log_event(trace_id, "v1", "Agent3", "GENERATION_STARTED", "Executing single-pass generation", "v1")
        result = await _execute_generation(execution_context, llm, getattr(request, "pipeline_id", "unknown_pipeline"))
        
        log_event(trace_id, "v1", "Agent3", "FINAL_OUTPUT_GENERATED", "Generation successful", "v1")

        # Log metadata
        if save_to_db:
            log_execution_metadata(metadata)
        
        log_event(trace_id, "v1", "Agent3", "AGENT_COMPLETED", "Agent 3 V1 Completed", "v1")
        
        # Return result (Agent3Response dump) directly
        return result
        
    except Exception as e:
        log_event(trace_id, "v1", "Agent3", "EXCEPTION", f"Execution error: {str(e)}", "v1", level="ERROR", data={"error": str(e)})
        metadata.voice_violations.append(f"EXECUTION_ERROR: {str(e)}")
        log_execution_metadata(metadata)
        
        return {
            "error": "EXECUTION_FAILED",
            "message": f"Failed to generate content: {str(e)}",
            "field": ""
        }


def _build_execution_context(
    profile: BrandVoiceProfile,
    brief: ContentBrief,
    platforms: list
) -> str:
    """
    Build the execution prompt with all inputs
    """
    # Serialize brand voice rules
    brand_voice_section = f"""
## BRAND VOICE PROFILE

**Profile ID:** {profile.profile_id if profile.profile_id else "UNKNOWN_PROFILE_ID"}

**Tone:**
- Primary: {profile.tone.get('primary', 'Not specified')}
- Secondary: {', '.join(profile.tone.get('secondary', []))}
- Description: {profile.tone.get('description', 'Not provided')}

**DO's ({len(profile.dos)} rules):**
{chr(10).join(f'- {rule}' for rule in profile.dos)}

**DON'Ts ({len(profile.donts)} rules):**
{chr(10).join(f'- {rule}' for rule in profile.donts)}

**Forbidden Phrases ({len(profile.forbidden_phrases)} phrases):**
{', '.join(profile.forbidden_phrases) if profile.forbidden_phrases else 'None specified'}

**Preferred Vocabulary ({len(profile.preferred_vocabulary)} terms):**
{', '.join(profile.preferred_vocabulary) if profile.preferred_vocabulary else 'None specified'}

**BRAND VOICE EXAMPLES (Mimic this style!):**
{chr(10).join(f'- "{ex}"' for ex in profile.examples) if profile.examples else 'No key examples provided.'}
"""
    
    # Serialize content brief
    content_brief_section = f"""
## CONTENT BRIEF

**Topic:** {brief.topic}

**Target Audience:** {brief.target_audience}

**Key Messages ({len(brief.key_messages)} messages - ALL MUST BE INCLUDED):**
{chr(10).join(f'{i+1}. {msg}' for i, msg in enumerate(brief.key_messages))}

**Call-to-Action:** {brief.cta}

**SEO Keywords:** {', '.join(brief.keywords) if brief.keywords else 'None provided'}

**Blog Outline (H2 headings):**
{chr(10).join(f'- {heading}' for heading in brief.blog_outline) if brief.blog_outline else 'Not applicable'}
"""
    
    # Serialize platform rules
    platform_rules_section = "## PLATFORM RULES\n\n"
    for platform in platforms:
        rules = PLATFORM_RULES.get(platform, {})
        platform_rules_section += f"**{platform.upper()}:**\n"
        for key, value in rules.items():
            platform_rules_section += f"- {key}: {value}\n"
        platform_rules_section += "\n"
    
    # Add universal constraints
    platform_rules_section += "**UNIVERSAL CONSTRAINTS:**\n"
    for key, value in UNIVERSAL_CONSTRAINTS.items():
        platform_rules_section += f"- {key}: {value}\n"
    
    # Combine all sections
    full_prompt = f"""
{SYSTEM_PROMPT}

---

# EXECUTION INPUTS

{brand_voice_section}

{content_brief_section}

{platform_rules_section}

---

# YOUR TASK

Generate platform-native marketing copy for the following platforms: {', '.join(platforms)}

**CRITICAL REMINDERS:**
1. Apply brand voice rules to EVERY sentence
2. Use content brief as single source of truth
3. Follow platform rules exactly
4. Include ALL {len(brief.key_messages)} key messages across all platforms
5. NEVER use forbidden phrases
6. Return ONLY valid JSON matching the schema
7. No explanations, no markdown, no commentary

Generate the content now.
"""
    
    return full_prompt


async def _execute_generation(prompt: str, llm: any, pipeline_id: str = "unknown_pipeline") -> Dict:
    """
    Execute the LLM generation
    """
    import time
    import uuid
    from core.execution.token_tracker import TokenTracker
    tracker = TokenTracker()
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    
    # Execute
    response = await llm.ainvoke(prompt)
    
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    await tracker.track_llm_usage(
        request_id=request_id,
        pipeline_id=pipeline_id,
        agent_name="agent3_execution_v1",
        provider="gemini",
        model=getattr(llm, "model", "gemini-2.5-flash"),
        response=response,
        latency_ms=latency_ms
    )
    
    # Parse JSON response
    try:
        result = safe_parse_json(response.content)
        # Check if LLM returned an error (Execution Rejected)
        if "error" in result:
            print(f"[AGENT3] LLM returned error: {result['error']}")
            # Normalize 'reason' to 'message' if needed (LLM prompt uses 'reason')
            if "message" not in result and "reason" in result:
                result["message"] = result["reason"]
            return result
        
        # Validate schema
        validated = Agent3Response(**result)
        return validated.model_dump()
        
    except Exception as e:
        print(f"[AGENT3] Failed to parse LLM response: {str(e)}")
        print(f"[AGENT3] Raw content (first 1000 chars):\n{response.content[:1000]}")
        
        # Return structured error
        return {
            "error": "PARSING_FAILED",
            "message": f"Failed to parse Agent 3 response: {str(e)}",
            "field": ""
        }
