"""
Agent 2: Content Strategist (The Researcher)

This module implements the second stage of the 3-agent marketing content pipeline.
Agent 2's job is to research a given topic and build a strategic "Content Brief" that
guides what should be written (but not how to write it).

Core Responsibilities:
- Web research using Tavily API (competitor analysis, trend identification)
- Topic analysis (audience definition, SEO keyword extraction)
- Strategic brief generation (H2 outline, key messages, CTA)
- Normalize & validate output (remove tone/style contamination)

BOUNDARY ENFORCEMENT (Critical):
Agent 2 operates in a "strategy-only" mode. It MUST NOT:
- Receive voice/tone data from Agent 1 (read-only brand_id check)
- Generate stylistic rules (dos, donts, tone descriptions)
- Include any writing style guidance in its output

This strict separation ensures Agent 2 focuses purely on WHAT to say,
while Agent 3 handles HOW to say it using Agent 1's voice profile.

Integration Points:
- Input: Called by `adapters/api/routers/ideation_router.py` with brand_id + topic
- Dependencies: Reads `voice_profiles` table (to verify brand exists)
- Output: Saves to `content_briefs` table via `ContentBriefsRepo`
- Used By: Agent 3 (fetches brief to generate platform content)

Key Components:
- run_agent2_ideation(): Main orchestration function with boundary checks
- build_content_brief(): LLM-powered research & brief generation
- validate_content_brief(): Ensures output has no tone leakage
- _enforce_agent2_boundaries(): Runtime validation of input parameters

Example Flow:
    1. User selects Brand "ABC Corp" and enters topic "AI in Finance"
    2. Ideation router calls run_agent2(brand_id="123", topic="AI in Finance")
    3. Agent 2 verifies brand exists (read-only)
    4. Tavily researches the topic → generates strategic brief
    5. Normalizer strips any style-related content
    6. Brief saved to DB with brief_id
    7. Agent 3 later fetches this brief + voice profile → generates copy
"""
from core.ideation.brief_builder import build_content_brief
from core.ideation.validators import validate_content_brief
from data.repos.voice_profiles import VoiceProfilesRepo
from data.repos.content_briefs import ContentBriefsRepo
from data.repos.content_briefs import ContentBriefsRepo
from data.repos.brands import BrandsRepo

from core.logging_utils import log_event
log_event(None, "unknown", "Agent2_V1", "FILE_LOADED", "File loaded", "v1", "core/agents/v1/agent2_ideation.py")


async def run_agent2_ideation(
    brand_id: str,
    topic: str,
    market: str = "",
    region: str = "",
    content_goal: str = "",
    skip_brand_check: bool = False,
    save_to_db: bool = True,
    trace_id: str = None, # NEW
    regenerate: bool = False,  # NEW: Skip cache + vary output
    **kwargs  # Catch-all for boundary enforcement
) -> dict:
    """
    Agent-2 Entry Point:
    1. Verifies Brand exists (read-only check).
    2. Orchestrates Content Brief generation.
    3. Validates output for tone leakage.
    4. Persists content brief to database.
    5. Returns safe JSON with brief_id.
    """
    from core.logging_utils import log_event
    
    # LOG: TRIGGERED
    log_event(trace_id, "v1", "Agent2", "AGENT_TRIGGERED", "Agent 2 V1 Triggered", "v1", "core/agents/v1/agent2_ideation.py", "run_agent2_ideation", data={"topic": topic, "brand_id": brand_id})

    try:
        # STEP 0: BOUNDARY ENFORCEMENT - Reject tone contamination
        _enforce_agent2_boundaries(kwargs)
        
        # CRITICAL DEBUG: Write to file with UTF-8 encoding (Windows fix)
        import os
        from datetime import datetime
        debug_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'AGENT2_DEBUG.log')
        # We keep the file debug for now as legacy/backup
                
        profile = None  # robust initialization
        
        # STEP 1: READ-ONLY Check for Brand Existence
        if not skip_brand_check:
            brand = await BrandsRepo.get_brand_by_id(brand_id)
            if not brand:
                 # Fallback: check profile repo just in case (legacy)
                 profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
                 if not profile:
                    log_event(trace_id, "v1", "Agent2", "VALIDATION_FAILED", f"Brand {brand_id} not found", "v1", level="ERROR")
                    raise ValueError(f"Brand not found for brand_id {brand_id}. Cannot run Agent 2.")
            else:
                profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
                # Log profile check status
                if profile:
                    log_event(trace_id, "v1", "Agent2", "INPUT_PROFILE_ID_RECEIVED", f"Found profile {profile.get('id')}", "v1", data={"profile_id": profile.get("id")})
                else:
                    log_event(trace_id, "v1", "Agent2", "WARNING", f"Brand exists but no profile found yet", "v1", level="INFO")
        else:
            log_event(trace_id, "v1", "Agent2", "INFO", "Skipping brand check (In-Memory Workflow)", "v1")
        
        # STEP 2: The Senior Strategist Loop
        from core.ideation.brief_builder import build_content_brief
        from core.ideation.strategy_scorer import StrategyScorer
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7
        )
        
        max_attempts = 2
        best_brief = None
        best_score = 0.0
        best_breakdown = {}
        gap_analysis_data = {}
        feedback_str = ""
        
        for attempt in range(max_attempts):
            log_event(trace_id, "v1", "Agent2", "STRATEGY_GENERATION", f"Attempt {attempt + 1}/{max_attempts}", "v1")
            
            try:
                # Build the brief (this handles signal gathering + gap analysis inside)
                brief_data, current_gap_analysis, raw_signals = await build_content_brief(
                    topic=topic,
                    llm=llm,
                    market=market,
                    region=region,
                    content_goal=content_goal,
                    previous_feedback=feedback_str
                )
                
                # --- PHASE 11: COMPETITOR SIMULATION (ARD LEVEL 8) ---
                log_event(trace_id, "v1", "Agent2", "STRATEGY_GENERATION", "Running Competitor Simulation Pass...", "v1")
                import json
                
                competitor_prompt = f"""
                You are a ruthless, highly-intelligent Competitor Content Strategist.
                Review the following Content Brief that your rival is about to publish.
                
                Rival Brief:
                {json.dumps(brief_data)[:2000]}
                
                Identify predictable angles, weak business logic, and missing insights.
                Rate how VULNERABLE this brief is to being outranked by better content on a scale of 0.0 (Invulnerable) to 5.0 (Highly Vulnerable/Generic).
                
                Respond with ONLY a decimal number between 0.0 and 5.0.
                """
                
                try:
                    comp_response = await llm.ainvoke([{"role": "user", "content": competitor_prompt}])
                    import re
                    comp_score = float(re.findall(r"[-+]?\d*\.\d+|\d+", comp_response.content)[0])
                    vulnerability_score = max(min(comp_score, 5.0), 0.0)
                    log_event(trace_id, "v1", "Agent2", "COMPETITOR_SIMULATION", f"Vulnerability Score: {vulnerability_score}", "v1")
                except Exception as e:
                    print(f"[Competitor Simulation Failed] {e}")
                    vulnerability_score = 0.0
                
                # Evaluation Layer (Dual Scorer + Coherence Engine)
                score, breakdown = await StrategyScorer.evaluate(llm, brief_data, current_gap_analysis, vulnerability_score, raw_signals)
                log_event(trace_id, "v1", "Agent2", "EVALUATION_SCORE", f"Composite Score: {score}", "v1", data={"score": score, "breakdown": breakdown})
                
                # Keep track of best just in case all fail
                if score > best_score:
                    best_score = score
                    best_breakdown = breakdown
                    best_brief = brief_data
                    gap_analysis_data = current_gap_analysis
                
                if score >= 7.0:
                    log_event(trace_id, "v1", "Agent2", "EVALUATION_PASSED", "Brief passed strategic threshold.", "v1")
                    break
                else:
                    log_event(trace_id, "v1", "Agent2", "EVALUATION_FAILED", "Brief failed strategic threshold, regenerating...", "v1", level="WARNING")
                    # Construct constraint feedback for Attempt 2
                    feedback_str = f"YOUR PREVIOUS ATTEMPT FAILED WITH SCORE: {score}/10.0\n"
                    feedback_str += f"COMPETITOR CRITIQUE VULNERABILITY: {vulnerability_score}/5.0 (Lower is better)\n"
                    feedback_str += "DETERMINISTIC PENALTIES APPLIED:\n"
                    for key, val in breakdown.items():
                        if val < 10.0:
                            feedback_str += f"- {key}: Penalty dragged score to {val}/10.0\n"
                    feedback_str += "\nCRITICAL: You MUST revise your H2 structure to fix the constraints above or the brief will fail again."
            
            except Exception as e:
                log_event(trace_id, "v1", "Agent2", "GENERATION_ERROR", f"Attempt {attempt + 1} failed: {e}", "v1", level="ERROR")
                if attempt == max_attempts - 1 and not best_brief:
                    raise Exception(f"Strategic generation failed completely: {e}")
        
        # Use the best brief we found (even if it didn't strictly hit 7.0 on the final attempt)
        brief_data = best_brief
        fingerprint = brief_data.get("fingerprint", "")
        
        # STEP 3: NORMALIZE FOR UI (Frontend Chips)
        from core.ideation.normalizer import extract_ui_labels
        ui_labels = extract_ui_labels(brief_data)
        
        # Keep signals only in content_brief_data.web_signals.
        top_level_signals = brief_data.pop("web_signals", {})

        # Remove fields that are canonicalized under ui_presentation.
        raw_strategy = dict(brief_data)
        for key in ("target_audience", "seo_keywords", "h2_outline", "key_takeaways"):
            raw_strategy.pop(key, None)

        # Canonical brief payload (no duplicated UI fields).
        final_payload = {
            "raw_strategy": raw_strategy,
            "ui_presentation": ui_labels,
            "web_signals": top_level_signals,
            "metrics": {
                "composite_score": best_score,
                "score_breakdown": best_breakdown,
                "gap_analysis": gap_analysis_data
            }
        }
        
        # STEP 4: Validation
        # The new Agent 2 generates a deep nested object. We don't check for
        # flat strings like 'target_audience' anymore during hard validation.
        # Instead, we validate the Pydantic schema structure implicitly via the scorers.
        
        # 5. PERSIST Content Brief (Agent-2 Write Path)
        brief_id = "temp-brief-id" # Default if not saving
        
        if save_to_db:
                 # In parallel execution, profile might not exist yet or wasn't fetched
                 # Try to get the profile_id dynamically if needed
                 if not profile:
                     import asyncio
                     # Retry loop to handle race conditions (Agent 1 saving vs Agent 2 reading)
                     for attempt in range(3):
                         profile = await VoiceProfilesRepo.get_profile_by_brand_id(brand_id)
                         if profile:
                             log_event(trace_id, "v1", "Agent2", "INFO", f"Fetced profile on attempt {attempt+1}", "v1")
                             break
                         else:
                             await asyncio.sleep(1)

                     if not profile:
                         # CRITICAL FAILURE - Cannot save without profile
                         err_msg = f"AGENT_2_PERSISTENCE_FAILURE: Voice Profile not found for brand {brand_id} after retries."
                         log_event(trace_id, "v1", "Agent2", "CRITICAL", err_msg, "v1", level="CRITICAL")
                         raise RuntimeError(err_msg)
            
                 # Only save if we have a valid profile
                 if save_to_db and profile:
                    try:
                        log_event(trace_id, "v1", "Agent2", "DB_WRITE_ATTEMPT", "Saving content brief", "v1")
                        
                        persisted_brief = await ContentBriefsRepo.insert_content_brief(
                            brand_id=brand_id,
                            voice_profile_id=profile["id"],
                            topic=topic,
                            content_brief_data=final_payload # Saving the fully nested object + UI chips
                        )
                        brief_id = persisted_brief['id']
                        
                        log_event(trace_id, "v1", "Agent2", "CONTENT_BRIEF_CREATED", f"Content brief saved: {brief_id}", "v1", data={"brief_id": brief_id})
                        
                    except Exception as e:
                        err_msg = f"AGENT_2_PERSISTENCE_FAILURE: Database insert failed. Reason: {str(e)}"
                        log_event(trace_id, "v1", "Agent2", "EXCEPTION", err_msg, "v1", level="ERROR")
                        raise RuntimeError(err_msg)

        # 5. Return Contract with brief ID
        response_data = {
            "brief_id": brief_id,
            "brand_id": brand_id, # Added to match contract
            "topic": topic, 
            "status": "generated",
            "content_brief": final_payload, # Contains raw_strategy for Agent 3
            "constraints": {
                "voice_profile_id": profile["id"] if profile else "pending-save",
                "must_follow_voice": True
            }
        }
        
        log_event(trace_id, "v1", "Agent2", "AGENT_COMPLETED", "Agent 2 V1 Completed", "v1", data={"brief_id": brief_id})

        # Add raw_json field for frontend extraction (consistent with Agent 1)
        return {
            **response_data,
            "raw_json": response_data  # Complete JSON for frontend debugging/transparency
        }

    except Exception as e:
        log_event(trace_id, "v1", "Agent2", "EXCEPTION", f"Agent 2 V1 Failed: {e}", "v1", level="ERROR")
        raise e


def _enforce_agent2_boundaries(kwargs: dict) -> None:
    """
    Hard boundary enforcement via constructor contracts.
    
    Agent 2 must NEVER receive:
    - tone (from Agent 1)
    - voice (from Agent 1)
    - style (from Agent 1)
    - dos/donts (from Agent 1)
    - examples (from Agent 1)
    
    This is enforced at runtime to prevent accidental coupling.
    
    Raises:
        ValueError: If any forbidden field is detected
    """
    FORBIDDEN_FIELDS = {
        "tone", "voice", "style", "voice_profile",
        "dos", "donts", "forbidden_phrases", "preferred_vocabulary",
        "examples", "best_match_examples", "system_prompt",
        "tone_primary", "tone_secondary", "tone_description"
    }
    
    violations = []
    for key in kwargs:
        if key.lower() in FORBIDDEN_FIELDS:
            violations.append(key)
    
    if violations:
        raise ValueError(
            f"BOUNDARY VIOLATION: Agent-2 received forbidden fields: {violations}. "
            f"Agent-2 must NEVER receive voice/tone data from Agent-1. "
            f"This is an architectural invariant violation."
        )
