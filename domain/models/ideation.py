from pydantic import BaseModel, Field, field_validator

# ARD V1 Schema for Agent 2 Output

class IdeationRequest(BaseModel):
    """
    Agent 2 Input Schema with Hard Boundary Enforcement.
    
    FORBIDDEN FIELDS (will raise validation error):
    - tone, voice, style (Agent 1 outputs)
    - dos, donts, examples (Agent 1 outputs)
    
    This ensures Agent 2 never receives voice data.
    """
    brand_id: str
    topic: str
    market: str = ""
    region: str = ""
    content_goal: str = ""
    session_id: str = None  # Optional session tracking
    
    class Config:
        extra = "forbid"  # Reject any extra fields
    
    @field_validator('*', mode='before')
    @classmethod
    def reject_tone_contamination(cls, v, info):
        """Prevent tone/voice fields from being passed."""
        field_name = info.field_name if hasattr(info, 'field_name') else ''
        
        FORBIDDEN = {'tone', 'voice', 'style', 'dos', 'donts', 'examples'}
        if field_name.lower() in FORBIDDEN:
            raise ValueError(
                f"BOUNDARY VIOLATION: Agent-2 cannot accept '{field_name}'. "
                f"Voice/tone data must not be passed to Agent-2."
            )
        return v


class ContentBriefData(BaseModel):
    """
    ARD V1 Frozen Contract for Agent 2 Output.

    Canonical de-duplicated shape:
    - ui_presentation: UI-facing chips/labels (single source of truth for audience/keywords/outline/takeaways)
    - raw_strategy: Deep strategic reasoning object
    - web_signals: Research provenance
    - metrics: Scoring diagnostics
    """
    raw_strategy: dict = Field(default_factory=dict, description="Deep strategy object from the LLM pass")
    ui_presentation: dict = Field(default_factory=dict, description="Canonical UI-facing labels/chips")
    web_signals: dict = Field(default_factory=dict, description="Tavily live research search results")
    metrics: dict = Field(default_factory=dict, description="Composite score and gap analysis mapping output")
    
    class Config:
        frozen = False  # Allow flexibility
        extra = "ignore" # Ignore extra fields from LLM
        json_schema_extra = {
            "version": "1.0.0",
            "agent": "Agent-2",
            "contract_type": "flexible",
        }


class IdeationResponseConstraints(BaseModel):
    voice_profile_id: str
    must_follow_voice: bool


class IdeationResponse(BaseModel):
    brief_id: str
    content_brief: ContentBriefData
    constraints: IdeationResponseConstraints
    
    class Config:
        json_schema_extra = {
            "example": {
                "brief_id": "uuid-here",
                "content_brief": {
                    "raw_strategy": {
                        "search_intent": "Investigational",
                        "buyer_stage": "Middle"
                    },
                    "ui_presentation": {
                        "target_audience": "Healthcare administrators evaluating AI adoption",
                        "seo_keywords": ["AI diagnostics", "healthcare AI", "medical imaging AI"],
                        "h2_outline": [
                            "AI Diagnostic Applications",
                            "Data Privacy Considerations",
                            "Implementation Requirements"
                        ],
                        "key_takeaways": [
                            "FDA approved multiple AI diagnostic tools",
                            "Healthcare AI market projected to grow"
                        ]
                    },
                    "web_signals": {
                        "signal_count": 3
                    },
                    "metrics": {
                        "composite_score": 8.2
                    }
                },
                "constraints": {
                    "voice_profile_id": "uuid-here",
                    "must_follow_voice": True
                }
            }
        }

class SaveBriefRequest(BaseModel):
    """
    Explicit schema for saving a generated brief.
    This resolves Pydantic/FastAPI Body conflicts.
    """
    brief_id: str
    brand_id: str
    voice_profile_id: str
    topic: str
    content_brief: ContentBriefData
    constraints: IdeationResponseConstraints
