from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FeedbackRequest(BaseModel):
    accepted: bool

class UpdateRulesRequest(BaseModel):
    tone: Dict[str, Any]  # Changed from str to Dict to match frontend payload
    dos: List[str]
    donts: List[str]
