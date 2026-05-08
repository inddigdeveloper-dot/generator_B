from typing import Optional

from pydantic import BaseModel, Field


class PublicBusinessInfo(BaseModel):
    business_name: str
    business_desc: Optional[str] = None


class PublicGenerateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    experience: Optional[str] = Field(None, max_length=500)


class PublicGenerateResponse(BaseModel):
    review_text: str
    google_review_url: str
