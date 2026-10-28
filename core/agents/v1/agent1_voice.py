"""
Agent 1: Brand Voice Profiler (The Style Police) - V1 Pure

This module implements the first stage of the 3-agent marketing content pipeline.
Agent 1's job is to ingest brand assets (PDFs, URLs, past content) and extract a 
mathematical "Golden Record" that defines the brand's unique voice.

Core Responsibilities:
- Extract explicit writing rules (do's, don'ts, forbidden phrases)
- Analyze tone characteristics (primary, secondary, description)
- Create a reusable system prompt for downstream agents
- Store structural metadata about example content
- STRICTLY V1: No persona, no dimensional scoring

Integration Points:
- Input: Called by `adapters/api/routers/ingest_router.py` (via VersionRouter)
- Output: Saves to `voice_profiles` table via `VoiceProfilesRepo`
"""
from typing import List, Dict, Optional, Any
from pathlib import Path
from core.voice.rule_extractor import extract_rules_from_text
from core.logging_utils import log_event
from langchain_google_genai import ChatGoogleGenerativeAI

async def run_agent1(
    source_docs: List[Any],
    source_text_for_rules: str,
    collection_name: str,
    trace_id: Optional[str] = None,
    **kwargs  # Absorb V2 args (persona_name, etc.) without crashing
) -> Dict:
    """
    Agent-1: Brand Voice Extraction (Pure V1).
    
    Orchestrates:
    1. Rule Extraction (explicit 'dos'/'donts', forbidden phrases)
    2. Tone Analysis
    3. Structural Analysis
    
    Args:
        source_docs: List of Document objects with metadata
        source_text_for_rules: Normalized text specifically for rule extraction
        collection_name: ChromaDB collection name
        trace_id: (Optional) trace ID for logging
        **kwargs: Ignored V2 arguments
        
    Returns:
        Dictionary containing the "Golden Record" of the brand voice (V1 schema).
    """
    
    # Check if this is a regeneration request
    is_regeneration = kwargs.get('regenerate', False)

    # LOG: TRIGGERED
    log_event(trace_id, "v1", "Agent1", "AGENT_TRIGGERED", f"Agent 1 V1 triggered (regenerate={is_regeneration})", "v1", "core/agents/v1/agent1_voice.py", "run_agent1")

    try:
        # 1. Create LLM Instance
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.7
        )

        # LOG: INGESTION STAGE
        doc_count = len(source_docs) if source_docs else 0
        log_event(trace_id, "v1", "Agent1", "INGESTION_STARTED", f"Processing {doc_count} documents", "v1", data={"doc_count": doc_count})

        # 2. Extract Voice Rules (Agent-1 Core Logic)
        # For regeneration: inject variation instruction so LLM produces fresh output
        text_for_extraction = source_text_for_rules
        if is_regeneration:
            variation_prefix = Path("prompts/regeneration_prefix.md").read_text(encoding="utf-8")
            text_for_extraction = variation_prefix + source_text_for_rules
        
        extraction_result = await extract_rules_from_text(
            text_for_extraction, 
            llm,
            pipeline_id=kwargs.get("pipeline_id", "unknown_pipeline"),
            agent_name="agent1_voice_v1"
        )
        
        # 3. Assemble V1 "Golden Record"
        golden_record = {
            "system_prompt": _generate_system_prompt(extraction_result),
            "explicit_rules": {
                "dos": extraction_result.get("dos", []),
                "donts": extraction_result.get("donts", []),
                "forbidden_phrases": extraction_result.get("forbidden_phrases", []),
                "preferred_vocabulary": extraction_result.get("preferred_vocabulary", []),
                "tone": extraction_result.get("tone", {})
            },
            "implicit_rules": extraction_result.get("style_metrics", {}),
            "examples_meta": {
                "collection": collection_name,
                "count": doc_count
            },
            "examples": [],  # Populated by ingestion pipeline
            "version": 1
        }
        
        # LOG: COMPLETED
        log_event(trace_id, "v1", "Agent1", "AGENT_COMPLETED", "Agent 1 V1 completed successfully", "v1")

        # Return strict V1 response
        return {
            "success": True,
            "version": 1,
            "raw_json": golden_record,
            "summary": {
                "dos_count": len(extraction_result.get("dos", [])),
                "donts_count": len(extraction_result.get("donts", []))
            }
        }

    except Exception as e:
        log_event(trace_id, "v1", "Agent1", "EXCEPTION", f"Agent 1 V1 Failed: {str(e)}", "v1", level="CRITICAL", data={"error": str(e)})
        raise e

def _generate_system_prompt(rules: Dict) -> str:
    """
    Compile extracted rules into a reusable LLM system prompt string.
    """
    tone = rules.get("tone", {})
    primary_tone = tone.get("primary", "Neutral")
    secondary_tones = ", ".join(tone.get("secondary", []))
    
    dos = "\n- ".join(rules.get("dos", []))
    donts = "\n- ".join(rules.get("donts", []))
    
    prompt = f"""You are a brand voice expert.
TONE: {primary_tone} ({secondary_tones})
 
STRICT GUIDELINES:
DO:
- {dos}
 
DON'T:
- {donts}
"""
    return prompt
