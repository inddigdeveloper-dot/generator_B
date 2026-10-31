"""
Public review rate limiter — 3 generation actions per 7 minutes per visitor and profile.

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


def _redis_check(identity: str, request_id: str | None = None) -> tuple[bool, int]:
    r   = _redis_client()
    identity_hash = hashlib.sha1(identity.encode()).hexdigest()
    key = f"rl:pub:{identity_hash}"
    now = time.time()

    request_key = None
    if request_id:
        request_hash = hashlib.sha1(request_id.encode()).hexdigest()
        request_key = f"rl:pub:req:{identity_hash}:{request_hash}"
        if r.exists(request_key):
            return True, 0

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
    if request_key:
        pipe.set(request_key, "1", ex=WINDOW_SECONDS + 10)
    pipe.execute()
    return True, 0


# ── In-process fallback ────────────────────────────────────────────────────────

_store: dict[str, list[float]] = defaultdict(list)
_seen_requests: dict[str, float] = {}
_lock  = Lock()


def _memory_check(identity: str, request_id: str | None = None) -> tuple[bool, int]:
    now = time.time()
    with _lock:
        expired_ids = [key for key, expires_at in _seen_requests.items() if expires_at <= now]
        for key in expired_ids:
            _seen_requests.pop(key, None)

        request_key = f"{identity}|{request_id}" if request_id else None
        if request_key and request_key in _seen_requests:
            return True, 0

        hits = [t for t in _store[identity] if now - t < WINDOW_SECONDS]
        _store[identity] = hits
        if len(hits) >= MAX_REQUESTS:
            retry_after = int(WINDOW_SECONDS - (now - hits[0]))
            return False, max(retry_after, 1)
        _store[identity].append(now)
        if request_key:
            _seen_requests[request_key] = now + WINDOW_SECONDS + 10
        return True, 0


# ── Public interface ──────────────────────────────────────────────────────────

def check(identity: str, request_id: str | None = None) -> tuple[bool, int]:
    """Return allowance and retry delay; retries with one request ID count once."""
    r = _redis_client()
    if r:
        try:
            return _redis_check(identity, request_id)
        except Exception as e:
            logger.warning("Redis rate-limit error: %s — falling back to in-process", e)
    return _memory_check(identity, request_id)


def reset_for_tests() -> None:
    with _lock:
        _store.clear()
        _seen_requests.clear()
