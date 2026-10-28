from core.ideation.schemas import StrategicBrief
from core.ideation.web_research import gather_web_signals
from core.ideation.signal_analyzer import analyze_signals
from langchain_core.prompts import PromptTemplate
from pathlib import Path
import json

PROMPT_TEMPLATE = Path("prompts/content_brief.md").read_text(encoding="utf-8")

async def build_content_brief(
    topic: str,
    llm,
    market: str = "",
    region: str = "",
    content_goal: str = "",
    pre_gathered_signals: dict = None,
    previous_feedback: str = "",
    pipeline_id: str = "unknown_pipeline"
):
    # STEP 1 — Gather Signals
    if pre_gathered_signals:
        web_signals = pre_gathered_signals
    else:
        web_signals = await gather_web_signals(topic, market, region, pipeline_id=pipeline_id)

    # Sanitize signals for the LLM to prevent schema poisoning and context bloat.
    # The full 'results' array contains raw 'title' keys which confuses the structured output parser.
    prompt_signals = {
        "titles": web_signals.get("titles", []),
        "snippets": web_signals.get("snippets", []),
        "signal_count": web_signals.get("signal_count", 0)
    }

    # Convert sanitized signals to string
    try:
        signals_str = json.dumps(prompt_signals, indent=2)
    except Exception:
        signals_str = str(prompt_signals)
        
    # STEP 1.5 - Gap Analysis
    # We must construct a pseudo CompetitiveSignals object to pass to analyze_signals
    # since analyze_signals expects an object with `.competitor_angles`
    class _MockSignals:
        def __init__(self, angles):
            self.competitor_angles = angles
            
    # Tavily returns "titles" which we map to "competitor_angles" for the analyzer
    mock_signals = _MockSignals(web_signals.get("titles", []))
    gap_model = await analyze_signals(llm, mock_signals, pipeline_id)
    gap_dict = gap_model.model_dump()
    gap_str = gap_model.model_dump_json(indent=2)

    # STEP 2 — Build Prompt (Now expecting gap_analysis and previous_feedback)
    prompt = PromptTemplate(
        input_variables=["topic", "market", "region", "content_goal", "web_signals", "gap_analysis", "previous_feedback"],
        template=PROMPT_TEMPLATE
    )

    # STEP 3 — Structured LLM Binding
    structured_llm = llm.with_structured_output(StrategicBrief, include_raw=True)
    chain = prompt | structured_llm

    import time
    import uuid
    from core.execution.token_tracker import TokenTracker
    tracker = TokenTracker()
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    result_wrapper = await chain.ainvoke({
        "topic": topic,
        "market": market or "General",
        "region": region or "Global",
        "content_goal": content_goal or "Comprehensive coverage",
        "web_signals": signals_str,
        "gap_analysis": gap_str,
        "previous_feedback": previous_feedback if previous_feedback else "None (First Attempt)"
    })

    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    await tracker.track_llm_usage(
        request_id=request_id,
        pipeline_id=pipeline_id,
        agent_name="agent2_ideation",
        provider="gemini",
        model=getattr(llm, "model", "gemini-2.5-flash"),
        response=result_wrapper["raw"],
        latency_ms=latency_ms
    )

    result: StrategicBrief = result_wrapper["parsed"]

    # Flatten out the result into a dict. 
    # agent2_ideation expects a tuple of (brief_data, gap_analysis_data, raw_signals)
    brief_data = result.model_dump()
    brief_data["fingerprint"] = web_signals.get("fingerprint", "")
    brief_data["web_signals"] = web_signals
    
    return brief_data, gap_dict, mock_signals.competitor_angles
