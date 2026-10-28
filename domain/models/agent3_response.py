"""
Agent 3 Response Schema
Defines the strict output structure for Agent 3 (The Executor)
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class BlogOutput(BaseModel):
    """Blog content output"""
    title: str = Field(..., description="Blog post title")
    content: str = Field(..., description="Full blog post content with H2 headings")


class LinkedInOutput(BaseModel):
    """LinkedIn post output"""
    post: str = Field(..., description="LinkedIn post content")


class TwitterOutput(BaseModel):
    """Twitter/X thread output"""
    thread: List[str] = Field(..., description="Thread of tweets (each ≤280 chars)")


class EmailOutput(BaseModel):
    """Email campaign output"""
    subject: str = Field(..., description="Email subject line")
    preview: str = Field(..., description="Preview text (50-100 chars)")
    body: str = Field(..., description="Email body content")
    cta: str = Field(..., description="Call-to-action button text")


class Agent3Response(BaseModel):
    """
    Complete Agent 3 output
    All platforms must be present in response
    """
    blog: Optional[BlogOutput] = None
    linkedin: Optional[LinkedInOutput] = None
    twitter: Optional[TwitterOutput] = None
    email: Optional[EmailOutput] = None
    
    # Additional fields provided by Agent 3 V2 execution
    version: Optional[int] = None
    execution_metadata: Optional[Dict[str, Any]] = None
    execution_id: Optional[str] = None
    usage_summary: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"
        json_schema_extra = {
            "example": {
                "blog": {
                    "title": "How AI Transforms Marketing",
                    "content": "## What is AI Marketing\n\nAI marketing uses..."
                },
                "linkedin": {
                    "post": "AI is transforming marketing. Here's how:\n\n1. Saves time\n2. Improves accuracy..."
                },
                "twitter": {
                    "thread": [
                        "AI is changing marketing forever. Here's what you need to know 🧵",
                        "1/ AI saves marketers 10+ hours per week on repetitive tasks",
                        "2/ Start your AI journey today. Get a free trial 👇"
                    ]
                },
                "email": {
                    "subject": "Transform Your Marketing with AI",
                    "preview": "Discover how AI saves time and improves results",
                    "body": "Hi there,\n\nAI is revolutionizing how we market...",
                    "cta": "Start Free Trial"
                }
            }
        }


class Agent3ErrorResponse(BaseModel):
    """Error response when Agent 3 cannot execute"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    field: str = Field(default="", description="Field that caused the error")
