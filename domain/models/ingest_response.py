from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ARD V1 Schema for Agent 1 Output

class ToneDefinition(BaseModel):
    """
    Tone structure derived from linguistic patterns.
    NOT adjectives alone - must be behavioral.
    """
    primary: str = Field(..., description="Primary tone descriptor")
    secondary: List[str] = Field(default_factory=list, description="Secondary tone descriptors")
    description: str = Field(..., description="Behavioral definition of tone")


class BestMatchExample(BaseModel):
    """
    Example demonstrating tone through actual text.
    NOT placeholders - must reflect sentence length, verb strength, cadence.
    """
    example_id: str = Field(..., description="Unique identifier (ex_1, ex_2, ex_3)")
    text: str = Field(..., description="Actual example text from source material")


class IngestResponse(BaseModel):
    """
    ARD V1 Compliant Agent 1 Output.
    
    Flat structure (no nested voice_profile).
    Exactly 3 best_match_examples enforced.
    Output is persistable and reusable.
    """
    brand_id: str
    profile_id: Optional[str] = Field(None, description="Unique identifier for the generated profile")
    status: Optional[str] = Field(None, description="Ingestion status (e.g. 'ingested_only')")
    version: Optional[int] = Field(1, description="Version number of the profile")
    tone: Optional[ToneDefinition] = None
    dos: Optional[List[str]] = Field(None, description="Enforceable binary-checkable rules")
    donts: Optional[List[str]] = Field(None, description="Enforceable binary-checkable rules")
    best_match_examples: Optional[List[BestMatchExample]] = Field(
        None, 
        description="Exactly 3 examples - no more, no less"
    )
    raw_json: Optional[Dict[str, Any]] = Field(None, description="Full raw JSON response from Agent 1")
    profile_data: Optional[Dict[str, Any]] = Field(None, description="Complete profile data for session storage")
    
    class Config:
        json_schema_extra = {
            "example": {
                "brand_id": "7979249c-f62b-4d42-85fb-48dca9035bbc",
                "tone": {
                    "primary": "Professional",
                    "secondary": ["Analytical", "Authoritative"],
                    "description": "Fact-based and direct communication"
                },
                "dos": [
                    "Use active voice",
                    "Lead with data",
                    "Keep sentences under 20 words"
                ],
                "donts": [
                    "Avoid exclamation marks",
                    "Don't use jargon without context",
                    "Never start with questions"
                ],
                "best_match_examples": [
                    {
                        "example_id": "ex_1",
                        "text": "Our platform processes 10M transactions daily. Performance metrics show 99.9% uptime."
                    },
                    {
                        "example_id": "ex_2",
                        "text": "Data security follows ISO 27001 standards. All transmissions use AES-256 encryption."
                    },
                    {
                        "example_id": "ex_3",
                        "text": "Integration requires three steps: authentication, configuration, deployment."
                    }
                ]
            }
        }


# Backward compatibility alias (deprecated)
VoiceProfile = IngestResponse
VoiceProfileResponse = IngestResponse
