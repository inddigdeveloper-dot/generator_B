from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import GeneratedReview, UserBusiness
from app.schemas.review import ReviewGenerateRequest, ReviewListResponse, ReviewOut
from app.services import review as review_service
from app.services.auth import get_current_user
from app.services.qr import generate_qr

router = APIRouter()


def _review_url(place_id: str) -> str:
    return f"https://search.google.com/local/writereview?placeid={place_id}"


@router.post("/generate", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def generate(
    payload: ReviewGenerateRequest,
    db: Session = Depends(get_db),
    current_user: UserBusiness = Depends(get_current_user),
):
    if not current_user.google_place_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business profile is missing a Google Place ID. Update your profile first.",
        )
    from app.core.settings import settings as _settings
    provider = _settings.llm_provider.lower()
    if provider == "gemini" and not _settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review generation is not configured. Set GEMINI_API_KEY or switch LLM_PROVIDER in .env.",
        )
    if provider == "ollama" and not _settings.ollama_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama provider selected but OLLAMA_BASE_URL is not set in .env.",
        )

    text = review_service.generate_review_text(
        business=current_user,
        rating=payload.rating,
        customer_name=payload.customer_name,
        experience=payload.experience,
    )

    review = GeneratedReview(
        user_id=current_user.id,
        customer_name=payload.customer_name,
        rating=payload.rating,
        review_text=text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return ReviewOut(
        id=review.id,
        customer_name=review.customer_name,
        rating=review.rating,
        review_text=review.review_text,
        google_review_url=_review_url(current_user.google_place_id),
        created_at=review.created_at,
    )


@router.get("/history", response_model=ReviewListResponse)
def history(
    db: Session = Depends(get_db),
    current_user: UserBusiness = Depends(get_current_user),
):
    rows = (
        db.query(GeneratedReview)
        .filter(GeneratedReview.user_id == current_user.id)
        .order_by(GeneratedReview.created_at.desc())
        .all()
    )
    place_id = current_user.google_place_id or ""
    items = [
        ReviewOut(
            id=r.id,
            customer_name=r.customer_name,
            rating=r.rating,
            review_text=r.review_text,
            google_review_url=_review_url(place_id) if place_id else "",
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ReviewListResponse(reviews=items, total=len(items))


@router.post("/qr", status_code=status.HTTP_200_OK)
def get_or_create_qr(
    db: Session = Depends(get_db),
    current_user: UserBusiness = Depends(get_current_user),
):
    from app.core.settings import settings as _settings

    if not current_user.google_place_id and not current_user.review_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No review link set on your profile.",
        )
    # QR points to the customer review page, not the raw Google link
    review_page_url = f"{_settings.frontend_url}/r/{current_user.user_name}"
    path = generate_qr(review_page_url, current_user.id)
    current_user.qr_code_url = f"/{path}"
    db.commit()
    db.refresh(current_user)
    return {"qr_code_url": current_user.qr_code_url}


