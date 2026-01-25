import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import notes_collection, bookmarks_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


@router.get("/my")
def my_bookmarks(current_user=Depends(get_current_user)):
    bookmarks = bookmarks_collection.find(
        {"user_id": ObjectId(current_user["id"])}
    ).sort("_id", -1)

    result = []
    for b in bookmarks:
        note = notes_collection.find_one({"_id": b["note_id"]})
        if note and note.get("status") == "approved":
            result.append(
                {
                    "bookmark_id": str(b["_id"]),
                    "note_id": str(b["note_id"]),
                    "created_at": b["created_at"],
                    "note": {
                        "id": str(note["_id"]),
                        "title": note.get("title"),
                        "subject": note.get("subject"),
                        "unit": note.get("unit"),
                        "semester": note.get("semester"),
                        "dept": note.get("dept"),
                        "file_url": note.get("file_url"),
                        "status": note.get("status"),
                    },
                }
            )

    return result


@router.post("/{note_id}")
def bookmark_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    already = bookmarks_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
        }
    )

    if already:
        return {"message": "Already bookmarked ✅"}

    bookmarks_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
            "created_at": int(time.time()),
        }
    )

    return {"message": "Bookmarked ✅"}


@router.delete("/{note_id}")
def remove_bookmark(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    bookmarks_collection.delete_one(
        {
            "note_id": ObjectId(note_id),
            "user_id": ObjectId(current_user["id"]),
        }
    )

    return {"message": "Bookmark removed ✅"}
