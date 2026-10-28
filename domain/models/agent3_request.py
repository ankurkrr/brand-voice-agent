"""
Agent 3 Request Schema
Defines the input structure for Agent 3 (The Executor)
"""
from pydantic import BaseModel, Field, field_validator, model_validator, validator
from typing import List, Dict, Optional, Any, Literal



class ContentBrief(BaseModel):
    """Content Brief from Agent 2"""
    topic: str = Field(..., description="Main topic/subject of the content")
    target_audience: str = Field(..., description="Target audience description")
    key_messages: List[str] = Field(..., description="Core messages to communicate")
    keywords: List[str] = Field(default_factory=list, description="SEO keywords")
    cta: str = Field(..., description="Call-to-action text")
    blog_outline: List[str] = Field(default_factory=list, description="H2 headings for blog structure")


class BrandVoiceProfile(BaseModel):
    """Brand Voice Profile from Agent 1 (STRICT - Must be validated)"""
    profile_id: Optional[str] = Field(None, description="Brand voice profile ID from Agent 1")
    tone: Dict[str, Any] = Field(..., description="Tone specifications")
    dos: List[str] = Field(..., min_length=1, description="Writing dos (required)")
    donts: List[str] = Field(..., min_length=1, description="Writing don'ts (required)")
    forbidden_phrases: List[str] = Field(default_factory=list, description="Banned phrases")
    preferred_vocabulary: List[str] = Field(default_factory=list, description="Preferred terms")
    examples: List[str] = Field(default_factory=list, description="Best-match examples of brand voice")
    
    @validator('tone')
    def validate_tone(cls, v):
        if not v.get('primary'):
            raise ValueError("Tone must have 'primary' field")
        if not v.get('description'):
            raise ValueError("Tone must have 'description' field")
        return v


class Agent3Request(BaseModel):
    """
    Complete request for Agent 3 (STRICT MODE + AUTO-FETCH)
    
    Inputs Requirements:
    - EITHER `brand_id` provided (fetch data from DB)
    - OR `brand_voice_profile` AND `content_brief` provided (full manual input)
    - `platforms`: Required, must not be empty
    - `execution_mode`: 'single' or 'variants'
    """
    brand_id: Optional[str] = Field(None, description="Brand UUID for auto-fetching data from Agent 1 & 2")
    brief_id: Optional[str] = Field(None, description="Specific Content Brief UUID (optional, defaults to latest)")
    
    brand_voice_profile: Optional[BrandVoiceProfile] = Field(None, description="Brand voice rules from Agent 1")
    content_brief: Optional[ContentBrief] = Field(None, description="Content strategy from Agent 2")
    platforms: List[str] = Field(
        ...,
        min_length=1,
        description="Platforms to generate content for (required, non-empty)"
    )
    execution_mode: Literal["single", "variants"] = Field(
        default="single",
        description="Execution mode: 'single' for one version, 'variants' for multiple phrasings"
    )
    trace_id: Optional[str] = Field(None, description="Trace ID for logging")
    pipeline_id: Optional[str] = Field(None, description="Pipeline ID for tracking tokens")

    
    execution_version: Literal["v1", "v2"] = Field(
    default="v1",
    description="Execution version: v1 (single voice) or v2 (multi-persona)"
    )

    persona_id: Optional[str] = Field(
        None,
        description="Persona ID required for v2 (multi-persona) execution"
    )

    persona_ids: Optional[List[str]] = Field(
        None,
        description="List of Persona IDs for multi-persona v2 execution"
    )

    regenerate: bool = Field(
        False,
        description="If True, forces regeneration with higher temperature/variation"
    )

    
    @validator('platforms')
    def validate_platforms(cls, v):
        valid_platforms = {"blog", "linkedin", "twitter", "email"}
        invalid = set(v) - valid_platforms
        if invalid:
            raise ValueError(f"Unknown platforms: {invalid}. Must be from {valid_platforms}")
        return v
        
    @model_validator(mode="after")
    def validate_manual_mode_requirements(self):
        # Case 1: Auto-fetch mode (brand_id provided)
        if self.brand_id:
            return self

        # Case 2: Manual mode (no brand_id)
        # MUST have both profile and brief
        if not self.brand_voice_profile or not self.content_brief:
            raise ValueError("Must provide either 'brand_id' OR both 'brand_voice_profile' and 'content_brief'")
        
        # Validate content_brief completeness
        # We know content_brief is not None here due to check above
        if not self.content_brief.blog_outline:
            raise ValueError("content_brief.h2_outline is required and must not be empty")
        if not self.content_brief.target_audience:
            raise ValueError("content_brief.target_audience is required")
        if not self.content_brief.key_messages:
            raise ValueError("content_brief.key_messages is required and must not be empty")
            
        return self

    @model_validator(mode="after")
    def enforce_v2_persona(self):
        # Only enforce persona_id if brand_id is NOT provided
        if (
            self.execution_version == "v2"
            and not self.persona_id
            and not self.persona_ids
            and not self.brand_id
        ):
            raise ValueError(
                "persona_id (or persona_ids) is required for v2 when brand_id is not provided"
            )
        return self




    
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand_voice_profile": {
                    "tone": {
                        "primary": "Professional",
                        "secondary": ["Empowering", "Clear"],
                        "description": "Professional yet approachable communication"
                    },
                    "dos": ["Use active voice", "Keep sentences under 20 words"],
                    "donts": ["Use jargon", "Write in passive voice"],
                    "forbidden_phrases": ["leverage", "synergy"],
                    "preferred_vocabulary": ["empower", "transform"]
                },
                "content_brief": {
                    "topic": "AI in Marketing",
                    "target_audience": "Marketing professionals",
                    "key_messages": ["AI saves time", "AI improves accuracy"],
                    "keywords": ["AI marketing", "automation"],
                    "cta": "Start your free trial",
                    "blog_outline": ["What is AI Marketing", "Benefits of AI", "Getting Started"]
                },
                "platforms": ["blog", "linkedin", "twitter", "email"]
            }
        }
