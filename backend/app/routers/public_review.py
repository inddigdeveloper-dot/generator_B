from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
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


@router.get("/{username}", response_model=PublicBusinessInfo)
def get_business_info(username: str, db: Session = Depends(get_db)):
    biz = (
        db.query(UserBusiness)
        .filter(UserBusiness.user_name == username)
        .first()
    )
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return PublicBusinessInfo(
        business_name=biz.business_name,
        business_desc=biz.business_desc,
    )


@router.post("/{username}/generate", response_model=PublicGenerateResponse)
@limiter.limit("10/minute")
def generate_public_review(
    request: Request,
    username: str,
    payload: PublicGenerateRequest,
    db: Session = Depends(get_db),
):
    biz = (
        db.query(UserBusiness)
        .filter(UserBusiness.user_name == username)
        .first()
    )
    if not biz:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    google_url = _google_review_url(biz)
    if not google_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This business hasn't configured a Google review link yet.",
        )

    try:
        text = review_service.generate_review_text(
            business=biz,
            rating=payload.rating,
            customer_name="A customer",
            experience=payload.experience,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review generation is temporarily unavailable. Please try again shortly.",
        )

    db.add(
        GeneratedReview(
            user_id=biz.id,
            customer_name="Public",
            rating=payload.rating,
            review_text=text,
        )
    )
    db.commit()

    return PublicGenerateResponse(review_text=text, google_review_url=google_url)