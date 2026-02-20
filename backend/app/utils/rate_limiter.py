import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None


class RedisSlidingWindowLimiter:
    def __init__(self, redis_client, requests_limit: int, time_window: int, key_prefix: str):
        self.redis_client = redis_client
        self.requests_limit = requests_limit
        self.time_window = time_window
        self.key_prefix = key_prefix

    def _client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def __call__(self, request: Request):
        identifier = self._client_ip(request)
        key = f"{self.key_prefix}:{identifier}"
        now_ms = int(time.time() * 1000)
        window_start = now_ms - self.time_window * 1000

        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        member = f"{now_ms}:{time.time_ns()}"
        pipe.zadd(key, {member: now_ms})
        pipe.expire(key, self.time_window + 5)
        _, count, _, _ = pipe.execute()

        if int(count) >= self.requests_limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )


class InMemoryLimiter:
    def __init__(self, requests_limit: int, time_window: int):
        self.requests_limit = requests_limit
        self.time_window = time_window
        self.clients = defaultdict(list)

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        self.clients[client_ip] = [
            t for t in self.clients[client_ip] if current_time - t < self.time_window
        ]

        if len(self.clients[client_ip]) >= self.requests_limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )

        self.clients[client_ip].append(current_time)


def _build_redis_client() -> Optional["Redis"]:
    if Redis is None:
        return None
    try:
        client = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=0.2)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory limiter fallback: %s", exc)
        return None


_redis_client = _build_redis_client()


def _build_limiter(requests_limit: int, time_window: int, key_prefix: str):
    if _redis_client is not None:
        return RedisSlidingWindowLimiter(_redis_client, requests_limit, time_window, key_prefix)
    return InMemoryLimiter(requests_limit, time_window)


# Login: 5 attempts per minute
login_limiter = _build_limiter(requests_limit=5, time_window=60, key_prefix="rl:login")

# Search: 20 requests per minute
search_limiter = _build_limiter(requests_limit=20, time_window=60, key_prefix="rl:search")


user_request_history = defaultdict(list)


def check_rate_limit(user_id: str, limit: int = 50, window: int = 60) -> bool:
    if _redis_client is not None:
        key = f"rl:user:{user_id}"
        now_ms = int(time.time() * 1000)
        window_start = now_ms - window * 1000
        member = f"{now_ms}:{time.time_ns()}"
        pipe = _redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {member: now_ms})
        pipe.expire(key, window + 5)
        _, count, _, _ = pipe.execute()
        return int(count) < limit

    current_time = time.time()

    user_request_history[user_id] = [
        t for t in user_request_history[user_id] if current_time - t < window
    ]

    if len(user_request_history[user_id]) >= limit:
        return False

    user_request_history[user_id].append(current_time)
    return True
