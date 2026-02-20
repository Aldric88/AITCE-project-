from bson import ObjectId
from fastapi import APIRouter, HTTPException
import time
import logging

from app.database import purchases_collection, notes_collection
from app.utils.cache import cache_get_json, cache_set_json

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.get("/also-bought/{note_id}")
def also_bought(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    cache_key = f"recommendations:also-bought:{note_id}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    started = time.time()
    # users who bought this note
    buyers = purchases_collection.find({
        "note_id": ObjectId(note_id),
        "status": "success"
    })

    buyer_ids = [b.get("buyer_id") or b.get("user_id") for b in buyers]
    buyer_ids = [b for b in buyer_ids if b]
    if not buyer_ids:
        return []

    # other purchases by those users
    other = purchases_collection.find({
        "$or": [
            {"buyer_id": {"$in": buyer_ids}},
            {"user_id": {"$in": buyer_ids}},
        ],
        "note_id": {"$ne": ObjectId(note_id)},
        "status": "success"
    })

    freq = {}
    for p in other:
        nid = str(p["note_id"])
        freq[nid] = freq.get(nid, 0) + 1

    # sort top recommendations
    top_note_ids = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:10]

    results = []
    for nid in top_note_ids:
        n = notes_collection.find_one({"_id": ObjectId(nid), "status": "approved"})
        if n:
            results.append({
                "id": str(n["_id"]),
                "title": n.get("title"),
                "subject": n.get("subject"),
                "dept": n.get("dept"),
                "semester": n.get("semester"),
                "unit": n.get("unit"),
                "is_paid": n.get("is_paid", False),
                "price": n.get("price", 0),
                "ai_summary": (n.get("ai") or {}).get("summary", "")
            })

    cache_set_json(cache_key, results, ttl=120)
    logger.info("db_profile name=also_bought elapsed_ms=%s rows=%s", int((time.time() - started) * 1000), len(results))
    return results
