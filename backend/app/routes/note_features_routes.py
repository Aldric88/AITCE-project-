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
    users_collection,
    note_annotations_collection,
)
from app.utils.dependencies import get_current_user
from app.utils.text_extract import extract_text_from_pdf
from app.services.duplicate_service import find_near_duplicates
from app.services.pass_service import has_active_creator_pass

router = APIRouter(prefix="/notes", tags=["Note Features"])


class NoteVersionCreate(BaseModel):
    file_url: str
    changelog: str = ""


class CollaboratorAddRequest(BaseModel):
    email: str
    split_percent: float = 0.0


class AnnotationUpsertRequest(BaseModel):
    content: str
    cursor: int = 0
    source: str = "web"


def _tokenize(value: str):
    return [t for t in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(t) > 2]


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a.intersection(b)) / max(len(a.union(b)), 1)


def _owner_or_collaborator(note: dict, current_user: dict) -> bool:
    if str(note.get("uploader_id")) == current_user["id"]:
        return True
    collabs = note.get("collaborator_ids") or []
    my_oid = ObjectId(current_user["id"])
    return my_oid in collabs or current_user["id"] in [str(c) for c in collabs]


def _has_note_access(note: dict, current_user: dict) -> bool:
    if str(note.get("uploader_id")) == current_user["id"]:
        return True
    if not note.get("is_paid", False):
        return True
    note_oid = note.get("_id")
    if not note_oid:
        return False
    purchased = purchases_collection.find_one(
        {
            "note_id": note_oid,
            "$or": [
                {"buyer_id": ObjectId(current_user["id"]), "status": "success"},
                {"user_id": ObjectId(current_user["id"]), "status": {"$in": ["success", "paid", "free"]}},
            ],
        }
    )
    if purchased is not None:
        return True
    return has_active_creator_pass(current_user["id"], note.get("uploader_id"))


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


@router.get("/{note_id}/near-duplicates")
def near_duplicates(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _has_note_access(note, current_user):
        raise HTTPException(status_code=403, detail="Not allowed")

    items = find_near_duplicates(
        note_id,
        notes_collection,
        ai_reports_collection,
        threshold=0.6,
        scan_limit=500,
        top_k=25,
    )
    return {"note_id": note_id, "duplicates": items}


@router.get("/{note_id}/smart-study-pack")
def smart_study_pack(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _has_note_access(note, current_user):
        raise HTTPException(status_code=403, detail="Unlock this note first")

    ai = note.get("ai") or {}
    ai_report = ai_reports_collection.find_one({"note_id": ObjectId(note_id)}) or {}
    topics = [str(t).strip() for t in (ai.get("topics") or ai_report.get("topics") or []) if str(t).strip()]
    summary = str(ai.get("summary") or ai_report.get("summary") or "").strip()

    extracted = ""
    file_url = note.get("file_url")
    if file_url:
        upload = uploads_collection.find_one({"file_url": file_url})
        stored_name = (upload or {}).get("stored_name")
        if stored_name:
            file_path = f"uploads/private/{stored_name}"
            try:
                extracted = extract_text_from_pdf(file_path)
            except Exception:
                extracted = ""

    if not summary:
        base = extracted or f"{note.get('title', '')}. {note.get('description', '')}"
        summary = " ".join(base.split())[:700]

    top_words = Counter([t for t in _tokenize(extracted or summary) if len(t) >= 4]).most_common(8)
    key_points = [w for w, _ in top_words][:6]
    if not key_points:
        key_points = topics[:6]

    flashcards = []
    for idx, topic in enumerate((topics or key_points)[:8], start=1):
        flashcards.append(
            {
                "id": idx,
                "question": f"What is {topic} in {note.get('subject', 'this subject')}?",
                "answer": f"{topic} is a key concept from this note. Review the summary and examples for mastery.",
            }
        )

    quiz = []
    for idx, topic in enumerate((topics or key_points)[:6], start=1):
        quiz.append(
            {
                "id": idx,
                "question": f"Which option best describes {topic}?",
                "choices": [
                    f"{topic} is core to this unit",
                    f"{topic} is unrelated to this unit",
                    f"{topic} only appears in lab records",
                    f"{topic} is not covered",
                ],
                "answer_index": 0,
            }
        )

    return {
        "note_id": note_id,
        "summary": summary,
        "topics": topics[:12],
        "key_points": key_points,
        "flashcards": flashcards,
        "quiz": quiz,
    }


@router.post("/{note_id}/versions")
def add_note_version(note_id: str, data: NoteVersionCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note_oid = ObjectId(note_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _owner_or_collaborator(note, current_user) and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only collaborators can add versions")

    upload = uploads_collection.find_one({"file_url": data.file_url})
    if not upload:
        raise HTTPException(status_code=400, detail="Invalid file_url")
    if upload.get("uploader_id") != ObjectId(current_user["id"]) and current_user.get("role") != "admin":
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


@router.get("/{note_id}/collaborators")
def list_collaborators(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _owner_or_collaborator(note, current_user) and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    collabs = note.get("collaborator_ids") or []
    splits = note.get("collaborator_splits") or {}
    users = {}
    if collabs:
        for row in users_collection.find({"_id": {"$in": collabs}}, {"name": 1, "email": 1}):
            users[row["_id"]] = row
    out = []
    for collab_id in collabs:
        u = users.get(collab_id, {})
        out.append(
            {
                "user_id": str(collab_id),
                "name": u.get("name", "Collaborator"),
                "email": u.get("email"),
                "split_percent": float(splits.get(str(collab_id), 0.0)),
            }
        )
    return {"note_id": note_id, "collaborators": out}


@router.post("/{note_id}/collaborators")
def add_collaborator(note_id: str, data: CollaboratorAddRequest, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note_oid = ObjectId(note_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if str(note.get("uploader_id")) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only owner can manage collaborators")

    user = users_collection.find_one({"email": data.email.strip().lower()})
    if not user:
        raise HTTPException(status_code=404, detail="Collaborator user not found")
    if user["_id"] == note.get("uploader_id"):
        raise HTTPException(status_code=400, detail="Owner is already the primary author")

    collabs = note.get("collaborator_ids") or []
    if user["_id"] in collabs:
        raise HTTPException(status_code=400, detail="User is already a collaborator")

    split = max(0.0, min(float(data.split_percent), 100.0))
    updates = {
        "$addToSet": {"collaborator_ids": user["_id"]},
        "$set": {f"collaborator_splits.{str(user['_id'])}": split},
    }
    notes_collection.update_one({"_id": note_oid}, updates)
    return {"message": "Collaborator added ✅", "user_id": str(user["_id"]), "split_percent": split}


@router.delete("/{note_id}/collaborators/{user_id}")
def remove_collaborator(note_id: str, user_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id) or not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid id")
    note_oid = ObjectId(note_id)
    user_oid = ObjectId(user_id)
    note = notes_collection.find_one({"_id": note_oid})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if str(note.get("uploader_id")) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only owner can manage collaborators")

    notes_collection.update_one(
        {"_id": note_oid},
        {
            "$pull": {"collaborator_ids": user_oid},
            "$unset": {f"collaborator_splits.{user_id}": ""},
        },
    )
    return {"message": "Collaborator removed"}


@router.get("/{note_id}/annotations")
def get_my_annotations(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _has_note_access(note, current_user):
        raise HTTPException(status_code=403, detail="Unlock this note first")
    row = note_annotations_collection.find_one(
        {"note_id": ObjectId(note_id), "user_id": ObjectId(current_user["id"])}
    ) or {}
    return {
        "note_id": note_id,
        "content": row.get("content", ""),
        "cursor": int(row.get("cursor", 0)),
        "updated_at": row.get("updated_at"),
        "source": row.get("source", "web"),
    }


@router.put("/{note_id}/annotations")
def upsert_my_annotations(note_id: str, data: AnnotationUpsertRequest, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")
    note = notes_collection.find_one({"_id": ObjectId(note_id), "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not _has_note_access(note, current_user):
        raise HTTPException(status_code=403, detail="Unlock this note first")

    now_ts = int(time.time())
    note_annotations_collection.update_one(
        {"note_id": ObjectId(note_id), "user_id": ObjectId(current_user["id"])},
        {
            "$set": {
                "content": data.content,
                "cursor": int(data.cursor),
                "source": data.source,
                "updated_at": now_ts,
            },
            "$setOnInsert": {
                "created_at": now_ts,
            },
        },
        upsert=True,
    )
    return {"message": "Annotations synced ✅", "note_id": note_id, "updated_at": now_ts}


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
