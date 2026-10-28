from typing import Optional, Dict, Literal
from core.orchestration.pipeline_state import PipelineState, PipelineStatus, PipelineStepStatus
from core.orchestration.version_router import route_agent1, route_agent2, route_agent3
from domain.models.agent3_request import Agent3Request
from data.repos.pipeline_state import PipelineStateRepo
from data.repos.voice_profiles import VoiceProfilesRepo
from data.repos.content_briefs import ContentBriefsRepo
import uuid
from datetime import datetime
from core.logging_utils import log_event

# File Load Logging
log_event(
    trace_id=None,
    pipeline_version="unknown",
    agent="PipelineRunner", 
    stage="FILE_LOADED",
    message="PipelineRunner loaded",
    agent_version="unknown",
    file="core/orchestration/pipeline_runner.py"
)


class PipelineRunner:
    """
    Central orchestration engine.
    Enforces the execution order: Voice -> Ideation -> Execution.
    Dispatches to appropriate agent version via VersionRouter.
    """

    @staticmethod
    async def create_pipeline(brand_id: str, mode: Literal["v1", "v2"] = "v1") -> PipelineState:
        """Initialize a new pipeline tracking state."""
        # Create pipeline (generates trace_id automatically in State model)
        state = await PipelineStateRepo.create_pipeline(brand_id, mode)
        
        # LOG: Pipeline Selected
        log_event(
            trace_id=state.trace_id,
            pipeline_version=mode,
            agent="Orchestrator",
            stage="PIPELINE_SELECTED",
            message=f"Pipeline version {mode} selected.",
            agent_version=mode,
            file="core/orchestration/pipeline_runner.py",
            function="create_pipeline",
            data={"reason": "create_pipeline request", "brand_id": brand_id}
        )
        return state

    @staticmethod
    async def get_pipeline(pipeline_id: str) -> Optional[PipelineState]:
        """Retrieve pipeline state by ID."""
        return await PipelineStateRepo.get_pipeline(pipeline_id)

    @staticmethod
    async def run_step(pipeline_id: str, step_name: str, payload: dict) -> PipelineState:
        """
        Execute a specific step in the pipeline.
        Enforces dependencies and updates state.
        """
        state = await PipelineStateRepo.get_pipeline(pipeline_id)
        if not state:
            # We can't log trace_id efficiently if we don't have the state, but we can log the error
            log_event(None, "unknown", "Orchestrator", "ERROR", f"Pipeline {pipeline_id} not found", "unknown", "core/orchestration/pipeline_runner.py", "run_step", level="ERROR")
            raise ValueError(f"Pipeline {pipeline_id} not found")

        # Inject trace_id and pipeline_id into payload for agents
        payload["trace_id"] = state.trace_id
        payload["pipeline_id"] = state.pipeline_id

        log_event(
            trace_id=state.trace_id,
            pipeline_version=state.mode,
            agent="Orchestrator",
            stage="STEP_STARTED",
            message=f"Starting step: {step_name}",
            agent_version=state.mode,
            function="run_step",
            data={"step": step_name}
        )

        try:
            if step_name == "voice_profiling":
                return_state = await PipelineRunner._run_voice_profiling(state, payload)
            elif step_name == "ideation":
                return_state = await PipelineRunner._run_ideation(state, payload)
            elif step_name == "execution":
                return_state = await PipelineRunner._run_execution(state, payload)
            else:
                log_event(state.trace_id, state.mode, "Orchestrator", "ERROR", f"Unknown step: {step_name}", state.mode, "core/orchestration/pipeline_runner.py", "run_step", level="ERROR")
                raise ValueError(f"Unknown step: {step_name}")

            # Agent level Cost Check
            import os
            from data.repos.token_usage_repo import TokenUsageRepo
            try:
                usage = await TokenUsageRepo.aggregate_pipeline(pipeline_id)
                max_cost = float(os.getenv("MAX_PIPELINE_COST", "10.0"))
                if usage.get("total_cost_usd", 0.0) > max_cost:
                    log_event(state.trace_id, state.mode, "Orchestrator", "BUDGET_EXCEEDED", f"Cost exceeded max allowed: ${max_cost}", state.mode, level="ERROR")
                    raise RuntimeError("BudgetExceededError: Pipeline cost exceeded safety threshold")
            except Exception as e:
                if "BudgetExceededError" in str(e):
                    raise
                log_event(state.trace_id, state.mode, "Orchestrator", "ERROR", f"Failed budget check: {str(e)}", state.mode, level="ERROR")
                
            return return_state

        except Exception as e:
            log_event(
                trace_id=state.trace_id,
                pipeline_version=state.mode,
                agent="Orchestrator",
                stage="EXCEPTION",
                message=f"Exception in step {step_name}: {str(e)}",
                agent_version=state.mode,
                function="run_step",
                data={"error": str(e), "step": step_name},
                level="ERROR"
            )
            # Reraise to let router handle HTTP error
            raise e

    @staticmethod
    async def approve_step(pipeline_id: str, step_name: str, feedback: Optional[str] = None) -> PipelineState:
        """
        Handle user approval for a step.
        """
        state = await PipelineStateRepo.get_pipeline(pipeline_id)
        if not state:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        log_event(state.trace_id, state.mode, "Orchestrator", "STEP_APPROVAL", f"Approving step {step_name}", state.mode, "core/orchestration/pipeline_runner.py", "approve_step")

        if step_name == "voice_profiling":
             if not state.voice_profile_id:
                 raise ValueError("No voice profile to approve")
             # Update VoiceProfileRepo
             await VoiceProfilesRepo.update_status(state.voice_profile_id, "APPROVED")
             # Update PipelineStateRepo
             await PipelineStateRepo.update_agent_status(pipeline_id, "agent1", "APPROVED")

        elif step_name == "ideation":
             if not state.brief_id:
                 raise ValueError("No content brief to approve")
             # Update ContentBriefRepo
             await ContentBriefsRepo.update_status(state.brief_id, "APPROVED")
             # Update PipelineStateRepo
             await PipelineStateRepo.update_agent_status(pipeline_id, "agent2", "APPROVED")
             
        else:
            raise ValueError(f"Approval not supported for step: {step_name}")
            
        return await PipelineStateRepo.get_pipeline(pipeline_id)

    @staticmethod
    async def reject_step(pipeline_id: str, step_name: str, feedback: Optional[str] = None) -> PipelineState:
        """
        Handle user rejection for a step.
        """
        state = await PipelineStateRepo.get_pipeline(pipeline_id)
        if not state:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        log_event(state.trace_id, state.mode, "Orchestrator", "STEP_REJECTION", f"Rejecting step {step_name}", state.mode, "core/orchestration/pipeline_runner.py", "reject_step")

        if step_name == "voice_profiling":
             await VoiceProfilesRepo.update_status(state.voice_profile_id, "REJECTED")
             await PipelineStateRepo.update_agent_status(pipeline_id, "agent1", "REJECTED")
        elif step_name == "ideation":
             await ContentBriefsRepo.update_status(state.brief_id, "REJECTED")
             await PipelineStateRepo.update_agent_status(pipeline_id, "agent2", "REJECTED")
        else:
             raise ValueError(f"Rejection not supported for step: {step_name}")
             
        return await PipelineStateRepo.get_pipeline(pipeline_id)


    @staticmethod
    async def _run_voice_profiling(state: PipelineState, payload: dict) -> PipelineState:
        """Run Agent 1 (Routed)"""
        
        # Auto-Fetch Content if missing (Common in Pipeline flow)
        if "source_text_for_rules" not in payload:
             # Lazy import to avoid circular dependencies if any
             from core.storage.vector import fetch_chunks_from_chroma
             from lib.text.preprocess import join_documents
             
             collection_name = payload.get("collection_name") or f"brand_{state.brand_id}"
             print(f"[PIPELINE] Auto-fetching content for collection: {collection_name}")
             
             docs = fetch_chunks_from_chroma(collection_name)
             if not docs:
                 raise ValueError(f"No content found for brand {state.brand_id}. Please ingest content first (POST /ingest).")
                 
             payload["source_docs"] = docs
             payload["source_text_for_rules"] = join_documents(docs)
             payload["collection_name"] = collection_name
             
             # Ensure brand_id is passed
             payload["brand_id"] = state.brand_id

        # Execute Agent 1 via Router
        result = await route_agent1(state.mode, payload)

        # CONTRACT ADAPTER: V2 Schema -> Persistence Schema
        if state.mode == "v2":
            # 1. Fail Fast Checks
            if not result.get("refined_explicit_rules"):
                log_event(state.trace_id, "v2", "Agent1", "VALIDATION_FAILED", "refined_explicit_rules is empty", "v2", level="ERROR")
                raise ValueError("V2 Error: refined_explicit_rules is empty")
            
            # Strict Tone Check
            v2_rules = result["refined_explicit_rules"]
            if not v2_rules.get("tone"):
                 log_event(state.trace_id, "v2", "Agent1", "VALIDATION_FAILED", "refined_explicit_rules['tone'] is empty", "v2", level="ERROR")
                 raise ValueError("V2 Error: refined_explicit_rules['tone'] is empty")

            if not result.get("implicit_rules"):
                raise ValueError("V2 Error: implicit_rules is empty")
            if not result.get("dimensional_scores"):
                raise ValueError("V2 Error: dimensional_scores is empty")

            # 2. Map & Preserve Data (Strict Contract)
            parent_profile = payload.get("parent_profile", {})
            
            
            # 3. Persist (Explicitly for V2 as it returns dict only)
            parent_profile = payload["parent_profile"]

            log_event(state.trace_id, "v2", "Agent1", "DB_WRITE_ATTEMPT", "Saving V2 profile", "v2", "core/orchestration/pipeline_runner.py", "_run_voice_profiling")
            await VoiceProfilesRepo.save_profile_v2(
                brand_id=state.brand_id,
                parent_profile_id=parent_profile["profile_id"],
                agent1_v2_output=result
            )
            log_event(state.trace_id, "v2", "Agent1", "DB_WRITE_SUCCESS", "V2 Profile Saved", "v2", "core/orchestration/pipeline_runner.py", "_run_voice_profiling", data={"parent_profile_id": parent_profile["profile_id"]})

            # V2 refines the existing profile — ID does NOT change
            profile_id = parent_profile["profile_id"]
        else:
            # V1 Legacy: Profile ID is in the result (assuming V1 saves internally logic was WRONG)
            # We must save the pure functional output to the DB
            
            golden_record = result.get("raw_json", result)
            
            # --- Validaton: Fail if 0 Rules Extracted ---
            if not golden_record.get("explicit_rules", {}).get("dos"):
                 log_event(state.trace_id, "v1", "Agent1", "VALIDATION_FAILED", "Agent 1 extracted 0 rules (Dos list empty)", "v1", level="ERROR")
                 raise ValueError("Agent 1 failed to extract any rules (0 Dos found). Please verify you have ingested content (POST /ingest) for this brand.")
            # --------------------------------------------
            
            collection_name = payload.get("collection_name") or f"brand_{state.brand_id}"

            profile_data = {
                "collection_name": collection_name,
                "brand_id": state.brand_id,
                "system_prompt": golden_record.get("system_prompt", ""),
                "tone": golden_record.get("explicit_rules", {}).get("tone", {}),
                "rules": {
                    "dos": golden_record.get("explicit_rules", {}).get("dos", []),
                    "donts": golden_record.get("explicit_rules", {}).get("donts", []),
                    "forbidden_phrases": golden_record.get("explicit_rules", {}).get("forbidden_phrases", []),
                    "preferred_vocabulary": golden_record.get("explicit_rules", {}).get("preferred_vocabulary", []),
                },
                "style_metrics": golden_record.get("implicit_rules", {}),
                "embedding_meta": {"model": "models/embedding-001"},
                "stats": {"acceptance_rate": 0, "rewrite_count": 0, "locked": False}
            }

            # Save to Repo
            saved_profile = await VoiceProfilesRepo.save_profile(state.brand_id, profile_data)
            profile_id = saved_profile.get("id") or saved_profile.get("profile_id")
            
            log_event(state.trace_id, "v1", "Agent1", "DB_WRITE_SUCCESS", "V1 Profile Created/Saved", "v1", "core/orchestration/pipeline_runner.py", "_run_voice_profiling", data={"profile_id": profile_id})
        
        # Update State
        await PipelineStateRepo.update_agent_status(
            state.pipeline_id, 
            "agent1", 
            "DRAFT", 
            artifact_id=profile_id
        )
        
        return await PipelineStateRepo.get_pipeline(state.pipeline_id)

    @staticmethod
    async def _run_ideation(state: PipelineState, payload: dict) -> PipelineState:
        """Run Agent 2 (Routed)"""
        # 1. Check Dependency: Agent 1 must be APPROVED
        # We check the Repo source of truth, but state object is also good
        is_approved = await VoiceProfilesRepo.is_approved(state.voice_profile_id)
        if not is_approved:
            # Double check pipeline state for faster feedback
            if state.steps["voice_profiling"] != "APPROVED":
                log_event(state.trace_id, state.mode, "Orchestrator", "SHORT_CIRCUIT_RETURN", "Voice Profile not approved", state.mode, level="INFO")
                raise ValueError("Cannot run Ideation. Voice Profile must be APPROVED first.")

        # Enforce boundary: Agent 2 gets brand_id, NOT voice profile data
        if "brand_id" not in payload:
            payload["brand_id"] = state.brand_id

        # Execute Agent 2 via Router
        result = await route_agent2(state.mode, payload)
        
        brief_id = result.get("brief_id")
        
        # Update State
        await PipelineStateRepo.update_agent_status(
            state.pipeline_id, 
            "agent2", 
            "DRAFT", 
            artifact_id=brief_id
        )
        
        return await PipelineStateRepo.get_pipeline(state.pipeline_id)

    @staticmethod
    async def _run_execution(state: PipelineState, payload: dict) -> PipelineState:
        """Run Agent 3 (Routed)"""
        # 1. Check Dependency: Agent 2 must be APPROVED
        is_brief_approved = await ContentBriefsRepo.is_approved(state.brief_id)
        if not is_brief_approved:
             log_event(state.trace_id, state.mode, "Orchestrator", "SHORT_CIRCUIT_RETURN", "Content Brief not approved", state.mode, level="INFO")
             raise ValueError("Cannot run Execution. Content Brief must be APPROVED first.")
             
        # 2. Check Dependency: Agent 1 must be APPROVED (redundant if Agent 2 enforced, but safe)
        is_voice_approved = await VoiceProfilesRepo.is_approved(state.voice_profile_id)
        if not is_voice_approved:
             log_event(state.trace_id, state.mode, "Orchestrator", "SHORT_CIRCUIT_RETURN", "Voice Profile not approved (Double Check)", state.mode, level="INFO")
             raise ValueError("Cannot run Execution. Voice Profile must be APPROVED.")
        
        # Construct Request object from payload
        # Ensure we pass the IDs from the state to ensure we use the correct artifacts
        payload["brand_id"] = state.brand_id
        payload["brief_id"] = state.brief_id

        # ---------------------------------
            # V1 EXECUTION CONTRACT
        # ---------------------------------
        if state.mode == "v1":
            payload["execution_version"] = "v1"

            # REQUIRED for V1
            payload["voice_profile_id"] = state.voice_profile_id
            payload["pipeline_id"] = state.pipeline_id # explicitly inject pipeline_id

            # DO NOT allow persona in V1
            payload.pop("persona_id", None)

        # -------------------------------
        # V2 EXECUTION CONTRACT ADAPTER
        # -------------------------------
        # ---------------------------------
        # V2 EXECUTION CONTRACT
        # ---------------------------------
        if state.mode == "v2":
            payload["execution_version"] = "v2"
            payload.setdefault("platforms", ["blog", "linkedin", "twitter", "email"])

            # 🔑 AUTO-RESOLVE PERSONA (THIS WAS MISSING)
            if "persona_id" not in payload:
                persona = await VoicePersonasRepo.get_default_persona(
                    brand_id=state.brand_id
                )

                if not persona:
                    raise ValueError(
                        "No persona found for brand. Agent-3 V2 cannot execute."
                    )

                payload["persona_id"] = persona.persona_id

                # STRICT: no voice_profile_id in V2
                payload.pop("voice_profile_id", None)
    

        
        try:
            request = Agent3Request(**payload)
        except Exception as e:
            log_event(
                trace_id=state.trace_id,
                pipeline_version=state.mode,
                agent="Agent3",
                stage="REQUEST_VALIDATION_FAILED",
                message=str(e),
                agent_version=state.mode,
                level="ERROR",
                data={"payload_keys": list(payload.keys())}
            )
            raise ValueError("Invalid payload for Agent 3")
        
        # Execute Agent 3 via Router
        result = await route_agent3(state.mode, request)

        if "error" in result:
             log_event(state.trace_id, state.mode, "Orchestrator", "AGENT_ERROR", "Agent 3 returned error", state.mode, data=result, level="ERROR")
             raise ValueError(result["message"])

        # Attach usage metrics wrapper
        try:
             from data.repos.token_usage_repo import TokenUsageRepo
             usage_summary = await TokenUsageRepo.aggregate_pipeline(state.pipeline_id)
             result["usage_summary"] = usage_summary
        except Exception as e:
             log_event(state.trace_id, state.mode, "Orchestrator", "ERROR", f"Failed to attach usage metrics: {str(e)}", state.mode, level="ERROR")


        # Update State
        # Agent 3 doesn't have an explicit ID in the same way, or maybe it does? 
        # result typically has 'execution_id' or we generate one?
        # Agent 3 execution returns generated content.
        # Assuming result has 'execution_id' or 'id'
        execution_id = result.get("execution_id", result.get("id"))

        await PipelineStateRepo.update_agent_status(
            state.pipeline_id, 
            "agent3", 
            "COMPLETED", 
            artifact_id=execution_id
        )
        
        return await PipelineStateRepo.get_pipeline(state.pipeline_id)
