import os
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse

from app.database import notes_collection, purchases_collection, uploads_collection
from app.utils.dependencies import get_current_user
from app.utils.pdf_watermark import watermark_pdf_bytes
from app.utils.image_watermark import watermark_image_bytes
from app.utils.rate_limiter import check_rate_limit

router = APIRouter(prefix="/secure", tags=["Secure Viewer"])


def check_note_access(note, note_id: str, current_user: dict):
    """
    Checks whether current_user can access this note (free/paid rules).
    """
    if note.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Note is not approved")

    # Paid note access check
    if note.get("is_paid", False):
        is_owner = str(note["uploader_id"]) == current_user["id"]

        purchase = purchases_collection.find_one({
            "note_id": ObjectId(note_id),
            "buyer_id": ObjectId(current_user["id"]),
            "status": "success"
        })

        if not purchase and not is_owner:
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

    upload_doc = uploads_collection.find_one({"file_url": file_url})
    if not upload_doc:
        raise HTTPException(status_code=404, detail="Uploaded file record not found")

    stored_name = upload_doc.get("stored_name")
    if not stored_name:
        raise HTTPException(status_code=500, detail="File metadata corrupted")

    file_path = os.path.join("uploads", stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    ext = upload_doc.get("file_ext", "").lower()

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

    upload_doc = uploads_collection.find_one({"file_url": file_url})
    if not upload_doc:
        raise HTTPException(status_code=404, detail="Uploaded file record not found")

    stored_name = upload_doc.get("stored_name")
    if not stored_name:
        raise HTTPException(status_code=500, detail="File metadata corrupted")

    file_path = os.path.join("uploads", stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=upload_doc.get("original_name", stored_name),
        headers={"Cache-Control": "no-store"}
    )
