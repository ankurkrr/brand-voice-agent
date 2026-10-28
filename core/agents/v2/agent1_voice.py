"""
Agent 1 V2: Brand Voice Refinement Agent
Strictly refines, analyzes, and scores an existing V1 Golden Record.
"""
from typing import Dict, Optional, List, Any
import json
import logging
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
# Updated imports for modern LangChain
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from data.repos.voice_personas import VoicePersonasRepo


# Configure Logging
logger = logging.getLogger("Agent1_V2")
logger.setLevel(logging.INFO)

from core.logging_utils import log_event
log_event(None, "unknown", "Agent1_V2", "FILE_LOADED", "File loaded", "v2", "core/agents/v2/agent1_voice.py")


# ==============================================================================
# 1. Output Schema Definition (Strict Contract)
# ==============================================================================

class RefinedExplicitRules(BaseModel):
    tone: Dict[str, Any] = Field(..., description="Refined tone object with primary, secondary, and description.")
    dos: List[str] = Field(..., description="List of refined DO rules.")
    donts: List[str] = Field(..., description="List of refined DONT rules.")
    best_match_examples: List[str] = Field(default_factory=list, description="Examples that best match the clarified voice.")

class ImplicitRules(BaseModel):
    avg_sentence_length: int = Field(..., description="Estimated average sentence length.")
    reading_level: str = Field(..., description="Estimated reading level (e.g., 'Grade 8', 'College').")
    formality_bias: str = Field(..., description="low, medium, or high")
    emotional_intensity: str = Field(..., description="low, medium, or high")

class DimensionalScores(BaseModel):
    authority: float = Field(..., ge=0.0, le=1.0)
    empathy: float = Field(..., ge=0.0, le=1.0)
    innovation: float = Field(..., ge=0.0, le=1.0)
    urgency: float = Field(..., ge=0.0, le=1.0)

class Agent1V2Response(BaseModel):
    refined_explicit_rules: RefinedExplicitRules
    implicit_rules: ImplicitRules
    dimensional_scores: DimensionalScores

    @validator("dimensional_scores")
    def check_scores(cls, v):
        if v is None:
            raise ValueError("dimensional_scores cannot be null")
        return v

# ==============================================================================
# 2. Main Execution Function
# ==============================================================================

async def run_agent1(
    parent_profile: Dict[str, Any] = None, # Make optional to support doc-based entry
    source_docs: Any = None,
    source_text_for_rules: Any = None,
    collection_name: Any = None,
    persona_name: Any = None,
    parent_persona_id: Any = None,
    brand_id: Any = None,
    trace_id: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    Agent 1 V2: Refinement & Persona Logic.
    
    Orchestrates:
    1. Base Profile Acquisition (from input or by calling V1)
    2. Refinement (LLM)
    3. Dimensional Scoring (Strict Cache)
    4. Persona Creation
    
    Args:
        parent_profile: V1 Golden Record (optional if docs provided)
        source_docs, source_text_for_rules, collection_name: V1 inputs (if parent_profile missing)
    """
    from core.logging_utils import log_event
    from core.voice.dimensional_scorer import DimensionalScorer
    import uuid
    from core.agents.v1.agent1_voice import run_agent1 as run_agent1_v1

    # LOG: TRIGGERED
    log_event(trace_id, "v2", "Agent1", "AGENT_TRIGGERED", "Agent 1 V2 Refinement Started", "v2", "core/agents/v2/agent1_voice.py", "run_agent1")
    
    try:
        # -------------------------------------------------------------------------
        # 1. ACQUIRE BASE PROFILE (Delegation Logic)
        # -------------------------------------------------------------------------
        if not parent_profile:
            # Check if we have V1 inputs
            if source_docs and source_text_for_rules:
                log_event(trace_id, "v2", "Agent1", "DELEGATION_STARTED", "Delegating to V1 for base profile", "v2")
                v1_result = await run_agent1_v1(
                    source_docs=source_docs,
                    source_text_for_rules=source_text_for_rules,
                    collection_name=collection_name,
                    trace_id=trace_id
                )
                if not v1_result.get("success"):
                     raise ValueError("V1 Delegation Failed")
                
                # Extract the golden record from V1 response
                parent_profile = v1_result.get("raw_json")
                if not parent_profile:
                     raise ValueError("V1 returned no raw_json")
                     
                log_event(trace_id, "v2", "Agent1", "DELEGATION_COMPLETED", "Received base profile from V1", "v2")
            else:
                log_event(trace_id, "v2", "Agent1", "VALIDATION_FAILED", "Missing parent_profile AND source_docs", "v2", level="ERROR")
                raise ValueError("CRITICAL: Input missing. Provide 'parent_profile' OR 'source_docs' + 'source_text_for_rules'.")

        # -------------------------------------------------------------------------
# Validate Base Profile (V1 Golden Record)
# -------------------------------------------------------------------------

        required_keys = ["system_prompt", "explicit_rules"]
        for k in required_keys:
            if k not in parent_profile:
                raise ValueError(f"Invalid Base Profile: Missing {k}")

        # -------------------------------------------------------------------------
        # 1.5 ENSURE BRAND ID (STRICT INVARIANT)
        # -------------------------------------------------------------------------

        if not brand_id:
            brand_id = parent_profile.get("brand_id")

        if not brand_id:
            log_event(
                trace_id,
                "v2",
                "Agent1",
                "VALIDATION_FAILED",
                "brand_id missing for persona creation",
                "v2",
                level="CRITICAL"
            )
            raise ValueError(
                "Agent1 V2 requires brand_id to create persona "
                "(not found in args or parent_profile)"
            )

        # -------------------------------------------------------------------------
        # 1.6 ENSURE DEFAULT PERSONAS (V2 Requirement)
        # -------------------------------------------------------------------------
        from core.voice.persona_manager import PersonaManager
        log_event(trace_id, "v2", "Agent1", "CHECK_DEFAULTS", "Ensuring default personas exist", "v2")
        await PersonaManager.ensure_default_personas(brand_id)


        # -------------------------------------------------------------------------
        # 2. Setup LLM & Refinement
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # 2. Setup LLM & Refinement (Pydantic Output Parser)
        # -------------------------------------------------------------------------
        parser = PydanticOutputParser(pydantic_object=Agent1V2Response)
        
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
        
        prompt_text = """
        You are Agent-1 V2: Brand Voice Refinement Agent.
        
        TASK:
        Refine and analyze the provided Brand Voice.
        
        INPUTS:
        System Prompt: "{system_prompt}"
        Explicit Rules: {explicit_rules_json}
        
        {format_instructions}
        
        IMPORTANT: Return ONLY the JSON object. Do not include markdown formatting or additional text.
        """
        # Note: Dimensional scoring removed from LLM prompt, handled by Scorer
        
        prompt = PromptTemplate(
            template=prompt_text,
            input_variables=["system_prompt", "explicit_rules_json"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | llm 
        
        log_event(trace_id, "v2", "Agent1", "LLM_CALL_STARTED", "Refining rules", "v2")
        try:
            import time
            import uuid
            from core.execution.token_tracker import TokenTracker
            tracker = TokenTracker()
            request_id = str(uuid.uuid4())
            start_time = time.perf_counter()

            # Execute unparsed Chain
            raw_llm_response = await chain.ainvoke({
                "system_prompt": parent_profile.get("system_prompt", ""),
                "explicit_rules_json": json.dumps(parent_profile.get("explicit_rules", {}))
            })
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            await tracker.track_llm_usage(
                request_id=request_id,
                pipeline_id=kwargs.get("pipeline_id", "unknown_pipeline"),
                agent_name="agent1_voice_v2",
                provider="gemini",
                model=getattr(llm, "model", "gemini-2.5-flash"),
                response=raw_llm_response,
                latency_ms=latency_ms
            )

            # Parse Output
            data_obj = parser.invoke(raw_llm_response)
            
            # Convert to dict for downstream compatibility
            data = data_obj.dict()
            
        except Exception as e:
            log_event(trace_id, "v2", "Agent1", "EXCEPTION", f"Refinement Failed: {e}", "v2", level="ERROR")
            # Attempt fallback manual parsing if Pydantic fails (sometimes LLM wraps in markdown despite instructions)
            # But the PydanticOutputParser usually handles markdown blocks too.
            raise RuntimeError(f"Refinement Failed: {e}")

        # -------------------------------------------------------------------------
        # 3. DIMENSIONAL SCORING (Strict Cache)
        # -------------------------------------------------------------------------
        scorer = DimensionalScorer()
        dimensions = ["Humor", "Empathy", "Authority", "Formality", "Urgency"]
        
        # Determine text to score
        score_text = source_text_for_rules
        if not score_text:
             # Fallback: Score the system prompt if source text unavailable
             # This happens in pure refinement mode
             score_text = parent_profile.get("system_prompt", "")
             log_event(trace_id, "v2", "Agent1", "INFO", "Scoring System Prompt (Source text unavailable)", "v2")

        if not score_text:
             raise ValueError("No text available for dimensional scoring")

        try:
            log_event(trace_id, "v2", "Agent1", "SCORING_STARTED", "Calculating dimensional scores", "v2")
            dimensional_scores = await scorer.score_dimensions(score_text, dimensions)
        except Exception as e:
            # V2 MUST ABORT if scoring fails (Strict Rule 4)
             log_event(trace_id, "v2", "Agent1", "SCORING_FAILED", f"Dimensional Scoring Failed: {e}", "v2", level="CRITICAL")
             raise RuntimeError(f"Dimensional Scoring Failed: {e}")

        # -------------------------------------------------------------------------
        # 4. PERSONA & OUTPUT ASSEMBLY
        # -------------------------------------------------------------------------
        persona_id = str(uuid.uuid4())
        
        # Merge Refined Data
        result = {
            "refined_explicit_rules": data.get("refined_explicit_rules", {}),
            "implicit_rules": data.get("implicit_rules", {}),
            "dimensional_scores": dimensional_scores,
            "persona_id": persona_id,
            "persona_name": persona_name or "Refined Persona",
            "parent_persona_id": parent_persona_id,
            "brand_id": brand_id,
            "version": 2
        }

        # -------------------------------------------------
        # 4.1 PERSIST PERSONA (HARD REQUIREMENT FOR V2)
        # -------------------------------------------------
        refined = data.get("refined_explicit_rules", {})

        profile_data = {
            "tone": refined.get("tone", {}),
            "dos": refined.get("dos", []),
            "donts": refined.get("donts", []),
            "forbidden_phrases": [],
            "preferred_vocabulary": [],
            "examples": refined.get("best_match_examples", [])
        }

        await VoicePersonasRepo.create_persona(
            persona_id=persona_id,
            brand_id=brand_id,
            persona_name=persona_name or "Refined Persona",
            parent_persona_id=parent_persona_id,
            profile_data=profile_data,
            dimensional_scores=dimensional_scores,
            status="ACTIVE"
        )


        
        # Add profile_id if needed by persisting layer (usually it's persona_id)
        # But ensure we don't break contracts expecting 'raw_json'
        
        log_event(trace_id, "v2", "Agent1", "AGENT_COMPLETED", "Refinement Successful", "v2", data={"persona_id": persona_id})
        return result

    except Exception as e:
        log_event(trace_id, "v2", "Agent1", "EXCEPTION", f"Agent 1 V2 Crash: {e}", "v2", level="ERROR")
        raise e

