from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class ReviewGenerateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    customer_name: Optional[str] = Field(None, max_length=100)
    experience: Optional[str] = Field(None, max_length=500)


class ReviewOut(BaseModel):
    id: int
    customer_name: Optional[str]
    rating: int
    review_text: str
    google_review_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    reviews: List[ReviewOut]
    total: int
