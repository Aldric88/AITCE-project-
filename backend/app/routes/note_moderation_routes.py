import time

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import (
    follows_collection,
    moderation_logs_collection,
    moderation_rules_collection,
    notes_collection,
    users_collection,
)
from app.models.note_model import note_helper
from app.schemas.note_schema import ModerationActionRequest
from app.utils.audit import log_audit_event
from app.utils.dependencies import require_role
from app.utils.notify import notify
from app.utils.cache import cache_delete_prefix

router = APIRouter(prefix="/notes", tags=["Notes Moderation"])


class RejectRequest(BaseModel):
    reason: str = "Rejected by moderator"


class OverrideRejectRequest(BaseModel):
    reason: str = "Rejected by moderator override"


def _quality_gate_rules():
    cfg = moderation_rules_collection.find_one({"config_name": "default"})
    if cfg:
        return cfg
    return {"quality_gate_paid_min_quality": 0.55}


def _notify_followers_about_approved_note(note_id: str, note: dict):
    uploader_id = str(note.get("uploader_id", ""))
    if not uploader_id or not ObjectId.is_valid(uploader_id):
        return
    uploader = users_collection.find_one({"_id": ObjectId(uploader_id)}, {"name": 1})
    creator_name = (uploader or {}).get("name") or "A creator"
    title = note.get("title", "New note")
    message = f"{creator_name} uploaded a new approved note: {title}"
    link = f"/notes/{note_id}"
    followers = follows_collection.find({"following_id": ObjectId(uploader_id)}, {"follower_id": 1})
    for edge in followers:
        follower_id = str(edge["follower_id"])
        notify(follower_id, "upload", message, link)
        cache_delete_prefix(f"feed:follow:{follower_id}:")


def _invalidate_followers_feed_cache(note: dict):
    uploader_id = str(note.get("uploader_id", ""))
    if not uploader_id or not ObjectId.is_valid(uploader_id):
        return
    followers = follows_collection.find({"following_id": ObjectId(uploader_id)}, {"follower_id": 1})
    for edge in followers:
        cache_delete_prefix(f"feed:follow:{str(edge['follower_id'])}:")


@router.get("/pending")
def pending_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(require_role(["moderator", "admin"])),
):
    total = notes_collection.count_documents({"status": "pending"})
    notes = notes_collection.find({"status": "pending"}).sort("_id", -1).skip(skip).limit(limit)
    result = []
    for n in notes:
        result.append(
            {
                "id": str(n["_id"]),
                "title": n.get("title"),
                "subject": n.get("subject"),
                "dept": n.get("dept"),
                "semester": n.get("semester"),
                "unit": n.get("unit"),
                "note_type": n.get("note_type"),
                "is_paid": n.get("is_paid", False),
                "price": n.get("price", 0),
                "uploader_id": str(n.get("uploader_id")),
                "ai": n.get("ai"),
            }
        )
    return {"total": total, "skip": skip, "limit": limit, "items": result}


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
        raise HTTPException(status_code=400, detail="Only pending notes can be moderated")

    if data.status == "approved" and note.get("is_paid", False):
        minimum_quality = float(_quality_gate_rules().get("quality_gate_paid_min_quality", 0.55))
        note_quality = float((note.get("ai") or {}).get("quality_score", 0.0))
        if note_quality < minimum_quality:
            raise HTTPException(
                status_code=400,
                detail=f"Paid note quality gate failed ({note_quality:.2f} < {minimum_quality:.2f})",
            )

    notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": {"status": data.status}})
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": data.status,
            "reason": data.reason,
            "created_at": int(time.time()),
        }
    )
    log_audit_event("moderate_note", current_user["id"], note_id, {"action": data.status, "reason": data.reason})
    notify(str(note["uploader_id"]), "moderation", f"Your note '{note.get('title','')}' was {data.status}.", f"/notes/{note_id}")
    if data.status == "approved":
        _notify_followers_about_approved_note(note_id, note)

    updated = notes_collection.find_one({"_id": ObjectId(note_id)})
    return {"message": f"Note {data.status} ✅", "note": note_helper(updated)}


@router.get("/{note_id}/logs")
def get_note_logs(
    note_id: str,
    current_user=Depends(require_role(["moderator", "admin"])),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    logs = moderation_logs_collection.find({"note_id": ObjectId(note_id)}).sort("_id", -1)
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


@router.get("/rejected")
def get_rejected_notes(current_user=Depends(require_role(["admin", "moderator"]))):
    notes = notes_collection.find({"status": "rejected"}).sort("_id", -1)
    result = []
    for n in notes:
        result.append(
            {
                "id": str(n["_id"]),
                "title": n.get("title"),
                "subject": n.get("subject"),
                "dept": n.get("dept"),
                "semester": n.get("semester"),
                "unit": n.get("unit"),
                "note_type": n.get("note_type"),
                "is_paid": n.get("is_paid", False),
                "price": n.get("price", 0),
                "rejected_reason": n.get("rejected_reason", "No reason provided"),
                "rejected_at": n.get("rejected_at"),
                "ai": n.get("ai"),
            }
        )
    return result


@router.get("/approved")
def admin_get_approved_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_role(["admin", "moderator"])),
):
    notes = notes_collection.find({"status": "approved"}).sort("_id", -1).skip(skip).limit(limit)
    result = []
    for n in notes:
        result.append(
            {
                "id": str(n["_id"]),
                "title": n.get("title"),
                "subject": n.get("subject"),
                "dept": n.get("dept"),
                "semester": n.get("semester"),
                "unit": n.get("unit"),
                "note_type": n.get("note_type"),
                "is_paid": n.get("is_paid", False),
                "price": n.get("price", 0),
                "approved_at": n.get("approved_at"),
                "ai": n.get("ai"),
            }
        )
    return result


@router.patch("/{note_id}/approve")
def approve_note(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.get("is_paid", False):
        minimum_quality = float(_quality_gate_rules().get("quality_gate_paid_min_quality", 0.55))
        note_quality = float((note.get("ai") or {}).get("quality_score", 0.0))
        if note_quality < minimum_quality:
            raise HTTPException(
                status_code=400,
                detail=f"Paid note quality gate failed ({note_quality:.2f} < {minimum_quality:.2f})",
            )

    notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": {"status": "approved", "approved_at": int(time.time())}})
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": "approved",
            "reason": "manual approve endpoint",
            "created_at": int(time.time()),
        }
    )
    log_audit_event("approve_note", current_user["id"], note_id, {})
    notify(str(note["uploader_id"]), "moderation", f"Your note '{note.get('title','')}' was approved.", f"/notes/{note_id}")
    _notify_followers_about_approved_note(note_id, note)
    return {"message": "Note approved ✅"}


@router.patch("/{note_id}/reject")
def reject_note(note_id: str, data: RejectRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": {"status": "rejected", "rejected_reason": data.reason, "rejected_at": int(time.time())}},
    )
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": "rejected",
            "reason": data.reason,
            "created_at": int(time.time()),
        }
    )
    log_audit_event("reject_note", current_user["id"], note_id, {"reason": data.reason})
    notify(
        str(note["uploader_id"]),
        "moderation",
        f"Your note '{note.get('title','')}' was rejected: {data.reason}",
        f"/notes/{note_id}",
    )
    _invalidate_followers_feed_cache(note)
    return {"message": "Note rejected ❌"}


@router.patch("/{note_id}/override-approve")
def override_approve_note(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {
            "$set": {
                "status": "approved",
                "approved_at": int(time.time()),
                "override_action": "approved",
                "override_by_role": current_user["role"],
                "override_by": current_user["id"],
            }
        },
    )
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": "override_approved",
            "reason": "override approve",
            "created_at": int(time.time()),
        }
    )
    log_audit_event("override_approve", current_user["id"], note_id, {})
    notify(
        str(note["uploader_id"]),
        "moderation",
        f"Your note '{note.get('title','')}' was override-approved.",
        f"/notes/{note_id}",
    )
    _notify_followers_about_approved_note(note_id, note)
    return {"message": "Override approved ✅"}


@router.patch("/{note_id}/override-reject")
def override_reject_note(note_id: str, data: OverrideRejectRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {
            "$set": {
                "status": "rejected",
                "rejected_reason": data.reason,
                "rejected_at": int(time.time()),
                "override_action": "rejected",
                "override_by_role": current_user["role"],
                "override_by": current_user["id"],
            }
        },
    )
    moderation_logs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "moderator_id": ObjectId(current_user["id"]),
            "action": "override_rejected",
            "reason": data.reason,
            "created_at": int(time.time()),
        }
    )
    log_audit_event("override_reject", current_user["id"], note_id, {"reason": data.reason})
    notify(
        str(note["uploader_id"]),
        "moderation",
        f"Your note '{note.get('title','')}' was override-rejected: {data.reason}",
        f"/notes/{note_id}",
    )
    _invalidate_followers_feed_cache(note)
    return {"message": "Override rejected ❌"}
