from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
import time

from app.database import (
    comments_collection,
    notes_collection,
    users_collection,
    comment_likes_collection
)
from app.utils.dependencies import get_current_user, require_role
from app.utils.notify import notify

router = APIRouter(prefix="/comments", tags=["Comments"])


def user_public(user_doc):
    if not user_doc:
        return {
            "id": None,
            "name": "Unknown User",
            "dept": None,
            "year": None,
            "section": None,
            "profile_pic_url": None,
            "verified_seller": False,
        }

    return {
        "id": str(user_doc["_id"]),
        "name": user_doc.get("name"),
        "dept": user_doc.get("dept"),
        "year": user_doc.get("year"),
        "section": user_doc.get("section"),
        "profile_pic_url": user_doc.get("profile_pic_url"),
        "verified_seller": user_doc.get("verified_seller", False),
    }


def likes_count(comment_id: ObjectId) -> int:
    return comment_likes_collection.count_documents({"comment_id": comment_id})


def liked_by_me(comment_id: ObjectId, me_id: ObjectId) -> bool:
    return comment_likes_collection.find_one({"comment_id": comment_id, "user_id": me_id}) is not None


# ✅ Get comments as threads (parent + replies)
@router.get("/{note_id}")
def get_comments(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    me_id = ObjectId(current_user["id"])

    # get all comments for note
    docs = list(
        comments_collection.find({"note_id": ObjectId(note_id)}).sort("created_at", 1)
    )
    if not docs:
        return []

    comment_ids = [d["_id"] for d in docs]
    user_ids = list({d["user_id"] for d in docs if d.get("user_id")})

    user_map = {}
    if user_ids:
        for u in users_collection.find(
            {"_id": {"$in": user_ids}},
            {"name": 1, "dept": 1, "year": 1, "section": 1, "profile_pic_url": 1, "verified_seller": 1},
        ):
            user_map[u["_id"]] = u

    likes_map = {}
    for row in comment_likes_collection.aggregate(
        [
            {"$match": {"comment_id": {"$in": comment_ids}}},
            {"$group": {"_id": "$comment_id", "count": {"$sum": 1}}},
        ]
    ):
        likes_map[row["_id"]] = int(row.get("count", 0))

    liked_ids = set()
    for row in comment_likes_collection.find(
        {"comment_id": {"$in": comment_ids}, "user_id": me_id},
        {"comment_id": 1},
    ):
        liked_ids.add(row["comment_id"])

    # separate parents and replies
    parents = [c for c in docs if c.get("parent_id") is None]
    replies = [c for c in docs if c.get("parent_id") is not None]

    # build reply map: parent_id -> list(replies)
    reply_map = {}
    for r in replies:
        pid = str(r["parent_id"])
        reply_map.setdefault(pid, []).append(r)

    out = []

    # pinned should come first
    parents.sort(key=lambda x: (not x.get("is_pinned", False), x.get("created_at", 0)))

    for p in parents:
        u = user_map.get(p["user_id"])

        parent_obj = {
            "id": str(p["_id"]),
            "note_id": str(p["note_id"]),
            "comment": p["comment"],
            "created_at": p["created_at"],
            "parent_id": None,
            "is_pinned": p.get("is_pinned", False),
            "likes_count": likes_map.get(p["_id"], 0),
            "liked_by_me": p["_id"] in liked_ids,
            "user": user_public(u),
            "replies": []
        }

        rep_list = reply_map.get(str(p["_id"]), [])
        for r in rep_list:
            ru = user_map.get(r["user_id"])

            parent_obj["replies"].append({
                "id": str(r["_id"]),
                "note_id": str(r["note_id"]),
                "comment": r["comment"],
                "created_at": r["created_at"],
                "parent_id": str(r["parent_id"]),
                "is_pinned": r.get("is_pinned", False),
                "likes_count": likes_map.get(r["_id"], 0),
                "liked_by_me": r["_id"] in liked_ids,
                "user": user_public(ru),
            })

        out.append(parent_obj)

    return out


# ✅ Add comment (parent OR reply)
@router.post("/{note_id}")
def add_comment(note_id: str, body: dict, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    text = body.get("comment", "").strip()
    parent_id = body.get("parent_id")  # can be None

    if len(text) < 1:
        raise HTTPException(status_code=400, detail="Comment required")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    parent_obj_id = None
    if parent_id:
        if not ObjectId.is_valid(parent_id):
            raise HTTPException(status_code=400, detail="Invalid parent_id")

        parent_doc = comments_collection.find_one({"_id": ObjectId(parent_id)})
        if not parent_doc:
            raise HTTPException(status_code=404, detail="Parent comment not found")

        if str(parent_doc["note_id"]) != note_id:
            raise HTTPException(status_code=400, detail="Parent comment not in this note")

        parent_obj_id = ObjectId(parent_id)

    comments_collection.insert_one({
        "note_id": ObjectId(note_id),
        "user_id": ObjectId(current_user["id"]),
        "comment": text,
        "parent_id": parent_obj_id,
        "is_pinned": False,
        "created_at": int(time.time())
    })

    # ✅ notify note owner when someone comments/replies
    if str(note["uploader_id"]) != current_user["id"]:
        notify(
            user_id=note["uploader_id"],
            type="COMMENT",
            message=f"{current_user['name']} commented on your note",
            link=f"/notes/{note_id}"
        )

    return {"message": "Comment added ✅"}


# ✅ Like/Unlike comment
@router.post("/{comment_id}/like")
def like_comment(comment_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=400, detail="Invalid comment id")

    c = comments_collection.find_one({"_id": ObjectId(comment_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")

    me_id = ObjectId(current_user["id"])

    exists = comment_likes_collection.find_one({
        "comment_id": ObjectId(comment_id),
        "user_id": me_id
    })

    if exists:
        return {"message": "Already liked ✅"}

    comment_likes_collection.insert_one({
        "comment_id": ObjectId(comment_id),
        "user_id": me_id,
        "created_at": int(time.time())
    })

    # notify comment owner
    if str(c["user_id"]) != current_user["id"]:
        notify(
            user_id=c["user_id"],
            type="COMMENT_LIKE",
            message=f"{current_user['name']} liked your comment",
            link=f"/notes/{str(c['note_id'])}"
        )

    return {"message": "Liked ✅"}


@router.delete("/{comment_id}/like")
def unlike_comment(comment_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=400, detail="Invalid comment id")

    me_id = ObjectId(current_user["id"])

    comment_likes_collection.delete_one({
        "comment_id": ObjectId(comment_id),
        "user_id": me_id
    })

    return {"message": "Unliked ✅"}


# ✅ Pin/Unpin comment (creator OR moderator/admin)
@router.post("/{comment_id}/pin")
def pin_comment(comment_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=400, detail="Invalid comment id")

    c = comments_collection.find_one({"_id": ObjectId(comment_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")

    note = notes_collection.find_one({"_id": c["note_id"]})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # ✅ allowed: note owner OR moderator/admin
    is_owner = (str(note["uploader_id"]) == current_user["id"])
    is_staff = current_user["role"] in ["admin", "moderator"]

    if not (is_owner or is_staff):
        raise HTTPException(status_code=403, detail="Not allowed to pin")

    # ✅ unpin all others first (only 1 pinned)
    comments_collection.update_many(
        {"note_id": c["note_id"]},
        {"$set": {"is_pinned": False}}
    )

    comments_collection.update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": {"is_pinned": True}}
    )

    return {"message": "Pinned ✅"}


@router.delete("/{comment_id}/pin")
def unpin_comment(comment_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=400, detail="Invalid comment id")

    c = comments_collection.find_one({"_id": ObjectId(comment_id)})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")

    note = notes_collection.find_one({"_id": c["note_id"]})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    is_owner = (str(note["uploader_id"]) == current_user["id"])
    is_staff = current_user["role"] in ["admin", "moderator"]

    if not (is_owner or is_staff):
        raise HTTPException(status_code=403, detail="Not allowed to unpin")

    comments_collection.update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": {"is_pinned": False}}
    )

    return {"message": "Unpinned ✅"}
