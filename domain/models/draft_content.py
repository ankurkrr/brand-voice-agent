from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any, Optional
from datetime import datetime
import uuid

class DraftContentV1(BaseModel):
    """
    V1 Draft Content (Pure Deterministic).
    Single-pass generation from Agent 3.
    """
    draft_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    platform: str
    content: Dict[str, Any]  # The generated JSON content
    
    # Lineage
    voice_profile_id: str
    brief_id: str
    
    # Metadata
    version: str = "v1"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True

class DraftContentV2(DraftContentV1):
    """
    V2 Draft Content (Adaptive / Varied).
    Includes multiple variants and semantic checks.
    """
    base_draft_id: Optional[str] = None
    
    # V2 Enhancements
    variants: List[Dict[str, Any]] = []
    best_variant_index: int = 0
    confidence_score: float = 1.0
    semantic_check_passed: bool = True
    
    # Metadata update
    version: str = "v2"

DraftContent = Union[DraftContentV1, DraftContentV2]
