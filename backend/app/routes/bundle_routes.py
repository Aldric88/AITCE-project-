import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.database import bundles_collection, notes_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/bundles", tags=["Bundles"])


class BundleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    note_ids: List[str]
    price: int = 0


@router.post("/")
def create_bundle(data: BundleCreate, current_user=Depends(get_current_user)):
    if len(data.note_ids) < 2:
        raise HTTPException(status_code=400, detail="Bundle needs at least 2 notes")

    # validate notes ownership
    valid_notes = []
    for nid in data.note_ids:
        if not ObjectId.is_valid(nid):
            raise HTTPException(status_code=400, detail=f"Invalid note id: {nid}")

        n = notes_collection.find_one({"_id": ObjectId(nid)})
        if not n:
            raise HTTPException(status_code=404, detail=f"Note not found: {nid}")

        if str(n.get("uploader_id")) != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can bundle only your notes")

        if n.get("status") != "approved":
            raise HTTPException(status_code=400, detail="All notes must be approved")

        valid_notes.append(ObjectId(nid))

    doc = {
        "title": data.title,
        "description": data.description,
        "note_ids": valid_notes,
        "creator_id": ObjectId(current_user["id"]),
        "is_paid": True if data.price > 0 else False,
        "price": data.price,
        "created_at": int(time.time()),
    }

    res = bundles_collection.insert_one(doc)
    return {"message": "Bundle created ✅", "id": str(res.inserted_id)}


@router.get("/")
def list_bundles():
    bundles = bundles_collection.find().sort("_id", -1)

    out = []
    for b in bundles:
        out.append({
            "id": str(b["_id"]),
            "title": b.get("title"),
            "description": b.get("description"),
            "price": b.get("price", 0),
            "note_count": len(b.get("note_ids", [])),
        })
    return out
