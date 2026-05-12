from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional


class BusinessRegister(BaseModel):
    name: str
    business_name: str
    email: EmailStr
    user_name: str
    seo_keyword: List[str]
    mobile_no: str
    password: str
    review_link: str
    business_desc: str


class LoginBusiness(BaseModel):
    login_id: str
    password: str


class GoogleAuthPayload(BaseModel):
    token: str


class BusinessOut(BaseModel):
    id: int
    business_name: str
    qr_code_url: Optional[str] = None

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    id: int
    name: str
    user_name: str
    business_name: str
    email: str
    mobile_no: str
    seo_keyword: List[str]
    review_link: str
    business_desc: str
    qr_code_url: Optional[str] = None
    google_place_id: Optional[str] = None
    auth_provider: str
    language: str = "English"
    tone: str = "Professional"
    bill_items: str = ""

    model_config = {"from_attributes": True}


class UpdateProfile(BaseModel):
    name: Optional[str] = None
    business_name: Optional[str] = None
    mobile_no: Optional[str] = None
    review_link: Optional[str] = None
    seo_keyword: Optional[List[str]] = None
    business_desc: Optional[str] = None
    google_place_id: Optional[str] = None
    language: Optional[str] = None
    tone: Optional[str] = None
    bill_items: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("English", "Hindi", "Hinglish"):
            raise ValueError("language must be one of: English, Hindi, Hinglish")
        return v

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("Professional", "Friendly", "Enthusiastic"):
            raise ValueError("tone must be one of: Professional, Friendly, Enthusiastic")
        return v


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_name: Optional[str] = None
