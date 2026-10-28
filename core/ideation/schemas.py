from pydantic import BaseModel, Field
from typing import List, Literal

class StrategicBrief(BaseModel):
    """The generated content strategy brief (Deep Level 5 Structure)."""
    search_intent: Literal["Informational", "Investigational", "Transactional"] = Field(...)
    buyer_stage: Literal["Top", "Middle", "Bottom"] = Field(...)
    
    # Flattened Persona Fields (Avoids Langchain nested JSON Schema extraction bugs)
    persona_role: str = Field(description="The primary job title or role of the target reader.")
    persona_seniority: str = Field(description="e.g. Executive, Mid-level, Entry-level, General Public")
    persona_company_type: str = Field(description="The type of industry or organization they belong to.")
    persona_primary_pain_point: str = Field(description="The specific challenge or problem this content solves.")
    
    differentiation_strategy: str = Field(
        ..., 
        description="Explicit declaration of how this brief stands out from the SRRP (SERP) saturated themes."
    )
    seo_keywords: List[str] = Field(description="3-15 strategic keywords")
    h2_outline: List[str] = Field(description="3-10 section headings")
    key_takeaways: List[str] = Field(description="2-8 factual insights")
