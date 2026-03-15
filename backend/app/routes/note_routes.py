import os
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from typing import Optional

from app.database import (
    notes_collection,
    uploads_collection,
    purchases_collection,
    users_collection,
)
from app.schemas.note_schema import NoteCreate, NoteUpdate
from app.models.note_model import note_helper
from app.utils.dependencies import get_current_user, get_optional_current_user, require_email_verified
from app.utils.rate_limiter import search_limiter
from app.services.ai_pipeline import enqueue_note_ai_analysis
from app.utils.cache import cache_get_json, cache_set_json
from app.utils.observability import log_if_slow
from app.services.risk_service import compute_user_risk_score
from app.services.feed_pipeline import (
    append_trust_lookups,
    append_trust_fields,
    append_access_fields,
)
from app.database import reports_collection, disputes_collection, requests_collection
from app.services.points_service import award_points
from app.config import settings

router = APIRouter(prefix="/notes", tags=["Notes"])
logger = logging.getLogger(__name__)


def _safe_object_id(value):
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return None


# Student uploads note (always pending) — requires verified college email
@router.post("/")
def create_note(note: NoteCreate, current_user=Depends(require_email_verified)):
    new_note = note.model_dump()
    uploader_id = ObjectId(current_user["id"])

    risk = compute_user_risk_score(
        current_user["id"],
        {
            "users_collection": users_collection,
            "notes_collection": notes_collection,
            "reports_collection": reports_collection,
            "disputes_collection": disputes_collection,
            "requests_collection": requests_collection,
            "purchases_collection": purchases_collection,
        },
    )
    if risk["risk_score"] >= 90:
        raise HTTPException(status_code=403, detail="Account risk too high. Contact support.")

    if not current_user.get("is_email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email to upload notes")

    # ✅ Pricing validation
    if new_note.get("is_paid"):
        if new_note.get("price") is None:
            raise HTTPException(status_code=400, detail="Price required for paid notes")

        if new_note.get("price") < 1:
            raise HTTPException(status_code=400, detail="Price must be at least ₹1")

        if new_note.get("price") > 150:
            raise HTTPException(status_code=400, detail="Max price allowed is ₹150")
    else:
        new_note["price"] = 0

    # ✅ only verified sellers can post paid notes
    if new_note.get("is_paid") is True:
        if current_user.get("verified_seller") is not True:
            raise HTTPException(
                status_code=403,
                detail="Only verified sellers can upload paid notes"
            )

    # uploader info
    new_note["uploader_id"] = uploader_id
    new_note["status"] = "pending"
    new_note["ai"] = None  # AI analysis field
    
    # ✅ Cluster assignment (Trust Architecture)
    current_cluster_id = _safe_object_id(current_user.get("cluster_id"))
    if current_cluster_id:
        new_note["cluster_id"] = current_cluster_id
    else:
        # If user has no cluster (manual user?), explicitly set None or handle logic
        # For now, allow but maybe flag?
        new_note["cluster_id"] = None

    collaborator_ids: list[ObjectId] = []
    collaborator_splits: dict[str, float] = {}
    split_total = 0.0
    for collab in note.collaborators:
        email = collab.email.strip().lower()
        if email == current_user["email"].strip().lower():
            continue
        user = users_collection.find_one({"email": email}, {"_id": 1})
        if not user:
            raise HTTPException(status_code=400, detail=f"Collaborator not found: {email}")
        user_id = user["_id"]
        if user_id in collaborator_ids:
            continue
        collaborator_ids.append(user_id)
        split_value = round(float(collab.split_percent), 2)
        if split_value > 0:
            collaborator_splits[str(user_id)] = split_value
            split_total += split_value
    if collaborator_ids and split_total == 0:
        raise HTTPException(status_code=400, detail="Collaborator split total must be greater than 0%")
    if split_total > 95:
        raise HTTPException(status_code=400, detail="Collaborator split total must be <= 95%")
    if collaborator_ids:
        new_note["collaborator_ids"] = collaborator_ids
        new_note["collaborator_splits"] = collaborator_splits
        new_note["owner_split_percent"] = round(100.0 - split_total, 2)
    new_note.pop("collaborators", None)

    # validate note type requirements
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        if not note.file_url:
            raise HTTPException(
                status_code=400,
                detail="file_url is required for this note_type",
            )

        # SECURITY: file_url must exist in uploads collection
        upload_doc = uploads_collection.find_one({"file_url": note.file_url})
        if not upload_doc:
            raise HTTPException(
                status_code=400,
                detail="Invalid file_url (file not found). Upload the file first.",
            )

        # SECURITY: file must belong to same user
        if upload_doc["uploader_id"] != uploader_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to use this file_url (not your upload).",
            )

        # SECURITY: prevent reusing same uploaded file in multiple notes
        if upload_doc.get("is_linked") is True:
            raise HTTPException(
                status_code=400,
                detail="This file is already linked to another note.",
            )

    elif note.note_type == "link":
        if not note.external_link:
            raise HTTPException(
                status_code=400,
                detail="external_link is required for link note_type",
            )

    elif note.note_type == "text":
        pass

    else:
        raise HTTPException(status_code=400, detail="Invalid note_type")

    # insert note
    result = notes_collection.insert_one(new_note)
    saved_note = notes_collection.find_one({"_id": result.inserted_id})

    if settings.NOTE_PUBLISH_POINTS > 0:
        try:
            award_points(
                user_id=uploader_id,
                points=settings.NOTE_PUBLISH_POINTS,
                reason="note_publish_initiated",
                meta={"note_id": str(result.inserted_id)},
            )
        except Exception:
            logger.exception("Failed to award note publish points")

    # mark upload as linked to this note (only for file-based notes)
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        uploads_collection.update_one(
            {"file_url": note.file_url},
            {"$set": {"is_linked": True, "linked_note_id": saved_note["_id"]}},
        )

    file_url = new_note.get("file_url")
    if file_url:
        enqueue_note_ai_analysis(
            note_id=str(result.inserted_id),
            file_url=file_url,
            meta={
                "title": new_note.get("title"),
                "subject": new_note.get("subject"),
                "dept": new_note.get("dept"),
                "unit": new_note.get("unit"),
            },
        )

    return note_helper(saved_note)


# Approved notes feed (public but cluster-aware)
@router.get("/")
def get_approved_notes(
    dept: Optional[str] = Query(default=None),
    semester: Optional[int] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    exam_tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    cluster_id: Optional[str] = Query(default=None), 
    sort: Optional[str] = Query(default="newest", pattern="^(newest|oldest|downloads|views|rating|price_high|price_low|free_first)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user = Depends(get_optional_current_user),
    _ = Depends(search_limiter)
):
    query = {"status": "approved"}

    current_cluster_id = _safe_object_id((current_user or {}).get("cluster_id"))
    if current_cluster_id:
        # Include notes from the user's cluster OR notes with no cluster (uploaded by admins/manual users)
        query["$or"] = [{"cluster_id": current_cluster_id}, {"cluster_id": None}, {"cluster_id": {"$exists": False}}]
    elif cluster_id and ObjectId.is_valid(cluster_id):
        query["cluster_id"] = ObjectId(cluster_id)
    
    if dept:
        query["dept"] = dept
    if semester:
        query["semester"] = semester
    if subject:
        query["subject"] = {"$regex": subject, "$options": "i"} 
    if exam_tag:
        query["exam_tag"] = exam_tag
    text_score_needed = False
    if search:
        search_term = search.strip()
        if search_term:
            query["$text"] = {"$search": search_term}
            text_score_needed = True
    
    pipeline = [{"$match": query}]
    append_trust_lookups(pipeline, include_college=True)
    append_trust_fields(pipeline, include_college=True)
    
    if text_score_needed:
        pipeline.append({"$addFields": {"_text_score": {"$meta": "textScore"}}})

    # Sort
    if sort == "newest":
        pipeline.append({"$sort": {"_id": -1}})
    elif sort == "oldest":
        pipeline.append({"$sort": {"_id": 1}})
    elif sort == "downloads":
        pipeline.append({"$sort": {"downloads": -1}})
    elif sort == "views":
        pipeline.append({"$sort": {"views": -1}})
    elif sort == "rating":
        pipeline.append({"$sort": {"avg_rating": -1}})
    elif sort == "price_high":
        pipeline.append({"$sort": {"price": -1}})
    elif sort == "price_low":
        pipeline.append({"$sort": {"price": 1}})
    elif sort == "free_first":
        pipeline.append({"$sort": {"price": 1}})
    if text_score_needed:
        pipeline.append({"$sort": {"_text_score": -1, "_id": -1}})
    
    append_access_fields(
        pipeline,
        ObjectId(current_user["id"]) if current_user else None,
    )
    
    # Pagination
    pipeline.append({"$skip": skip})
    pipeline.append({"$limit": limit})
    
    started = time.time()
    notes = list(notes_collection.aggregate(pipeline))
    log_if_slow(
        logger,
        "notes.feed.aggregate",
        started,
        result_count=len(notes),
        skip=skip,
        limit=limit,
        sort=sort,
    )
    return [note_helper(n) for n in notes]


# My uploaded notes
@router.get("/my")
def my_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"])}
    ).sort("_id", -1).skip(skip).limit(limit)
    return [note_helper(n) for n in notes]


@router.get("/my-uploads")
def my_notes_alias(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"])}
    ).sort("_id", -1).skip(skip).limit(limit)
    return [note_helper(n) for n in notes]


# Student-accessible: own rejected notes (no admin required)
@router.get("/my/rejected")
def my_rejected_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"]), "status": "rejected"}
    ).sort("_id", -1).skip(skip).limit(limit)
    return [note_helper(n) for n in notes]


# Student-accessible: own pending notes
@router.get("/my/pending")
def my_pending_notes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"]), "status": "pending"}
    ).sort("_id", -1).skip(skip).limit(limit)
    return [note_helper(n) for n in notes]


# Edit note metadata (owner only)
@router.patch("/{note_id}")
def update_note(
    note_id: str,
    data: NoteUpdate,
    current_user=Depends(get_current_user),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    is_owner = str(note["uploader_id"]) == current_user["id"]
    collab_ids = note.get("collaborator_ids") or []
    is_collaborator = ObjectId(current_user["id"]) in collab_ids or current_user["id"] in [str(c) for c in collab_ids]
    if not is_owner and not is_collaborator:
        raise HTTPException(
            status_code=403, detail="You can only edit notes you collaborate on"
        )
        
    # ABAC: Prevent "Bait & Switch". Approved notes cannot be edited by students.
    if note.get("status") == "approved" and current_user.get("role") != "admin":
         raise HTTPException(
            status_code=403, detail="Approved notes cannot be edited. Contact admin."
        )

    updates = {k: v for k, v in data.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=400, detail="No fields provided to update"
        )

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": updates},
    )

    updated = notes_collection.find_one({"_id": ObjectId(note_id)})
    return note_helper(updated)


# Delete note + unlink upload, remove file from disk (owner or admin)
@router.delete("/{note_id}")
def delete_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only owner OR admin can delete
    if str(note["uploader_id"]) != current_user["id"] and current_user[
        "role"
    ] != "admin":
        raise HTTPException(
            status_code=403, detail="Not allowed to delete this note"
        )

    # unlink upload and remove file if it is file-based
    file_url = note.get("file_url")
    if file_url:
        upload_doc = uploads_collection.find_one({"file_url": file_url})

        if upload_doc:
            # unlink in DB
            uploads_collection.update_one(
                {"file_url": file_url},
                {"$set": {"is_linked": False, "linked_note_id": None}},
            )

            # delete actual file from disk
            stored_name = upload_doc.get("stored_name")
            if stored_name:
                local_path = os.path.join("uploads", stored_name)
                if os.path.exists(local_path):
                    os.remove(local_path)

            # delete upload record
            uploads_collection.delete_one({"file_url": file_url})

    # delete the note
    notes_collection.delete_one({"_id": ObjectId(note_id)})

    return {"message": "Note deleted successfully ✅", "note_id": note_id}


@router.get("/{note_id}/details")
def note_details(note_id: str, current_user=Depends(get_optional_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    pipeline = [{"$match": {"_id": ObjectId(note_id), "status": "approved"}}]
    append_trust_lookups(pipeline, include_college=True)
    append_trust_fields(pipeline, include_college=True)
    append_access_fields(
        pipeline,
        ObjectId(current_user["id"]) if current_user else None,
    )

    notes = list(notes_collection.aggregate(pipeline))
    if not notes:
        raise HTTPException(status_code=404, detail="Note not found")

    # Increment views only after the note is confirmed visible.
    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$inc": {"views": 1}},
    )

    return note_helper(notes[0])


@router.get("/trending")
def trending_notes(current_user=Depends(get_optional_current_user)):
    cache_user_scope = current_user.get("cluster_id") if current_user else "public"
    cache_key = f"notes:trending:{cache_user_scope}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    # Security: Filter by cluster
    query = {"status": "approved"}
    
    current_cluster_id = _safe_object_id((current_user or {}).get("cluster_id"))
    if current_cluster_id:
        query["$or"] = [{"cluster_id": current_cluster_id}, {"cluster_id": None}, {"cluster_id": {"$exists": False}}]

    pipeline = [{"$match": query}]
    append_trust_lookups(pipeline, include_college=True)
    append_trust_fields(pipeline, include_college=True)
    append_access_fields(
        pipeline,
        ObjectId(current_user["id"]) if current_user else None,
    )

    pipeline.append({"$sort": {"views": -1}})
    pipeline.append({"$limit": 20})

    notes = list(notes_collection.aggregate(pipeline))
    result = [note_helper(n) for n in notes]
    cache_set_json(cache_key, result, ttl=120)
    return result
