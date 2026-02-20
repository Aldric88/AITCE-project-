import time
import re
from collections import Counter

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from pymongo.errors import OperationFailure

from app.database import (
    notes_collection,
    uploads_collection,
    note_versions_collection,
    purchases_collection,
    ai_reports_collection,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/notes", tags=["Note Features"])


class NoteVersionCreate(BaseModel):
    file_url: str
    changelog: str = ""


def _tokenize(value: str):
    return [t for t in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(t) > 2]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / max(len(a.union(b)), 1)


@router.get("/semantic-search")
def semantic_search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    try:
        cursor = notes_collection.find(
            {"status": "approved", "$text": {"$search": q}},
            {
                "title": 1,
                "subject": 1,
                "dept": 1,
                "semester": 1,
                "unit": 1,
                "is_paid": 1,
                "price": 1,
                "score": {"$meta": "textScore"},
            },
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        return [
            {
                "id": str(note["_id"]),
                "title": note.get("title", "Untitled"),
                "subject": note.get("subject", ""),
                "dept": note.get("dept", ""),
                "semester": note.get("semester"),
                "unit": note.get("unit"),
                "is_paid": note.get("is_paid", False),
                "price": note.get("price", 0),
                "score": round(float(note.get("score", 0.0)), 4),
            }
            for note in cursor
        ]
    except OperationFailure:
        # Fallback when text index is unavailable/misconfigured.
        query_tokens = set(_tokenize(q))
        rows = list(notes_collection.find({"status": "approved"}).limit(200))
        scored = []
        for note in rows:
            text = " ".join(
                [
                    str(note.get("title", "")),
                    str(note.get("description", "")),
                    str(note.get("subject", "")),
                    " ".join([str(t) for t in note.get("tags", [])]),
                ]
            )
            score = _jaccard(query_tokens, set(_tokenize(text)))
            if score > 0:
                scored.append(
                    {
                        "id": str(note["_id"]),
                        "title": note.get("title", "Untitled"),
                        "subject": note.get("subject", ""),
                        "dept": note.get("dept", ""),
                        "semester": note.get("semester"),
                        "unit": note.get("unit"),
                        "is_paid": note.get("is_paid", False),
                        "price": note.get("price", 0),
                        "score": round(score, 4),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


@router.post("/{note_id}/versions")
def add_note_version(note_id: str, data: NoteVersionCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note_oid = ObjectId(note_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if str(note.get("uploader_id")) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only owner can add version")

    upload = uploads_collection.find_one({"file_url": data.file_url})
    if not upload:
        raise HTTPException(status_code=400, detail="Invalid file_url")
    if upload.get("uploader_id") != ObjectId(current_user["id"]):
        raise HTTPException(status_code=403, detail="This upload does not belong to you")

    latest = note_versions_collection.find_one({"note_id": note_oid}, sort=[("version_no", -1)])
    version_no = int(latest.get("version_no", 0) + 1) if latest else 1
    doc = {
        "note_id": note_oid,
        "version_no": version_no,
        "file_url": data.file_url,
        "changelog": data.changelog.strip(),
        "created_by": ObjectId(current_user["id"]),
        "created_at": int(time.time()),
    }
    res = note_versions_collection.insert_one(doc)

    notes_collection.update_one(
        {"_id": note_oid},
        {
            "$set": {
                "file_url": data.file_url,
                "current_version": version_no,
                "updated_at": int(time.time()),
            }
        },
    )
    uploads_collection.update_one({"_id": upload["_id"]}, {"$set": {"is_linked": True, "linked_note_id": note_oid}})
    return {"id": str(res.inserted_id), "version_no": version_no, "message": "Version added ✅"}


@router.get("/{note_id}/versions")
def list_note_versions(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note_oid = ObjectId(note_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    rows = list(note_versions_collection.find({"note_id": note_oid}).sort("version_no", -1))
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "version_no": r.get("version_no", 1),
                "file_url": r.get("file_url"),
                "changelog": r.get("changelog", ""),
                "created_at": r.get("created_at"),
            }
        )
    return out


@router.get("/{note_id}/confidence")
def note_confidence(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note_oid = ObjectId(note_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    verified_buyers = purchases_collection.count_documents({"note_id": note_oid, "status": "success"})
    ai = note.get("ai") or {}
    quality_score = float(ai.get("quality_score", 0.0))
    relevance_score = float(ai.get("relevance_score", 0.0))
    report = ai_reports_collection.find_one({"note_id": note_oid}) or {}
    issues = report.get("critical_issues", []) or []
    warnings = report.get("warnings", []) or []

    # duplicate indicator via repeated file hash across notes
    duplicate_count = 0
    file_url = note.get("file_url")
    if file_url:
        upload = uploads_collection.find_one({"file_url": file_url})
        file_hash = (upload or {}).get("file_hash")
        if file_hash:
            hash_urls = [u.get("file_url") for u in uploads_collection.find({"file_hash": file_hash}, {"file_url": 1})]
            if hash_urls:
                duplicate_count = notes_collection.count_documents({"file_url": {"$in": hash_urls}})
                duplicate_count = max(duplicate_count - 1, 0)

    confidence_score = int(
        min(
            100,
            max(
                0,
                (quality_score * 45)
                + (relevance_score * 30)
                + min(verified_buyers * 2, 20)
                - min(len(issues) * 10, 20)
                - min(duplicate_count * 8, 16),
            ),
        )
    )

    badge = "high" if confidence_score >= 75 else "medium" if confidence_score >= 45 else "low"
    return {
        "confidence_score": confidence_score,
        "badge": badge,
        "verified_buyers": verified_buyers,
        "quality_score": round(quality_score, 3),
        "relevance_score": round(relevance_score, 3),
        "duplicate_count": duplicate_count,
        "critical_issues": issues[:3],
        "warnings": warnings[:3],
    }
