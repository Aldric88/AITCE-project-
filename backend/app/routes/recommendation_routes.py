from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
import time
import logging
import re

from app.database import purchases_collection, notes_collection, follows_collection
from app.utils.cache import cache_get_json, cache_set_json
from app.utils.dependencies import get_optional_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


@router.get("/also-bought/{note_id}")
def also_bought(note_id: str, current_user=Depends(get_optional_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    cache_scope = current_user["id"] if current_user else "public"
    cache_key = f"recommendations:also-bought:{note_id}:{cache_scope}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    started = time.time()
    base_note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not base_note:
        raise HTTPException(status_code=404, detail="Note not found")
    base_text = " ".join(
        [
            str(base_note.get("title", "")),
            str(base_note.get("description", "")),
            str(base_note.get("subject", "")),
            " ".join([str(t) for t in base_note.get("tags", [])]),
        ]
    )
    base_tokens = _tokens(base_text)

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

    candidate_ids = {ObjectId(nid) for nid in freq.keys() if ObjectId.is_valid(nid)}
    fallback_rows = notes_collection.find(
        {
            "_id": {"$ne": ObjectId(note_id)},
            "status": "approved",
            "$or": [
                {"subject": base_note.get("subject")},
                {"dept": base_note.get("dept")},
                {"tags": {"$in": base_note.get("tags", [])}},
            ],
        },
        {"_id": 1},
    ).limit(80)
    for row in fallback_rows:
        candidate_ids.add(row["_id"])

    following_ids = set()
    if current_user:
        rows = follows_collection.find(
            {"follower_id": ObjectId(current_user["id"])},
            {"following_id": 1},
        ).limit(500)
        following_ids = {r.get("following_id") for r in rows if r.get("following_id")}

    results = []
    for candidate in notes_collection.find(
        {
            "_id": {"$in": list(candidate_ids)} if candidate_ids else {"$exists": False},
            "status": "approved",
        }
    ).limit(200):
        text = " ".join(
            [
                str(candidate.get("title", "")),
                str(candidate.get("description", "")),
                str(candidate.get("subject", "")),
                " ".join([str(t) for t in candidate.get("tags", [])]),
            ]
        )
        toks = _tokens(text)
        semantic = (len(base_tokens.intersection(toks)) / max(len(base_tokens.union(toks)), 1)) if base_tokens and toks else 0.0
        co_purchase = freq.get(str(candidate["_id"]), 0)
        subject_bonus = 1.5 if candidate.get("subject") == base_note.get("subject") else 0.0
        dept_bonus = 0.8 if candidate.get("dept") == base_note.get("dept") else 0.0
        follow_bonus = 2.2 if candidate.get("uploader_id") in following_ids else 0.0
        score = round(min(100.0, (co_purchase * 8.0) + (semantic * 35.0) + subject_bonus + dept_bonus + follow_bonus), 3)

        results.append(
            {
                "id": str(candidate["_id"]),
                "title": candidate.get("title"),
                "subject": candidate.get("subject"),
                "dept": candidate.get("dept"),
                "semester": candidate.get("semester"),
                "unit": candidate.get("unit"),
                "is_paid": candidate.get("is_paid", False),
                "price": candidate.get("price", 0),
                "ai_summary": (candidate.get("ai") or {}).get("summary", ""),
                "score": score,
                "reason": "Creator you follow" if follow_bonus > 0 else "Similar buyers and content",
            }
        )
    results.sort(key=lambda r: r.get("score", 0), reverse=True)
    results = results[:10]

    cache_set_json(cache_key, results, ttl=120)
    logger.info("db_profile name=also_bought elapsed_ms=%s rows=%s", int((time.time() - started) * 1000), len(results))
    return results
