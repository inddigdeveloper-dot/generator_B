from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import JobLock, UserBusiness
from app.services.aisensy import send_qr_inactive_reminder

REMINDER_INTERVAL = timedelta(days=7)
REMINDER_JOB_NAME = "qr_inactive_reminder"
RUN_TIMEZONE = ZoneInfo("Asia/Kolkata")


@dataclass
class ReminderRunResult:
    checked: int = 0
    eligible: int = 0
    sent: int = 0
    skipped: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def latest_datetime(*values: datetime | None) -> datetime | None:
    aware_values = [ensure_aware(value) for value in values if value is not None]
    return max(aware_values) if aware_values else None


def record_qr_scan(business: UserBusiness, db: Session) -> None:
    now = utc_now()
    if business.qr_tracking_started_at is None:
        business.qr_tracking_started_at = now
    business.last_qr_scan_at = now
    db.commit()


def is_reminder_due(business: UserBusiness, now: datetime | None = None) -> bool:
    now = now or utc_now()
    activity_at = latest_datetime(
        business.last_qr_scan_at,
        business.qr_tracking_started_at,
        business.created_at,
    )
    if activity_at is None or now - activity_at < REMINDER_INTERVAL:
        return False

    last_sent_at = ensure_aware(business.last_qr_reminder_sent_at)
    if last_sent_at and now - last_sent_at < REMINDER_INTERVAL:
        return False

    return True


def send_inactive_qr_reminders(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int = 100,
) -> ReminderRunResult:
    result = ReminderRunResult()
    now = utc_now()
    businesses = (
        db.query(UserBusiness)
        .filter(UserBusiness.mobile_no != "")
        .order_by(UserBusiness.id.asc())
        .limit(limit)
        .all()
    )

    for business in businesses:
        result.checked += 1
        if not business.qr_tracking_started_at:
            business.qr_tracking_started_at = now

        if not is_reminder_due(business, now):
            result.skipped += 1
            continue

        result.eligible += 1
        if dry_run:
            result.skipped += 1
            continue

        ok, message = send_qr_inactive_reminder(business)
        if ok:
            business.last_qr_reminder_sent_at = now
            result.sent += 1
        else:
            result.errors.append({"business": business.user_name, "error": message})

    db.commit()
    return result


def _local_run_date(value: datetime) -> object:
    return ensure_aware(value).astimezone(RUN_TIMEZONE).date()


def claim_daily_reminder_run(db: Session, now: datetime | None = None) -> bool:
    now = now or utc_now()

    try:
        if db.get(JobLock, REMINDER_JOB_NAME) is None:
            db.add(JobLock(job_name=REMINDER_JOB_NAME))
            db.commit()
    except IntegrityError:
        db.rollback()

    lock = (
        db.query(JobLock)
        .filter(JobLock.job_name == REMINDER_JOB_NAME)
        .with_for_update()
        .one()
    )
    last_run_at = ensure_aware(lock.last_run_at)
    if last_run_at and _local_run_date(last_run_at) == _local_run_date(now):
        db.rollback()
        return False

    lock.last_run_at = now
    db.commit()
    return True


def run_scheduled_qr_inactive_reminders(limit: int = 500) -> ReminderRunResult | None:
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        if not claim_daily_reminder_run(db):
            return None
        return send_inactive_qr_reminders(db, dry_run=False, limit=limit)
    finally:
        db.close()
