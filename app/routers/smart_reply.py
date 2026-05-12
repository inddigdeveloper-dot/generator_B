from fastapi import APIRouter, Depends, Request

from app.core.limiter import limiter
from app.db.models import UserBusiness
from app.schemas.smart_reply import SmartReplyRequest, SmartReplyResponse
from app.services import smart_reply as smart_reply_service
from app.services.auth import get_current_user

router = APIRouter()


@router.post("/generate", response_model=SmartReplyResponse)
@limiter.limit("5/minute")
def generate_reply(
    request: Request,
    payload: SmartReplyRequest,
    current_user: UserBusiness = Depends(get_current_user),
):
    reply = smart_reply_service.generate_smart_reply(
        review_text=payload.review_text,
        business_name=current_user.business_name,
        tone=payload.tone,
        language=payload.language,
    )
    return SmartReplyResponse(reply=reply)
