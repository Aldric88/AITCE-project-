import os
import time
import hashlib
from bson import ObjectId
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.database import uploads_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/files", tags=["Files"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png"}

# Max file size (MB)
MAX_FILE_SIZE_MB = 15
MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Local private upload directory (not publicly mounted)
UPLOAD_DIR = "uploads/private"


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def sha256_file(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    # Basic filename validation
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    ext = get_file_extension(file.filename)

    # Check file type
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Ensure upload folder exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Safe name + unique filename
    safe_name = file.filename.replace(" ", "_").replace("/", "_")
    unique_filename = f"{int(time.time())}-{current_user['id']}-{safe_name}"
    save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file with size validation (streamed)
    size_bytes = 0

    try:
        with open(save_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunk
                if not chunk:
                    break

                size_bytes += len(chunk)

                if size_bytes > MAX_BYTES:
                    buffer.close()
                    if os.path.exists(save_path):
                        os.remove(save_path)

                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Max allowed: {MAX_FILE_SIZE_MB} MB",
                    )

                buffer.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # ✅ Compute file hash and check for duplicates
    file_hash = sha256_file(save_path)
    
    # ✅ duplicate check
    existing = uploads_collection.find_one({"file_hash": file_hash})
    if existing:
        # optional: delete new file if duplicate
        try:
            os.remove(save_path)
        except:
            pass

        return {
            "message": "Duplicate file detected ❌",
            "file_url": existing["file_url"],
            "filename": existing["stored_name"],
            "original_name": existing.get("original_name"),
            "size_bytes": existing.get("size_bytes"),
            "duplicate_of": existing["file_url"]
        }

    # Opaque file identifier (resolved via uploads_collection)
    file_url = f"/private/{unique_filename}"

    # Store upload metadata in MongoDB
    upload_doc = {
        "uploader_id": ObjectId(current_user["id"]),
        "original_name": file.filename,
        "stored_name": unique_filename,
        "file_url": file_url,
        "file_ext": ext,
        "size_bytes": size_bytes,
        "file_hash": file_hash,
        "created_at": int(time.time()),
        "is_linked": False,
        "linked_note_id": None,
    }
    uploads_collection.insert_one(upload_doc)

    return {
        "message": "File uploaded successfully ✅",
        "file_url": file_url,
        "filename": unique_filename,
        "original_name": file.filename,
        "size_bytes": size_bytes,
    }
