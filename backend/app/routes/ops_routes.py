import os
import time

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import client
from app.services.ai_pipeline import get_ai_queue_stats
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/ops", tags=["Ops"])


@router.get("/health")
def ops_health():
    db_ok = True
    try:
        client.admin.command("ping")
    except Exception:
        db_ok = False
    queue = get_ai_queue_stats()
    return {
        "status": "ok" if db_ok else "degraded",
        "time": int(time.time()),
        "db_ok": db_ok,
        "ai_queue": queue,
    }


@router.get("/runtime")
def ops_runtime(current_user=Depends(get_current_user)):
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    return {
        "status": "ok",
        "app_env": settings.APP_ENV,
        "security_headers": settings.ENABLE_SECURITY_HEADERS,
        "slow_query_threshold_ms": settings.SLOW_QUERY_THRESHOLD_MS,
        "moderation_mode": os.getenv("MODERATION_AI_MODE", "rules"),
        "uses_paid_ai_api": False,
    }
