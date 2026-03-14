import os
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.database import notes_collection, purchases_collection, uploads_collection
from app.utils.dependencies import get_current_user
from app.services.pass_service import has_active_creator_pass

router = APIRouter(prefix="/download", tags=["Download"])


def _has_note_access(note: dict, user_id: str, note_id: str) -> bool:
    purchase = purchases_collection.find_one(
        {
            "note_id": ObjectId(note_id),
            "$or": [
                {"buyer_id": ObjectId(user_id), "status": "success"},
                {"user_id": ObjectId(user_id), "status": {"$in": ["success", "paid", "free"]}},
            ],
        }
    )
    if purchase is not None:
        return True
    uploader_id = note.get("uploader_id")
    if not uploader_id:
        return False
    return has_active_creator_pass(user_id, uploader_id)


def _resolve_note_file(file_url: str):
    upload_doc = uploads_collection.find_one({"file_url": file_url})

    if upload_doc:
        stored_name = upload_doc.get("stored_name")
        if stored_name:
            for candidate in (
                os.path.join("uploads/private", stored_name),
                os.path.join("uploads", stored_name),
            ):
                if os.path.exists(candidate):
                    return candidate, upload_doc

    raw = (file_url or "").lstrip("/")
    legacy = os.path.join("uploads", raw) if raw.startswith("private/") else raw
    normalized = os.path.normpath(legacy)
    allowed_roots = (os.path.normpath("uploads"), os.path.normpath("uploads/private"))
    if not any(normalized == root or normalized.startswith(root + os.sep) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not os.path.exists(normalized):
        raise HTTPException(status_code=404, detail="File not found")

    return normalized, None


@router.get("/{note_id}")
def download_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # ✅ Check access: Owner OR Purchased/Unlocked
    is_owner = str(note.get("uploader_id")) == current_user["id"]
    
    if not is_owner:
        access = _has_note_access(note, current_user["id"], note_id)
        if not access:
            raise HTTPException(status_code=403, detail="Unlock the note first")

        # ❌ Paid notes cannot be downloaded (View Only) - Business Rule
        # Owner CAN download (to verify/backup)e
        if note.get("is_paid", False) is True:
             raise HTTPException(status_code=403, detail="Paid notes cannot be downloaded (View Only)")

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached")

    file_path, upload_doc = _resolve_note_file(file_url)

    # Increment download count
    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$inc": {"downloads": 1}}
    )

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=(upload_doc or {}).get("original_name", os.path.basename(file_path))
    )
