from pydantic import BaseModel, EmailStr
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    user_name: Optional[str] = None
