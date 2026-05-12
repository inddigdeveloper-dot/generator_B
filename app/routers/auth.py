from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.db.database import get_db
from app.db.models import UserBusiness
from app.schemas.user import (
    BusinessOut,
    BusinessRegister,
    GoogleAuthPayload,
    LoginBusiness,
    RefreshTokenRequest,
    Token,
    UpdateProfile,
    UserProfile,
) 
from app.services import auth as auth_services

router = APIRouter()


@router.post("/register", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: BusinessRegister, db: Session = Depends(get_db)):
    if auth_services.get_user(db, payload.user_name):
        raise HTTPException(status_code=400, detail="Username already exists")
    if auth_services.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    user = UserBusiness(
        name=payload.name,
        user_name=payload.user_name,
        business_name=payload.business_name,
        email=payload.email,
        seo_keyword=payload.seo_keyword,
        mobile_no=payload.mobile_no,
        hashed_password=auth_services.get_password_hash(payload.password),
        review_link=payload.review_link,
        business_desc=payload.business_desc,
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginBusiness, db: Session = Depends(get_db)):
    user = auth_services.authenticate_user(db, payload.login_id, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=auth_services.create_access_token({"sub": user.user_name}),
        refresh_token=auth_services.create_refresh_token({"sub": user.user_name}),
        token_type="bearer",
    )


@router.post("/google", response_model=Token)
@limiter.limit("10/minute")
def google_auth(request: Request, payload: GoogleAuthPayload, db: Session = Depends(get_db)):
    try:
        google_data = auth_services.verify_google_token(payload.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google token",
        )

    google_id: str = google_data["sub"]
    email: str = google_data["email"]
    name: str = google_data.get("name", "")

    user = db.query(UserBusiness).filter(UserBusiness.google_id == google_id).first()

    if not user:
        existing = auth_services.get_user_by_email(db, email)
        if existing:
            existing.google_id = google_id
            db.commit()
            db.refresh(existing)
            user = existing
        else:
            import random as _rng
            base_username = email.split("@")[0]
            username = base_username
            suffix_pool = [google_id[:6]] + [str(_rng.randint(100, 9999)) for _ in range(8)]
            for suffix in suffix_pool:
                candidate = f"{base_username}_{suffix}" if auth_services.get_user(db, username) else username
                if not auth_services.get_user(db, candidate):
                    username = candidate
                    break
            else:
                raise HTTPException(status_code=500, detail="Could not generate unique username")

            user = UserBusiness(
                name=name,
                user_name=username,
                business_name=name,
                email=email,
                google_id=google_id,
                auth_provider="google",
                seo_keyword=[],
                mobile_no="",
                review_link="",
                business_desc="",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    return Token(
        access_token=auth_services.create_access_token({"sub": user.user_name}),
        refresh_token=auth_services.create_refresh_token({"sub": user.user_name}),
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
def refresh_tokens(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_data = auth_services.decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    username: str | None = token_data.get("sub")
    if not username or not auth_services.get_user(db, username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return Token(
        access_token=auth_services.create_access_token({"sub": username}),
        refresh_token=auth_services.create_refresh_token({"sub": username}),
        token_type="bearer",
    )


@router.get("/me", response_model=UserProfile)
def get_me(current_user: UserBusiness = Depends(auth_services.get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfile)
def update_me(
    payload: UpdateProfile,
    db: Session = Depends(get_db),
    current_user: UserBusiness = Depends(auth_services.get_current_user),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user
