import logging
import json
from typing import Optional, Any, Literal
from datetime import datetime
import uuid

# Configure root logger (stdout is default, no need to specify stream)
logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_logger(name: str):
    """
    Returns a logger instance.
    In this setup, we rely on the root logger configured above, 
    but this allows for future extensibility.
    """
    return logging.getLogger(name)

def log_event(
    trace_id: Optional[str],
    pipeline_version: Literal["v1", "v2", "unknown"],
    agent: str,
    stage: str,
    message: str,
    agent_version: Literal["v1", "v2", "unknown"] = "unknown", 
    file: Optional[str] = None,
    function: Optional[str] = None,
    data: Optional[Any] = None,
    level: Literal["INFO", "ERROR", "CRITICAL"] = "INFO"
):
    """
    Logs a structured event in JSON format.
    
    Args:
        trace_id: Unique trace ID for the request.
        pipeline_version: "v1" or "v2".
        agent: Name of the agent (e.g., "agent_1", "router", "orchestrator").
        stage: Lifecycle stage (e.g., "TRIGGERED", "COMPLETED").
        message: Human-readable message.
        agent_version: Version of the agent ("v1" or "v2").
        file: Filename where log originated.
        function: Function name where log originated.
        data: Safe payload snapshot (optional).
        level: Log level.
    """
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "trace_id": trace_id or "NO_TRACE_ID",
        "pipeline": pipeline_version,
        "agent": agent,
        "version": agent_version,
        "file": file or "unknown",
        "function": function or "unknown",
        "stage": stage,
        "message": message,
        "data": data,
        "level": level
    }
    
    # Serialize to JSON
    try:
        json_log = json.dumps(log_entry, default=str)
    except Exception as e:
        # Fallback if serialization fails
        log_entry["data"] = f"SERIALIZATION_ERROR: {str(e)}"
        json_log = json.dumps(log_entry, default=str)

    logger = logging.getLogger(agent)
    
    if level == "INFO":
        logger.info(json_log)
    elif level == "ERROR":
        logger.error(json_log)
    elif level == "CRITICAL":
        logger.critical(json_log)
