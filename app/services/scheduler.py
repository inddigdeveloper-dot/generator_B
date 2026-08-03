import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.settings import settings
from app.services.qr_reminder import run_scheduled_qr_inactive_reminders

logger = logging.getLogger(__name__)
RUN_TIMEZONE = ZoneInfo("Asia/Kolkata")


def seconds_until_next_reminder_run(now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(RUN_TIMEZONE)
    run_at = local_now.replace(
        hour=settings.qr_reminder_run_hour_ist,
        minute=settings.qr_reminder_run_minute_ist,
        second=0,
        microsecond=0,
    )
    if local_now >= run_at:
        run_at += timedelta(days=1)
    return max(1.0, (run_at.astimezone(timezone.utc) - now).total_seconds())


async def qr_inactive_reminder_scheduler() -> None:
    logger.info(
        "QR reminder scheduler enabled for %02d:%02d IST",
        settings.qr_reminder_run_hour_ist,
        settings.qr_reminder_run_minute_ist,
    )
    while True:
        delay = seconds_until_next_reminder_run()
        logger.info("Next QR reminder check in %.0f seconds", delay)
        await asyncio.sleep(delay)

        try:
            result = await asyncio.to_thread(run_scheduled_qr_inactive_reminders)
            if result is None:
                logger.info("QR reminder check skipped; already ran today")
            else:
                logger.info(
                    "QR reminder check complete: checked=%s eligible=%s sent=%s errors=%s",
                    result.checked,
                    result.eligible,
                    result.sent,
                    len(result.errors),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("QR reminder scheduler run failed")
