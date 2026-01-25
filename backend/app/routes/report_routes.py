import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional

from app.database import reports_collection, notes_collection
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportCreate(BaseModel):
    reason: Literal["spam", "fake", "misleading", "copyright", "other"]
    message: Optional[str] = None


@router.post("/note/{note_id}")
def report_note(note_id: str, data: ReportCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    reports_collection.insert_one({
        "note_id": ObjectId(note_id),
        "reporter_id": ObjectId(current_user["id"]),
        "reason": data.reason,
        "message": data.message,
        "status": "pending",  # pending / resolved
        "created_at": int(time.time())
    })

    return {"message": "Report submitted ✅"}


@router.get("/pending")
def pending_reports(current_user=Depends(require_role(["moderator", "admin"]))):
    reports = reports_collection.find({"status": "pending"}).sort("_id", -1)

    result = []
    for r in reports:
        result.append({
            "id": str(r["_id"]),
            "note_id": str(r["note_id"]),
            "reporter_id": str(r["reporter_id"]),
            "reason": r["reason"],
            "message": r.get("message"),
            "status": r["status"],
            "created_at": r["created_at"],
        })

    return result


@router.patch("/{report_id}/resolve")
def resolve_report(report_id: str, current_user=Depends(require_role(["moderator", "admin"]))):
    if not ObjectId.is_valid(report_id):
        raise HTTPException(status_code=400, detail="Invalid report_id")

    reports_collection.update_one(
        {"_id": ObjectId(report_id)},
        {"$set": {"status": "resolved"}}
    )

    return {"message": "Report resolved ✅"}
