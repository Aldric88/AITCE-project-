import os
import time
import uuid
from typing import Optional
from pydantic import BaseModel
from bson import ObjectId
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.utils.dependencies import get_current_user
from app.database import users_collection

router = APIRouter(prefix="/profile", tags=["Profile"])

PROFILE_DIR = "uploads/profile"
os.makedirs(PROFILE_DIR, exist_ok=True)

ALLOWED_EXT = [".png", ".jpg", ".jpeg", ".webp"]
MAX_SIZE_BYTES = 3 * 1024 * 1024  # 3MB


@router.post("/upload-pic")
async def upload_profile_pic(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    filename = file.filename.lower()

    ext = "." + filename.split(".")[-1]
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Only png/jpg/jpeg/webp allowed")

    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 3MB)")

    safe_name = f"{int(time.time())}-{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(PROFILE_DIR, safe_name)

    with open(save_path, "wb") as f:
        f.write(content)

    url = f"/uploads/profile/{safe_name}"

    users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"profile_pic_url": url}}
    )

    return {
        "message": "Profile picture updated ✅",
        "profile_pic_url": url
    }


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    dept: Optional[str] = None
    year: Optional[int] = None
    section: Optional[str] = None
    cluster_id: Optional[str] = None # Only if manual user


@router.patch("/me")
def update_profile(data: ProfileUpdate, current_user=Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Security: Domain Locking
    if "cluster_id" in updates:
        if current_user.get("verified_by_domain") is True:
             raise HTTPException(
                status_code=403, 
                detail="Domain-verified users cannot change their cluster."
            )
        
        # Verify cluster exists if changing
        if updates["cluster_id"]:
             from app.database import clusters_collection
             if not clusters_collection.find_one({"_id": ObjectId(updates["cluster_id"])}):
                 raise HTTPException(status_code=400, detail="Invalid cluster_id")
             updates["cluster_id"] = ObjectId(updates["cluster_id"])

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    users_collection.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": updates}
    )
    
    return {"message": "Profile updated ✅"}
