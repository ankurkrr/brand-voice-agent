from pydantic import BaseModel, Field
from typing import Optional


class IngestRequest(BaseModel):
    """Request schema for text/URL ingestion."""
    brand_name: Optional[str] = Field(None, description="Brand name. If not provided, auto-generated.")
    input_type: str = Field(..., description="Type of input: 'text' or 'url'")
    input_value: str = Field(..., description="Text content or URL to ingest")
