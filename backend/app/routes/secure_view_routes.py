import os
import time
import secrets
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse

from app.database import notes_collection, purchases_collection, uploads_collection, view_sessions_collection
from app.utils.dependencies import get_current_user
from app.utils.pdf_watermark import watermark_pdf_bytes
from app.utils.image_watermark import watermark_image_bytes
from app.utils.rate_limiter import check_rate_limit
from app.services.pass_service import has_active_creator_pass

router = APIRouter(prefix="/secure", tags=["Secure Viewer"])

SESSION_TTL_SECONDS = 10 * 60  # 10 minutes


def _has_purchase_access(user_id: str, note_id: str, seller_id: ObjectId | None = None) -> bool:
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
    if seller_id is None:
        return False
    return has_active_creator_pass(user_id, seller_id)


def _resolve_note_file(file_url: str):
    upload_doc = uploads_collection.find_one({"file_url": file_url})

    if upload_doc:
        stored_name = upload_doc.get("stored_name")
        if not stored_name:
            raise HTTPException(status_code=500, detail="File metadata corrupted")

        for candidate in (
            os.path.join("uploads/private", stored_name),
            os.path.join("uploads", stored_name),  # legacy storage
        ):
            if os.path.exists(candidate):
                return candidate, upload_doc.get("file_ext", "").lower(), upload_doc

    # Legacy fallback when uploads metadata is missing
    raw = (file_url or "").lstrip("/")
    if raw.startswith("private/"):
        legacy = os.path.join("uploads", raw)
    else:
        legacy = raw

    normalized = os.path.normpath(legacy)
    allowed_roots = (os.path.normpath("uploads"), os.path.normpath("uploads/private"))
    if not any(normalized == root or normalized.startswith(root + os.sep) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not os.path.exists(normalized):
        raise HTTPException(status_code=404, detail="File not found on server")

    ext = os.path.splitext(normalized)[1].lower()
    return normalized, ext, None


@router.post("/session/start/{note_id}")
def start_session(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Check access (paid/free rules)
    if note.get("is_paid", False):
        # Paid note: user must have successful purchase
        existing = _has_purchase_access(current_user["id"], note_id, note.get("uploader_id"))
        if not existing:
            raise HTTPException(status_code=403, detail="Buy this paid note to view")
    else:
        # Free note must be unlocked too
        existing = _has_purchase_access(current_user["id"], note_id, note.get("uploader_id"))
        if not existing:
            raise HTTPException(status_code=403, detail="Unlock this note first")

    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_TTL_SECONDS

    view_sessions_collection.insert_one({
        "user_id": ObjectId(current_user["id"]),
        "note_id": ObjectId(note_id),
        "token": token,
        "expires_at": expires_at
    })

    return {
        "token": token,
        "expires_at": expires_at,
        "viewer_url": f"/secure/session/file/{note_id}?token={token}"
    }


@router.get("/session/file/{note_id}")
def get_session_file(note_id: str, token: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    session = view_sessions_collection.find_one({
        "user_id": ObjectId(current_user["id"]),
        "note_id": ObjectId(note_id),
        "token": token
    })

    if not session:
        raise HTTPException(status_code=403, detail="Invalid viewing session")

    if int(time.time()) > session["expires_at"]:
        raise HTTPException(status_code=403, detail="Session expired")

    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached")

    file_path, ext, _ = _resolve_note_file(file_url)
    watermark_text = f"{current_user['name']} | {current_user['email']} | {int(time.time())}"

    # ✅ PDF watermark
    if ext == ".pdf":
        pdf_bytes = watermark_pdf_bytes(file_path, watermark_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline; filename=watermarked.pdf",
                "Cache-Control": "no-store"
            }
        )

    # ✅ Image watermark (jpg/png)
    if ext in [".jpg", ".jpeg", ".png"]:
        img_bytes = watermark_image_bytes(file_path, watermark_text)
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "inline; filename=watermarked.jpg",
                "Cache-Control": "no-store"
            }
        )

    # ❌ docx/pptx cannot be viewed in browser directly, use secure download
    raise HTTPException(
        status_code=400,
        detail="This file type cannot be previewed. Use secure download endpoint."
    )


def check_note_access(note, note_id: str, current_user: dict):
    """
    Checks whether current_user can access this note (free/paid rules).
    """
    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Note is not approved")

    # Paid note access check
    if note.get("is_paid", False):
        is_owner = str(note["uploader_id"]) == current_user["id"]
        purchase_ok = _has_purchase_access(
            current_user["id"],
            note_id,
            note.get("uploader_id"),
        )

        if not purchase_ok and not is_owner:
            raise HTTPException(status_code=403, detail="Purchase required to access this note")


@router.get("/note/{note_id}/file")
def view_note_file(note_id: str, current_user=Depends(get_current_user)):
    # ✅ Rate limit protection
    if not check_rate_limit(current_user["id"]):
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.")

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    check_note_access(note, note_id, current_user)

    # ✅ Increment views counter
    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$inc": {"views": 1}}
    )

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached to this note")

    file_path, ext, _ = _resolve_note_file(file_url)

    watermark_text = f"{current_user['name']} | {current_user['email']} | {current_user['id']}"

    # ✅ PDF watermark
    if ext == ".pdf":
        pdf_bytes = watermark_pdf_bytes(file_path, watermark_text)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "inline; filename=watermarked.pdf",
                "Cache-Control": "no-store"
            }
        )

    # ✅ Image watermark (jpg/png)
    if ext in [".jpg", ".jpeg", ".png"]:
        img_bytes = watermark_image_bytes(file_path, watermark_text)
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "inline; filename=watermarked.jpg",
                "Cache-Control": "no-store"
            }
        )

    # ❌ docx/pptx cannot be viewed in browser directly, use secure download
    raise HTTPException(
        status_code=400,
        detail="This file type cannot be previewed. Use secure download endpoint."
    )


@router.get("/note/{note_id}/download")
def download_note_file(note_id: str, current_user=Depends(get_current_user)):
    # ✅ Rate limit protection
    if not check_rate_limit(current_user["id"]):
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.")

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    check_note_access(note, note_id, current_user)

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached to this note")

    file_path, _, upload_doc = _resolve_note_file(file_url)

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=(upload_doc or {}).get("original_name", os.path.basename(file_path)),
        headers={"Cache-Control": "no-store"}
    )
