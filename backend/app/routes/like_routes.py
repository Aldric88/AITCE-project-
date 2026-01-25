import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import notes_collection, likes_collection, leaderboard_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/likes", tags=["Likes"])


def add_points(user_id: str, points: int, reason: str):
    leaderboard_collection.insert_one(
        {
            "user_id": ObjectId(user_id),
            "points": points,
            "reason": reason,
            "created_at": int(time.time()),
        }
    )


@router.get("/my")
def my_likes(current_user=Depends(get_current_user)):
    likes = likes_collection.find(
        {"user_id": ObjectId(current_user["id"])}
    ).sort("_id", -1)

    return [str(l["note_id"]) for l in likes]


@router.get("/{note_id}/count")
def like_count(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    count = likes_collection.count_documents({"note_id": ObjectId(note_id)})
    return {"note_id": note_id, "likes": count}


@router.post("/{note_id}")
def like_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only approved notes can be liked
    if note.get("status") != "approved":
        raise HTTPException(
            status_code=403, detail="Only approved notes can be liked"
        )

    already = likes_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
        }
    )

    if already:
        return {"message": "Already liked ✅"}

    likes_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
            "created_at": int(time.time()),
        }
    )

    # +1 points to uploader
    uploader_id = str(note["uploader_id"])
    add_points(uploader_id, 1, "Got a like")

    return {"message": "Liked ✅"}


@router.delete("/{note_id}")
def unlike_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    likes_collection.delete_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
        }
    )

    return {"message": "Unliked ✅"}
