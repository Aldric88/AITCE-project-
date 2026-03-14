import time
import logging
from collections import defaultdict
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import (
    follows_collection,
    users_collection,
    notes_collection,
    purchases_collection,
    likes_collection,
    bookmarks_collection,
)
from app.models.note_model import note_helper
from app.utils.dependencies import get_current_user
from app.utils.notify import notify
from app.utils.cache import cache_get_json, cache_set_json, cache_delete_prefix
from app.utils.observability import log_if_slow
from app.services.feed_pipeline import (
    append_trust_lookups,
    append_trust_fields,
    append_access_fields,
)

router = APIRouter(prefix="/follow", tags=["Follow System"])
logger = logging.getLogger(__name__)


def _cache_prefix_for_user(user_id: str) -> str:
    return f"feed:follow:{user_id}:"


def _invalidate_feed_cache_for_user(user_id: str):
    cache_delete_prefix(_cache_prefix_for_user(user_id))


def _invalidate_feed_cache_for_followers(creator_id: str):
    for edge in follows_collection.find({"following_id": ObjectId(creator_id)}, {"follower_id": 1}):
        _invalidate_feed_cache_for_user(str(edge["follower_id"]))


def _public_user_map(user_ids: list[ObjectId]) -> dict[ObjectId, dict]:
    if not user_ids:
        return {}
    rows = users_collection.find(
        {"_id": {"$in": list(set(user_ids))}},
        {"name": 1, "email": 1, "dept": 1, "year": 1, "section": 1, "profile_pic_url": 1, "verified_seller": 1},
    )
    return {u["_id"]: u for u in rows}


def _base_feed_pipeline(following_ids: list[ObjectId], current_user_id: ObjectId, limit: int):
    pipeline = [
        {"$match": {"uploader_id": {"$in": following_ids}, "status": "approved"}},
        {"$sort": {"created_at": -1, "_id": -1}},
        {"$limit": limit},
    ]
    append_trust_lookups(pipeline, include_college=False)
    append_trust_fields(pipeline, include_college=False)
    append_access_fields(pipeline, current_user_id=current_user_id)
    return pipeline


def _subject_preferences_for_user(user_oid: ObjectId) -> dict[str, float]:
    weights: defaultdict[str, float] = defaultdict(float)
    note_ids: list[ObjectId] = []

    bought = purchases_collection.find(
        {"$or": [{"buyer_id": user_oid}, {"user_id": user_oid}], "status": {"$in": ["success", "paid", "free"]}},
        {"note_id": 1},
    ).limit(120)
    liked = likes_collection.find({"user_id": user_oid}, {"note_id": 1}).limit(120)
    bookmarked = bookmarks_collection.find({"user_id": user_oid}, {"note_id": 1}).limit(120)

    for row in bought:
        if row.get("note_id"):
            note_ids.append(row["note_id"])
    for row in liked:
        if row.get("note_id"):
            note_ids.append(row["note_id"])
    for row in bookmarked:
        if row.get("note_id"):
            note_ids.append(row["note_id"])

    if not note_ids:
        return {}

    for note in notes_collection.find({"_id": {"$in": note_ids}}, {"subject": 1}):
        subject = str(note.get("subject", "")).strip().lower()
        if subject:
            weights[subject] += 1.0

    total = sum(weights.values()) or 1.0
    return {k: v / total for k, v in weights.items()}


def _personalize_feed(items: list[dict], subject_weights: dict[str, float]):
    now = int(time.time())
    personalized = []
    for item in items:
        created_at = int(item.get("created_at") or 0)
        age_hours = max((now - created_at) / 3600.0, 0.0)
        recency_score = max(0.0, 1.0 - min(age_hours / 120.0, 1.0))
        rating_score = min(max(float(item.get("avg_rating", 0)) / 5.0, 0.0), 1.0)
        sales_score = min(float(item.get("seller_total_sales", 0)) / 25.0, 1.0)
        subject_score = subject_weights.get(str(item.get("subject", "")).lower(), 0.0)

        score = round((recency_score * 0.42) + (rating_score * 0.25) + (sales_score * 0.18) + (subject_score * 0.15), 4)

        reason = "Recent from creator you follow"
        if subject_score >= 0.15:
            reason = "Matches your preferred subjects"
        elif rating_score >= 0.8:
            reason = "Highly rated from followed creators"
        elif sales_score >= 0.5:
            reason = "Popular creator in your network"

        item["personalization_score"] = score
        item["personalization_reason"] = reason
        personalized.append(item)
    personalized.sort(key=lambda x: x.get("personalization_score", 0), reverse=True)
    return personalized


@router.post("/{user_id}")
def follow_user(user_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    exists = follows_collection.find_one({
        "follower_id": ObjectId(current_user["id"]),
        "following_id": ObjectId(user_id)
    })

    if exists:
        return {"message": "Already following ✅"}

    follows_collection.insert_one({
        "follower_id": ObjectId(current_user["id"]),
        "following_id": ObjectId(user_id),
        "created_at": int(time.time())
    })
    _invalidate_feed_cache_for_user(current_user["id"])

    # Notify the user being followed
    notify(
        user_id=user_id,
        type="FOLLOW",
        message=f"{current_user['name']} started following you",
        link=f"/creator/{current_user['id']}"
    )

    return {"message": "Followed ✅"}


@router.delete("/{user_id}")
def unfollow_user(user_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    follows_collection.delete_one({
        "follower_id": ObjectId(current_user["id"]),
        "following_id": ObjectId(user_id)
    })
    _invalidate_feed_cache_for_user(current_user["id"])

    return {"message": "Unfollowed ✅"}


@router.get("/me/following")
def my_following(current_user=Depends(get_current_user)):
    following = follows_collection.find({
        "follower_id": ObjectId(current_user["id"])
    })

    ids = [str(f["following_id"]) for f in following]
    return {"following_ids": ids}


@router.get("/stats/{user_id}")
def follow_stats(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    followers = follows_collection.count_documents({"following_id": ObjectId(user_id)})
    following = follows_collection.count_documents({"follower_id": ObjectId(user_id)})

    return {"followers": followers, "following": following}


@router.get("/feed")
def following_feed(
    mode: str = Query(default="personalized", pattern="^(personalized|latest)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=60),
    current_user=Depends(get_current_user),
):
    current_user_id = ObjectId(current_user["id"])
    cache_key = f"{_cache_prefix_for_user(current_user['id'])}{mode}:{skip}:{limit}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    following_ids = [row["following_id"] for row in follows_collection.find({"follower_id": current_user_id}, {"following_id": 1})]
    if not following_ids:
        return []

    started = time.time()
    pipeline = _base_feed_pipeline(following_ids=following_ids, current_user_id=current_user_id, limit=max(limit + skip, 80))
    feed_docs = list(notes_collection.aggregate(pipeline))
    log_if_slow(
        logger,
        "follow.feed.aggregate",
        started,
        mode=mode,
        rows=len(feed_docs),
        skip=skip,
        limit=limit,
    )

    mapped = [note_helper(n) for n in feed_docs]
    if mode == "personalized":
        prefs = _subject_preferences_for_user(current_user_id)
        mapped = _personalize_feed(mapped, prefs)
    else:
        for row in mapped:
            row["personalization_reason"] = "Latest from followed creators"

    result = mapped[skip:skip + limit]
    cache_set_json(cache_key, result, ttl=90)
    return result


@router.get("/feed/personalized")
def following_feed_personalized(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=60),
    current_user=Depends(get_current_user),
):
    return following_feed(mode="personalized", skip=skip, limit=limit, current_user=current_user)


@router.get("/followers/{user_id}")
def get_followers(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    followers = list(
        follows_collection.find({"following_id": ObjectId(user_id)}, {"follower_id": 1}).sort("_id", -1)
    )
    user_map = _public_user_map([f["follower_id"] for f in followers])

    out = []
    for f in followers:
        u = user_map.get(f["follower_id"])
        if not u:
            continue
        out.append({
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "dept": u.get("dept"),
            "year": u.get("year"),
            "section": u.get("section"),
            "profile_pic_url": u.get("profile_pic_url", None),
            "verified_seller": u.get("verified_seller", False),
        })
    return out


@router.get("/following/{user_id}")
def get_following(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    following = list(
        follows_collection.find({"follower_id": ObjectId(user_id)}, {"following_id": 1}).sort("_id", -1)
    )
    user_map = _public_user_map([f["following_id"] for f in following])

    out = []
    for f in following:
        u = user_map.get(f["following_id"])
        if not u:
            continue
        out.append({
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "dept": u.get("dept"),
            "year": u.get("year"),
            "section": u.get("section"),
            "profile_pic_url": u.get("profile_pic_url", None),
            "verified_seller": u.get("verified_seller", False),
        })
    return out
