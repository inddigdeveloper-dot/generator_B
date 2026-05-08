from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.settings import settings


def _real_ip(request) -> str:
    # Respect X-Real-IP set by nginx; fall back to direct client address.
    forwarded = request.headers.get("X-Real-IP")
    return forwarded if forwarded else get_remote_address(request)


# Use Redis storage in production so limits are shared across workers.
# Falls back to in-memory if REDIS_URL is not set (dev only).
_storage_uri = getattr(settings, "redis_url", None)

if _storage_uri:
    limiter = Limiter(key_func=_real_ip, storage_uri=_storage_uri)
else:
    limiter = Limiter(key_func=_real_ip)
