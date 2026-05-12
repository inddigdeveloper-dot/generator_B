from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.database import get_db
from app.db.models import UserBusiness

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def authenticate_user(db: Session, login_id: str, password: str) -> UserBusiness | bool:
    # 1. Search across all three allowed login columns
    user = (
        db.query(UserBusiness)
        .filter(
            or_(
                UserBusiness.user_name == login_id,
                UserBusiness.email == login_id,
                UserBusiness.mobile_no == login_id,
            )
        )
        .first()
    )

    # 2. If user doesn't exist, mitigate timing attacks
    if not user:
        # We hash a dummy password so the request takes the same amount
        # of time, hiding whether the user exists or not.
        verify_password(password, DUMMY_HASH)
        return False

    # 3. Google-only accounts have no password — must use /auth/google
    if not user.hashed_password:
        return False

    # 4. Verify password for local accounts
    if not verify_password(password, user.hashed_password):
        return False

    return user


def verify_google_token(token: str) -> dict:
    request = google_requests.Request()
    payload = id_token.verify_oauth2_token(token, request, settings.google_client_id)
    return payload


def get_user(db: Session, username: str) -> UserBusiness | None:
    return db.query(UserBusiness).filter(UserBusiness.user_name == username).first()


def get_user_by_email(db: Session, email: str) -> UserBusiness | None:
    return db.query(UserBusiness).filter(UserBusiness.email == email).first()


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload.update({"exp": expire, "type": "access"})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload.update({"exp": expire, "type": "refresh"})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers=_BEARER_CHALLENGE,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers=_BEARER_CHALLENGE,
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserBusiness:
    """Return the authenticated user based on a JWT access token.

    The token is decoded, the ``sub`` claim is interpreted as the username,
    and the corresponding ``UserBusiness`` row is fetched.  Errors raise a
    401 ``HTTPException`` consistent with FastAPI security conventions.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers=_BEARER_CHALLENGE,
        )
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers=_BEARER_CHALLENGE,
        )
    user = get_user(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=_BEARER_CHALLENGE,
        )
    return user
