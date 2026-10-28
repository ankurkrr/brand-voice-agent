from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
from datetime import datetime
import uuid

class VoiceProfileV1(BaseModel):
    """
    V1 Voice Profile (Deterministic / Static).
    Standard immutable voice definition.
    """
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    tone: Dict[str, Any]  # primary, secondary, description
    dos: List[str]
    donts: List[str]
    forbidden_phrases: List[str]
    preferred_vocabulary: List[str]
    examples: List[str]
    
    # Metadata
    version: str = "v1"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True  # Immutable

class VoiceProfileV2(VoiceProfileV1):
    """
    V2 Voice Profile (Adaptive / Multi-Persona).
    Extends V1 with dimensional scoring and persona variants.
    """
    base_profile_id: str  # Reference to V1 parent
    persona_type: str = "default"  # e.g., "CEO", "Support", "Marketing"
    
    # V2 Enhancements
    tone_dimensions: Dict[str, float] = {}  # e.g., {"authority": 0.8, "empathy": 0.4}
    drift_score: float = 0.0
    confidence_score: float = 1.0
    
    # Metadata update
    version: str = "v2"
    
    # Multi-Modal Audio Profile (Optional)
    audio_profile: Optional[Dict[str, Any]] = None  # Stores AudioMetrics + CadenceRules
    transcript_meta: Optional[Dict[str, Any]] = None
    modalities: Optional[Union[List[str], Dict[str, Any]]] = None


# Union type for type hinting
VoiceProfile = Union[VoiceProfileV1, VoiceProfileV2]
