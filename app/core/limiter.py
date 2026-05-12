import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _real_ip(request) -> str:
    forwarded = request.headers.get("X-Real-IP")
    return forwarded if forwarded else get_remote_address(request)


def _make_limiter() -> Limiter:
    """Return a Limiter backed by Redis if REDIS_URL is configured, otherwise in-memory."""
    try:
        from app.core.settings import settings
        redis_url = getattr(settings, "redis_url", None)
        if redis_url:
            import redis as _redis_lib
            _redis_lib.from_url(redis_url, socket_connect_timeout=2).ping()
            logger.info("slowapi limiter: using Redis backend (%s)", redis_url)
            return Limiter(key_func=_real_ip, storage_uri=redis_url)
    except Exception as e:
        logger.warning("slowapi limiter: Redis unavailable (%s) — using in-memory", e)
    return Limiter(key_func=_real_ip)


limiter = _make_limiter()
