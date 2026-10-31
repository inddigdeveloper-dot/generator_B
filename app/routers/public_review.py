from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.db.database import get_db
from app.db.models import GeneratedReview, UserBusiness
from app.schemas.public_review import (
    PublicBusinessInfo,
    PublicGenerateRequest,
    PublicGenerateResponse,
)
from app.services.keywords import normalize_business_keywords
from app.services.qr_reminder import record_qr_scan
from app.services import review as review_service

router = APIRouter()


def _google_review_url(biz: UserBusiness) -> str:
    if biz.google_place_id:
        return f"https://search.google.com/local/writereview?placeid={biz.google_place_id}"
    return biz.review_link or ""


def _client_identity(request: Request, username: str) -> str:
    visitor_id = request.headers.get("X-Review-Visitor", "").strip()
    if visitor_id and 8 <= len(visitor_id) <= 100:
        return f"{username}|visitor:{visitor_id}"

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    forwarded_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else ""
    real_ip = request.headers.get("X-Real-IP", "").strip()
    client_ip = request.client.host if request.client else "unknown"
    return f"{username}|ip:{forwarded_ip or real_ip or client_ip}"


@router.get("/{username}", response_model=PublicBusinessInfo)
def get_business_info(username: str, db: Session = Depends(get_db)):
    biz = db.query(UserBusiness).filter(UserBusiness.user_name == username).first()
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    record_qr_scan(biz, db)
    return PublicBusinessInfo(business_name=biz.business_name, business_desc=biz.business_desc)


@router.post("/{username}/generate", response_model=PublicGenerateResponse)
def generate_public_review(
    request: Request,
    username: str,
    payload: PublicGenerateRequest,
    db: Session = Depends(get_db),
):
    # Three generation actions per visitor/profile; network retries count once.
    identity = _client_identity(request, username)
    request_id = request.headers.get("X-Review-Request-ID", "").strip() or None
    allowed, retry_after = rate_limit.check(identity, request_id)
    if not allowed:
        mins = (retry_after + 59) // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please wait {mins} minute{'s' if mins != 1 else ''} before generating again.",
        )

    biz = db.query(UserBusiness).filter(UserBusiness.user_name == username).first()
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    normalize_business_keywords(biz, db)

    google_url = _google_review_url(biz)
    if not google_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This business hasn't configured a Google review link yet.",
        )

    previous_reviews = [
        row[0]
        for row in (
            db.query(GeneratedReview.review_text)
            .filter(GeneratedReview.user_id == biz.id)
            .order_by(GeneratedReview.created_at.desc())
            .all()
        )
    ]

    # ── Generate 5 variants in parallel ───────────────────────────────────────
    reviews = review_service.generate_review_variants(
        business=biz,
        rating=payload.rating,
        customer_name="A customer",
        experience=payload.experience,
        count=5,
        excluded_reviews=previous_reviews,
    )

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
