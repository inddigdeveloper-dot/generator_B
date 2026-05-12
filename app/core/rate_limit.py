"""
Public review rate limiter — 3 requests per 7 minutes per IP.

Uses Redis when REDIS_URL is set (shared across workers, survives restarts).
Falls back to an in-process store when Redis is unavailable.
"""
import hashlib
import json
import logging
import time
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 7 * 60
MAX_REQUESTS   = 3

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
            logger.info("rate_limit: using Redis backend")
        else:
            logger.info("rate_limit: Redis unavailable — using in-process store")
    return _redis


def _redis_check(ip: str) -> tuple[bool, int]:
    r   = _redis_client()
    key = f"rl:pub:{hashlib.sha1(ip.encode()).hexdigest()}"
    now = time.time()

    pipe = r.pipeline()
    pipe.lrange(key, 0, -1)
    results = pipe.execute()
    raw_hits: list[bytes] = results[0]

    hits = [float(h) for h in raw_hits if now - float(h) < WINDOW_SECONDS]

    if len(hits) >= MAX_REQUESTS:
        retry_after = int(WINDOW_SECONDS - (now - hits[0]))
        return False, max(retry_after, 1)

    pipe = r.pipeline()
    pipe.delete(key)
    for h in hits:
        pipe.rpush(key, h)
    pipe.rpush(key, now)
    pipe.expire(key, WINDOW_SECONDS + 10)
    pipe.execute()
    return True, 0


# ── In-process fallback ────────────────────────────────────────────────────────

_store: dict[str, list[float]] = defaultdict(list)
_lock  = Lock()


def _memory_check(ip: str) -> tuple[bool, int]:
    now = time.time()
    with _lock:
        hits = [t for t in _store[ip] if now - t < WINDOW_SECONDS]
        _store[ip] = hits
        if len(hits) >= MAX_REQUESTS:
            retry_after = int(WINDOW_SECONDS - (now - hits[0]))
            return False, max(retry_after, 1)
        _store[ip].append(now)
        return True, 0


# ── Public interface ──────────────────────────────────────────────────────────

def check(ip: str) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Records the hit when allowed."""
    r = _redis_client()
    if r:
        try:
            return _redis_check(ip)
        except Exception as e:
            logger.warning("Redis rate-limit error: %s — falling back to in-process", e)
    return _memory_check(ip)
