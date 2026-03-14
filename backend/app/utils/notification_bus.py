import os
import threading

# ── Redis pub/sub (multi-worker) ─────────────────────────────────────────────
try:
    import redis as _redis_lib

    _redis_client = _redis_lib.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    _redis_client.ping()
    _REDIS_OK = True
except Exception:
    _redis_client = None
    _REDIS_OK = False

# ── threading fallback (single-process / no Redis) ───────────────────────────
_EVENTS: dict[str, threading.Event] = {}
_LOCK = threading.Lock()


def _event_for(user_id: str) -> threading.Event:
    with _LOCK:
        evt = _EVENTS.get(user_id)
        if evt is None:
            evt = threading.Event()
            _EVENTS[user_id] = evt
        return evt


def _channel(user_id: str) -> str:
    return f"notif:{user_id}"


def publish_notification(user_id: str) -> None:
    if _REDIS_OK:
        try:
            _redis_client.publish(_channel(user_id), "1")
            return
        except Exception:
            pass
    _event_for(user_id).set()


def wait_for_notification(user_id: str, timeout_seconds: int = 20) -> bool:
    if _REDIS_OK:
        try:
            ps = _redis_client.pubsub()
            ps.subscribe(_channel(user_id))
            try:
                remaining = float(timeout_seconds)
                while remaining > 0:
                    step = min(1.0, remaining)
                    msg = ps.get_message(ignore_subscribe_messages=True, timeout=step)
                    if msg and msg.get("type") == "message":
                        return True
                    remaining -= step
                return False
            finally:
                ps.unsubscribe()
                ps.close()
        except Exception:
            pass
    # threading fallback
    evt = _event_for(user_id)
    changed = evt.wait(timeout_seconds)
    if changed:
        evt.clear()
    return changed
