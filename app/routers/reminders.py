from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.db.database import get_db
from app.services.qr_reminder import send_inactive_qr_reminders

router = APIRouter()


@router.post("/qr-inactive/run")
def run_qr_inactive_reminders(
    dry_run: bool = Query(True),
    limit: int = Query(500, ge=1, le=500),
    x_reminder_token: str | None = Header(default=None, alias="X-Reminder-Token"),
    db: Session = Depends(get_db),
):
    if not settings.reminder_job_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reminder job token is not configured.",
        )
    if x_reminder_token != settings.reminder_job_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    result = send_inactive_qr_reminders(db, dry_run=dry_run, limit=limit)
    return {
        "dry_run": dry_run,
        "checked": result.checked,
        "eligible": result.eligible,
        "sent": result.sent,
        "skipped": result.skipped,
        "errors": result.errors,
    }
