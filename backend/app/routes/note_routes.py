import os
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from typing import Optional

from app.database import (
    notes_collection,
    uploads_collection,
    moderation_logs_collection,
    leaderboard_collection,
    reviews_collection,
    purchases_collection,
    likes_collection,
)
from app.schemas.note_schema import NoteCreate, NoteUpdate, ModerationActionRequest
from app.models.note_model import note_helper
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/notes", tags=["Notes"])


def _add_points(user_id, points: int, reason: str):
    leaderboard_collection.insert_one(
        {
            "user_id": user_id,
            "points": points,
            "reason": reason,
            "created_at": int(time.time()),
        }
    )


# Student uploads note (always pending)
@router.post("/")
def create_note(note: NoteCreate, current_user=Depends(get_current_user)):
    new_note = note.model_dump()
    uploader_id = ObjectId(current_user["id"])

    # ✅ only verified sellers can post paid notes
    if new_note.get("is_paid") is True:
        if current_user.get("verified_seller") is not True:
            raise HTTPException(
                status_code=403,
                detail="Only verified sellers can upload paid notes"
            )

        if new_note.get("price", 0) <= 0:
            raise HTTPException(status_code=400, detail="Paid notes must have valid price")

    # uploader info
    new_note["uploader_id"] = uploader_id
    new_note["status"] = "pending"

    # validate note type requirements
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        if not note.file_url:
            raise HTTPException(
                status_code=400,
                detail="file_url is required for this note_type",
            )

        # SECURITY: file_url must exist in uploads collection
        upload_doc = uploads_collection.find_one({"file_url": note.file_url})
        if not upload_doc:
            raise HTTPException(
                status_code=400,
                detail="Invalid file_url (file not found). Upload the file first.",
            )

        # SECURITY: file must belong to same user
        if upload_doc["uploader_id"] != uploader_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to use this file_url (not your upload).",
            )

        # SECURITY: prevent reusing same uploaded file in multiple notes
        if upload_doc.get("is_linked") is True:
            raise HTTPException(
                status_code=400,
                detail="This file is already linked to another note.",
            )

    elif note.note_type == "link":
        if not note.external_link:
            raise HTTPException(
                status_code=400,
                detail="external_link is required for link note_type",
            )

    elif note.note_type == "text":
        pass

    else:
        raise HTTPException(status_code=400, detail="Invalid note_type")

    # insert note
    result = notes_collection.insert_one(new_note)
    saved_note = notes_collection.find_one({"_id": result.inserted_id})

    # mark upload as linked to this note (only for file-based notes)
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        uploads_collection.update_one(
            {"file_url": note.file_url},
            {"$set": {"is_linked": True, "linked_note_id": saved_note["_id"]}},
        )

    return note_helper(saved_note)


# Approved notes feed (public)
@router.get("/")
def get_approved_notes(
    dept: Optional[str] = Query(default=None),
    semester: Optional[int] = Query(default=None),
    subject: Optional[str] = Query(default=None),
):
    query = {"status": "approved"}

    if dept:
        query["dept"] = dept
    if semester:
        query["semester"] = semester
    if subject:
        query["subject"] = subject

    notes = notes_collection.find(query).sort("_id", -1)
    return [note_helper(n) for n in notes]


# My uploaded notes
@router.get("/my")
def my_notes(current_user=Depends(get_current_user)):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"])}
    ).sort("_id", -1)
    return [note_helper(n) for n in notes]


# Moderation queue (moderator/admin)
@router.get("/pending")
def pending_notes(
    current_user=Depends(require_role(["moderator", "admin"])),
):
    notes = notes_collection.find({"status": "pending"}).sort("_id", -1)
    return [note_helper(n) for n in notes]


# Approve/reject note + moderation log (moderator/admin)
@router.patch("/{note_id}/moderate")
def moderate_note(
    note_id: str,
    data: ModerationActionRequest,
    current_user=Depends(require_role(["moderator", "admin"])),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") != "pending":
        raise HTTPException(
            status_code=400, detail="Only pending notes can be moderated"
        )

    # update note status
    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": {"status": data.status}},
    )

    # +10 points to uploader when approved
    if data.status == "approved":
        _add_points(note["uploader_id"], 10, "Note approved")

    # add moderation log
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": data.status,
            "reason": data.reason,
            "created_at": int(time.time()),
        }
    )

    updated = notes_collection.find_one({"_id": ObjectId(note_id)})
    return {
        "message": f"Note {data.status} ✅",
        "note": note_helper(updated),
    }


# Moderation logs for a note (moderator/admin)
@router.get("/{note_id}/logs")
def get_note_logs(
    note_id: str,
    current_user=Depends(require_role(["moderator", "admin"])),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    logs = moderation_logs_collection.find(
        {"note_id": ObjectId(note_id)}
    ).sort("_id", -1)

    result = []
    for log in logs:
        result.append(
            {
                "id": str(log["_id"]),
                "note_id": str(log["note_id"]),
                "moderator_id": str(log["moderator_id"]),
                "action": log["action"],
                "reason": log.get("reason"),
                "created_at": log["created_at"],
            }
        )

    return result


# Edit note metadata (owner only)
@router.patch("/{note_id}")
def update_note(
    note_id: str,
    data: NoteUpdate,
    current_user=Depends(get_current_user),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only owner can edit
    if str(note["uploader_id"]) != current_user["id"]:
        raise HTTPException(
            status_code=403, detail="You can only edit your own note"
        )

    updates = {k: v for k, v in data.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=400, detail="No fields provided to update"
        )

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": updates},
    )

    updated = notes_collection.find_one({"_id": ObjectId(note_id)})
    return note_helper(updated)


# Delete note + unlink upload, remove file from disk (owner or admin)
@router.delete("/{note_id}")
def delete_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only owner OR admin can delete
    if str(note["uploader_id"]) != current_user["id"] and current_user[
        "role"
    ] != "admin":
        raise HTTPException(
            status_code=403, detail="Not allowed to delete this note"
        )

    # unlink upload and remove file if it is file-based
    file_url = note.get("file_url")
    if file_url:
        upload_doc = uploads_collection.find_one({"file_url": file_url})

        if upload_doc:
            # unlink in DB
            uploads_collection.update_one(
                {"file_url": file_url},
                {"$set": {"is_linked": False, "linked_note_id": None}},
            )

            # delete actual file from disk
            stored_name = upload_doc.get("stored_name")
            if stored_name:
                local_path = os.path.join("uploads", stored_name)
                if os.path.exists(local_path):
                    os.remove(local_path)

            # delete upload record
            uploads_collection.delete_one({"file_url": file_url})

    # delete the note
    notes_collection.delete_one({"_id": ObjectId(note_id)})

    return {"message": "Note deleted successfully ✅", "note_id": note_id}


@router.get("/{note_id}/details")
def note_details(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Note not approved")

    # likes count
    likes_count = likes_collection.count_documents({"note_id": ObjectId(note_id)})

    # reviews summary
    pipeline = [
        {"$match": {"note_id": ObjectId(note_id)}},
        {"$group": {"_id": "$note_id", "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    summary = list(reviews_collection.aggregate(pipeline))
    avg_rating = round(summary[0]["avg_rating"], 2) if summary else 0
    review_count = summary[0]["count"] if summary else 0

    # access check for paid
    has_access = True
    if note.get("is_paid", False):
        is_owner = str(note["uploader_id"]) == current_user["id"]
        purchase = purchases_collection.find_one({
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "success"
        })
        has_access = True if (purchase or is_owner) else False

    note_out = {
        "id": str(note["_id"]),
        "title": note.get("title"),
        "description": note.get("description"),
        "dept": note.get("dept"),
        "semester": note.get("semester"),
        "subject": note.get("subject"),
        "unit": note.get("unit"),
        "tags": note.get("tags", []),
        "note_type": note.get("note_type"),
        "file_url": note.get("file_url"),
        "status": note.get("status"),
        "uploader_id": str(note.get("uploader_id")),
        "is_paid": note.get("is_paid", False),
        "price": note.get("price", 0),
        "likes": likes_count,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "has_access": has_access,
    }

    return note_out


@router.get("/trending")
def trending_notes():
    notes = notes_collection.find({"status": "approved"}).sort("views", -1).limit(20)

    result = []
    for n in notes:
        result.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "dept": n.get("dept"),
            "subject": n.get("subject"),
            "semester": n.get("semester"),
            "unit": n.get("unit"),
            "is_paid": n.get("is_paid", False),
            "price": n.get("price", 0),
            "views": n.get("views", 0),
        })
    return result
