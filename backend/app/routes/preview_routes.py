import os
import mimetypes
import time
import logging
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
import fitz  # pymupdf

from app.database import notes_collection, uploads_collection
from app.utils.pdf_preview import paid_preview_pages, build_pdf_preview_cached
from app.utils.cache import cache_get_json, cache_set_json

router = APIRouter(prefix="/preview", tags=["Preview"])
logger = logging.getLogger(__name__)


def _resolve_note_file(file_url: str) -> str:
    upload_doc = uploads_collection.find_one({"file_url": file_url})
    if upload_doc:
        stored_name = upload_doc.get("stored_name")
        if stored_name:
            for candidate in (
                os.path.join("uploads/private", stored_name),
                os.path.join("uploads", stored_name),
            ):
                if os.path.exists(candidate):
                    return candidate

    raw = (file_url or "").lstrip("/")
    legacy = os.path.join("uploads", raw) if raw.startswith("private/") else raw
    normalized = os.path.normpath(legacy)
    allowed_roots = (os.path.normpath("uploads"), os.path.normpath("uploads/private"))
    if not any(normalized == root or normalized.startswith(root + os.sep) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not os.path.exists(normalized):
        raise HTTPException(status_code=404, detail="File not found on server")
    return normalized


def _file_signature(path: str) -> str:
    st = os.stat(path)
    return f"{int(st.st_mtime)}-{st.st_size}"


def _etag(path: str) -> str:
    return f'W/"{_file_signature(path)}"'


@router.get("/{note_id}")
def preview_note(note_id: str, request: Request):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached")

    file_path = _resolve_note_file(file_url)
    content_type, _ = mimetypes.guess_type(file_path)
    is_pdf = str(file_path).lower().endswith(".pdf")
    is_image = str(note.get("note_type", "")).lower() == "image" or (content_type or "").startswith("image/")

    # Fast path for images
    if is_image:
        etag = _etag(file_path)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=300"})
        return FileResponse(file_path, media_type=content_type or "application/octet-stream", headers={"ETag": etag, "Cache-Control": "public, max-age=300"})

    if not is_pdf:
        raise HTTPException(status_code=400, detail="Preview supported for PDF/image notes only")

    sig = _file_signature(file_path)
    page_cache_key = f"preview:pdf-pages:{note_id}:{sig}"
    total_pages = cache_get_json(page_cache_key)
    if total_pages is None:
        started = time.time()
        doc = fitz.open(file_path)
        total_pages = doc.page_count
        doc.close()
        cache_set_json(page_cache_key, total_pages, ttl=12 * 60 * 60)
        logger.info("db_profile name=preview_pdf_pagecount elapsed_ms=%s note_id=%s", int((time.time() - started) * 1000), note_id)

    # ✅ Free = full PDF preview (no watermark)
    if note.get("is_paid", False) is False:
        etag = _etag(file_path)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=300"})
        return FileResponse(file_path, media_type="application/pdf", headers={"ETag": etag, "Cache-Control": "public, max-age=300"})

    # ✅ Paid = limited preview + watermark + cache
    preview_pages = paid_preview_pages(total_pages)

    wm_text = f"PREVIEW ONLY - Purchase for full access"

    preview_path = build_pdf_preview_cached(
      input_path=file_path,
      output_dir="uploads/previews",
      note_id=str(note["_id"]),
      max_pages=preview_pages,
      watermark_text=wm_text,
      source_signature=sig,
    )
    etag = _etag(preview_path)
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=300"})
    return FileResponse(preview_path, media_type="application/pdf", headers={"ETag": etag, "Cache-Control": "public, max-age=300"})
