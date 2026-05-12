from pydantic import BaseModel, Field


class SmartReplyRequest(BaseModel):
    review_text: str = Field(..., min_length=5, max_length=1000)
    tone: str = Field("Professional")
    language: str = Field("English")


class SmartReplyResponse(BaseModel):
    reply: str
