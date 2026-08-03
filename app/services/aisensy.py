import json
import logging
import re
from urllib import error, request

from app.core.settings import settings
from app.db.models import UserBusiness

logger = logging.getLogger(__name__)

AISENSY_API_URL = "https://backend.aisensy.com/campaign/t1/api/v2"


def normalize_whatsapp_number(raw_number: str) -> str:
    digits = re.sub(r"\D+", "", raw_number or "")
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def send_qr_inactive_reminder(business: UserBusiness) -> tuple[bool, str]:
    if not settings.aisensy_api_key or not settings.aisensy_campaign_name:
        return False, "AiSensy config missing"

    destination = normalize_whatsapp_number(business.mobile_no)
    if len(destination) < 11:
        return False, "Invalid mobile number"

    display_name = business.name or business.business_name
    payload = {
        "apiKey": settings.aisensy_api_key,
        "campaignName": settings.aisensy_campaign_name,
        "destination": destination,
        "userName": display_name,
        "source": settings.aisensy_source,
        "templateParams": [display_name, business.business_name],
    }

    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        AISENSY_API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if 200 <= resp.status < 300:
                return True, body
            return False, f"AiSensy returned HTTP {resp.status}: {body}"
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning("AiSensy reminder failed for business %s: %s", business.id, body)
        return False, f"AiSensy returned HTTP {exc.code}: {body}"
    except Exception as exc:
        logger.warning("AiSensy reminder failed for business %s: %s", business.id, exc)
        return False, str(exc)
