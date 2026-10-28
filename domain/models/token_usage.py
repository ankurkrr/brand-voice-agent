from pydantic import BaseModel, Field, root_validator
from datetime import datetime, timezone
from typing import Optional, Dict, Any

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TokenUsage(BaseModel):
    request_id: str
    pipeline_id: str
    agent_name: str
    provider: str
    model: Optional[str] = None
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: Optional[float] = 0.0
    latency_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
