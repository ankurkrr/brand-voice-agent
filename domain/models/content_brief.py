from pydantic import BaseModel, Field
from typing import List, Dict, Union, Optional
from datetime import datetime
import uuid

class ContentBriefV1(BaseModel):
    """
    V1 Content Brief (Deterministic / Strategic).
    Standard immutable brief from Agent 2.
    """
    brief_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    topic: str
    target_audience: str
    key_messages: List[str]
    keywords: List[str]
    cta: str
    blog_outline: List[str]
    
    # Determinism
    source_fingerprint: Optional[str] = None
    
    # Metadata
    version: str = "v1"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True

class ContentBriefV2(ContentBriefV1):
    """
    V2 Content Brief (Adaptive / Trend-Aware).
    Extends V1 with trend data and competitive analysis.
    """
    base_brief_id: str  # Reference to V1 parent (if applicable) or linked V1
    
    # V2 Enhancements
    trend_score: float = 0.0
    competitive_gap: str = ""
    audience_segment: str = "Broad"
    confidence_score: float = 1.0
    freshness_window_days: int = 30
    
    # Metadata update
    version: str = "v2"

ContentBrief = Union[ContentBriefV1, ContentBriefV2]
