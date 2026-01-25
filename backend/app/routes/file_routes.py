import os
import time
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

# Local upload directory
UPLOAD_DIR = "uploads"


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


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

    # Public URL served via StaticFiles (in main.py)
    file_url = f"/uploads/{unique_filename}"

    # Store upload metadata in MongoDB
    upload_doc = {
        "uploader_id": ObjectId(current_user["id"]),
        "original_name": file.filename,
        "stored_name": unique_filename,
        "file_url": file_url,
        "file_ext": ext,
        "size_bytes": size_bytes,
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
