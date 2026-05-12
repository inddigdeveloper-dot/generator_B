from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core import rate_limit, review_cache
from app.db.database import get_db
from app.db.models import GeneratedReview, UserBusiness
from app.schemas.public_review import (
    PublicBusinessInfo,
    PublicGenerateRequest,
    PublicGenerateResponse,
)
from app.services import review as review_service

router = APIRouter()


def _google_review_url(biz: UserBusiness) -> str:
    if biz.google_place_id:
        return f"https://search.google.com/local/writereview?placeid={biz.google_place_id}"
    return biz.review_link or ""


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Real-IP")
    return forwarded if forwarded else (request.client.host if request.client else "unknown")


@router.get("/{username}", response_model=PublicBusinessInfo)
def get_business_info(username: str, db: Session = Depends(get_db)):
    biz = db.query(UserBusiness).filter(UserBusiness.user_name == username).first()
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return PublicBusinessInfo(business_name=biz.business_name, business_desc=biz.business_desc)


@router.post("/{username}/generate", response_model=PublicGenerateResponse)
def generate_public_review(
    request: Request,
    username: str,
    payload: PublicGenerateRequest,
    db: Session = Depends(get_db),
):
    # ── Rate limiting (pure Python, 3 requests per 7 minutes per IP) ──────────
    ip = _client_ip(request)
    allowed, retry_after = rate_limit.check(ip)
    if not allowed:
        mins = (retry_after + 59) // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please wait {mins} minute{'s' if mins != 1 else ''} before generating again.",
        )

    biz = db.query(UserBusiness).filter(UserBusiness.user_name == username).first()
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    google_url = _google_review_url(biz)
    if not google_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This business hasn't configured a Google review link yet.",
        )

    # ── Cache check (pure Python, 20-minute TTL) ───────────────────────────────
    cached = review_cache.get(username, payload.rating, payload.experience)
    if cached:
        return PublicGenerateResponse(reviews=cached, google_review_url=google_url)

    # ── Generate 5 variants in parallel ───────────────────────────────────────
    try:
        reviews = review_service.generate_review_variants(
            business=biz,
            rating=payload.rating,
            customer_name="A customer",
            experience=payload.experience,
            count=5,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review generation is temporarily unavailable. Please try again shortly.",
        )

    # ── Cache results ──────────────────────────────────────────────────────────
    review_cache.put(username, payload.rating, payload.experience, reviews)

    # ── Persist all variants ───────────────────────────────────────────────────
    for text in reviews:
        db.add(GeneratedReview(
            user_id=biz.id,
            customer_name="Public",
            rating=payload.rating,
            review_text=text,
        ))
    db.commit()

    return PublicGenerateResponse(reviews=reviews, google_review_url=google_url)
