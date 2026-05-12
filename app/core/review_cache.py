"""
Review variant cache — 20-minute TTL, keyed by (username, rating, experience).

Uses Redis when REDIS_URL is set. Falls back to an in-process dict.
"""
import hashlib
import json
import logging
import time
from threading import Lock

logger = logging.getLogger(__name__)

TTL = 20 * 60  # 20 minutes

# ── Redis backend ─────────────────────────────────────────────────────────────

def _get_redis():
    try:
        from app.core.settings import settings
        url = getattr(settings, "redis_url", None)
        if not url:
            return None
        import redis
        r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


_redis = None
_redis_checked = False


def _redis_client():
    global _redis, _redis_checked
    if not _redis_checked:
        _redis = _get_redis()
        _redis_checked = True
        if _redis:
            logger.info("review_cache: using Redis backend")
        else:
            logger.info("review_cache: Redis unavailable — using in-process cache")
    return _redis


def _cache_key(username: str, rating: int, experience: str | None) -> str:
    raw = f"{username}|{rating}|{experience or ''}".encode()
    return f"rc:{hashlib.sha1(raw).hexdigest()}"


# ── In-process fallback ───────────────────────────────────────────────────────

_cache: dict[str, tuple[float, list[str]]] = {}
_lock  = Lock()

# ── Public interface ──────────────────────────────────────────────────────────

def get(username: str, rating: int, experience: str | None) -> list[str] | None:
    r = _redis_client()
    k = _cache_key(username, rating, experience)

    if r:
        try:
            raw = r.get(k)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning("Redis cache get error: %s", e)

    with _lock:
        entry = _cache.get(k)
        if entry and time.time() - entry[0] < TTL:
            return entry[1]
        _cache.pop(k, None)
        return None


def put(username: str, rating: int, experience: str | None, reviews: list[str]) -> None:
    r = _redis_client()
    k = _cache_key(username, rating, experience)

    if r:
        try:
            r.setex(k, TTL, json.dumps(reviews))
            return
        except Exception as e:
            logger.warning("Redis cache put error: %s", e)

    with _lock:
        _cache[k] = (time.time(), reviews)
