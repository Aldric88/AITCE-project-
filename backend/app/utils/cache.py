import json
import logging
import time
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None


_redis = None
if Redis is not None:
    try:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=0.2)
        _redis.ping()
    except Exception as exc:  # pragma: no cover
        logger.warning("Cache Redis unavailable; falling back to in-memory cache: %s", exc)
        _redis = None

_in_memory: dict[str, tuple[float, str]] = {}


def cache_get_json(key: str) -> Optional[Any]:
    if _redis is not None:
        raw = _redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    value = _in_memory.get(key)
    if not value:
        return None
    expires_at, raw = value
    if time.time() >= expires_at:
        _in_memory.pop(key, None)
        return None
    return json.loads(raw)


def cache_set_json(key: str, data: Any, ttl: int = settings.CACHE_DEFAULT_TTL_SECONDS):
    raw = json.dumps(data, ensure_ascii=True)
    if _redis is not None:
        _redis.setex(key, ttl, raw)
        return
    _in_memory[key] = (time.time() + ttl, raw)


def cache_delete(key: str):
    if _redis is not None:
        _redis.delete(key)
        return
    _in_memory.pop(key, None)


def cache_delete_prefix(prefix: str):
    if _redis is not None:
        cursor = 0
        pattern = f"{prefix}*"
        while True:
            cursor, keys = _redis.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                _redis.delete(*keys)
            if cursor == 0:
                break
        return
    keys = [k for k in _in_memory.keys() if k.startswith(prefix)]
    for key in keys:
        _in_memory.pop(key, None)
