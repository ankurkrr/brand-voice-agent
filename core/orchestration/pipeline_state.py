from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

class PipelineStatus(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PipelineStepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    NOT_STARTED = "NOT_STARTED"
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class PipelineState(BaseModel):
    """
    Immutable snapshot of the pipeline state.
    Tracks the progress of a brand's content generation workflow.
    """
    pipeline_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    mode: Literal["v1", "v2"] = "v1"  # Default to V1
    status: PipelineStatus = PipelineStatus.IDLE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Artifact IDs
    voice_profile_id: Optional[str] = None
    brief_id: Optional[str] = None
    execution_id: Optional[str] = None
    
    # Step Statuses
    steps: Dict[str, PipelineStepStatus] = {
        "voice_profiling": PipelineStepStatus.PENDING,
        "ideation": PipelineStepStatus.PENDING,
        "execution": PipelineStepStatus.PENDING
    }
    
    # Metadata for audit trail
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

    class Config:
        frozen = True  # Enforce immutability
