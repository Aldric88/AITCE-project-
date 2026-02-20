import time
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import (
    notes_collection,
    ai_reports_collection,
    moderation_rules_collection,
    moderation_appeals_collection,
    moderation_logs_collection,
    users_collection,
    audit_events_collection,
    revalidation_jobs_collection,
)
from app.utils.dependencies import get_current_user, require_role
from app.utils.notify import notify
from app.utils.audit import log_audit_event
from app.utils.text_extract import extract_text_from_pdf
from app.utils.seller_trust import calculate_seller_trust_level


router = APIRouter(prefix="/moderation/features", tags=["Moderation Features"])


DEFAULT_RULES = {
    "config_name": "default",
    "auto_approve_max_risk": 20,
    "auto_reject_min_risk": 70,
    "quality_gate_paid_min_quality": 0.55,
    "revalidate_after_days": 14,
    "max_batch_size": 50,
    "updated_at": 0,
}


class RulesUpdateRequest(BaseModel):
    auto_approve_max_risk: int = Field(ge=0, le=100)
    auto_reject_min_risk: int = Field(ge=0, le=100)
    quality_gate_paid_min_quality: float = Field(ge=0.0, le=1.0)
    revalidate_after_days: int = Field(ge=1, le=365)
    max_batch_size: int = Field(ge=1, le=200)


class BatchAIRequest(BaseModel):
    note_ids: list[str] = Field(default_factory=list)
    force: bool = False


class BatchDecisionRequest(BaseModel):
    note_ids: list[str]
    action: Literal["approve", "reject"]
    reason: str = "Batch moderation decision"


class AppealCreateRequest(BaseModel):
    message: str = Field(min_length=10, max_length=2000)


class AppealResolveRequest(BaseModel):
    status: Literal["accepted", "rejected"]
    moderator_note: str = Field(min_length=3, max_length=1000)


class RevalidateRunRequest(BaseModel):
    run_now: bool = True
    limit: int = Field(default=25, ge=1, le=100)


def _get_rules():
    rules = moderation_rules_collection.find_one({"config_name": "default"})
    if rules:
        rules.pop("_id", None)
        return rules
    seed = dict(DEFAULT_RULES)
    seed["updated_at"] = int(time.time())
    moderation_rules_collection.insert_one(seed)
    return seed


def _note_quality_score(note_doc: dict) -> float:
    ai = note_doc.get("ai") or {}
    return float(ai.get("quality_score", 0.0))


@router.get("/rules")
def get_rules(current_user=Depends(require_role(["admin", "moderator"]))):
    return _get_rules()


@router.patch("/rules")
def update_rules(data: RulesUpdateRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    payload = data.model_dump()
    payload["config_name"] = "default"
    payload["updated_at"] = int(time.time())
    moderation_rules_collection.update_one(
        {"config_name": "default"},
        {"$set": payload},
        upsert=True,
    )
    log_audit_event("rules_updated", current_user["id"], None, payload)
    return {"message": "Moderation rules updated", "rules": payload}


@router.get("/queue")
def conflict_aware_queue(
    current_user=Depends(require_role(["admin", "moderator"])),
    limit: int = Query(default=50, ge=1, le=200),
):
    notes = list(notes_collection.find({"status": "pending"}).sort("_id", -1).limit(limit))
    items = []
    for note in notes:
        report = ai_reports_collection.find_one({"note_id": note["_id"]}) or {}
        rs = report.get("report_status", {})
        risk = int(rs.get("risk_score", 50))
        content_valid = bool(report.get("content_valid", False))
        subject_match = bool(report.get("subject_match", False))
        title_match = bool(report.get("title_match", False))
        is_spam = bool(report.get("is_spam", False))
        critical_count = len(report.get("critical_issues", []) or [])
        conflict_score = 0
        if content_valid and (not subject_match or not title_match):
            conflict_score += 40
        if (not is_spam) and critical_count > 0:
            conflict_score += 35
        if risk >= 70 and content_valid:
            conflict_score += 25
        priority = risk + conflict_score
        items.append(
            {
                "note_id": str(note["_id"]),
                "title": note.get("title", ""),
                "risk_score": risk,
                "conflict_score": conflict_score,
                "priority": priority,
                "moderation_bucket": rs.get("moderation_bucket", "needs_moderator_review"),
            }
        )
    items.sort(key=lambda x: x["priority"], reverse=True)
    return {"count": len(items), "items": items}


@router.post("/batch/run-ai")
def batch_run_ai(data: BatchAIRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    rules = _get_rules()
    max_batch = int(rules.get("max_batch_size", 50))
    ids = data.note_ids[:max_batch] if data.note_ids else [
        str(n["_id"]) for n in notes_collection.find({"status": "pending"}).sort("_id", -1).limit(max_batch)
    ]
    from app.routes.ai_routes import analyze_note  # local import to avoid circular at module load

    results = []
    for nid in ids:
        try:
            res = analyze_note(nid, force=data.force, current_user=current_user)
            results.append({"note_id": nid, "ok": True, "bucket": res.get("moderation_bucket")})
        except Exception as exc:  # keep batch running
            results.append({"note_id": nid, "ok": False, "error": str(exc)})
    log_audit_event("batch_run_ai", current_user["id"], None, {"count": len(ids), "force": data.force})
    return {"processed": len(results), "results": results}


@router.post("/batch/decision")
def batch_decision(data: BatchDecisionRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    rules = _get_rules()
    if len(data.note_ids) > int(rules.get("max_batch_size", 50)):
        raise HTTPException(status_code=400, detail="Batch too large for current rules")

    changed = []
    for nid in data.note_ids:
        if not ObjectId.is_valid(nid):
            continue
        note = notes_collection.find_one({"_id": ObjectId(nid)})
        if not note:
            continue
        if data.action == "approve" and note.get("is_paid"):
            if _note_quality_score(note) < float(rules.get("quality_gate_paid_min_quality", 0.55)):
                continue
        new_status = "approved" if data.action == "approve" else "rejected"
        update = {"status": new_status}
        if new_status == "approved":
            update["approved_at"] = int(time.time())
        else:
            update["rejected_at"] = int(time.time())
            update["rejected_reason"] = data.reason
        notes_collection.update_one({"_id": ObjectId(nid)}, {"$set": update})
        moderation_logs_collection.insert_one(
            {
                "note_id": ObjectId(nid),
                "moderator_id": ObjectId(current_user["id"]),
                "action": new_status,
                "reason": data.reason,
                "created_at": int(time.time()),
            }
        )
        log_audit_event("batch_decision_item", current_user["id"], nid, {"action": new_status, "reason": data.reason})
        changed.append(nid)
    return {"changed_count": len(changed), "changed_note_ids": changed}


@router.get("/diff/{note_id}")
def note_diff_view(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    upload = None
    if note.get("file_url"):
        from app.database import uploads_collection

        upload = uploads_collection.find_one({"file_url": note["file_url"]})
    text = ""
    if upload and upload.get("stored_name"):
        for p in (f"uploads/private/{upload['stored_name']}", f"uploads/{upload['stored_name']}"):
            text = extract_text_from_pdf(p) if p.endswith(".pdf") else ""
            if text:
                break
    snippet = (text or "")[:1200]
    metadata_tokens = [note.get("title", ""), note.get("subject", ""), note.get("description", "")]
    highlights = [t for s in metadata_tokens for t in s.split() if len(t) > 3 and t.lower() in snippet.lower()][:40]
    return {
        "note_id": note_id,
        "metadata": {
            "title": note.get("title"),
            "description": note.get("description"),
            "subject": note.get("subject"),
            "tags": note.get("tags", []),
        },
        "content_snippet": snippet,
        "matched_tokens": highlights,
    }


@router.post("/appeals/{note_id}")
def create_appeal(note_id: str, data: AppealCreateRequest, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if str(note.get("uploader_id")) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only note owner can appeal")
    if note.get("status") != "rejected":
        raise HTTPException(status_code=400, detail="Appeal allowed only for rejected notes")
    appeal = {
        "note_id": ObjectId(note_id),
        "creator_id": ObjectId(current_user["id"]),
        "message": data.message,
        "status": "open",
        "created_at": int(time.time()),
    }
    result = moderation_appeals_collection.insert_one(appeal)
    log_audit_event("appeal_created", current_user["id"], note_id, {"appeal_id": str(result.inserted_id)})
    # notify moderators
    moderators = users_collection.find({"role": {"$in": ["admin", "moderator"]}})
    for m in moderators:
        notify(str(m["_id"]), "appeal", f"New appeal for note: {note.get('title','')}", f"/moderation-dashboard")
    return {"message": "Appeal submitted", "appeal_id": str(result.inserted_id)}


@router.get("/appeals")
def list_appeals(
    status: Optional[str] = Query(default=None),
    current_user=Depends(require_role(["admin", "moderator"])),
):
    query = {}
    if status:
        query["status"] = status
    appeals = list(moderation_appeals_collection.find(query).sort("_id", -1))
    out = []
    for a in appeals:
        note = notes_collection.find_one({"_id": a["note_id"]})
        out.append(
            {
                "id": str(a["_id"]),
                "note_id": str(a["note_id"]),
                "note_title": (note or {}).get("title"),
                "status": a.get("status"),
                "message": a.get("message"),
                "moderator_note": a.get("moderator_note"),
                "created_at": a.get("created_at"),
            }
        )
    return out


@router.patch("/appeals/{appeal_id}/resolve")
def resolve_appeal(appeal_id: str, data: AppealResolveRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(appeal_id):
        raise HTTPException(status_code=400, detail="Invalid appeal id")
    appeal = moderation_appeals_collection.find_one({"_id": ObjectId(appeal_id)})
    if not appeal:
        raise HTTPException(status_code=404, detail="Appeal not found")
    update = {
        "status": data.status,
        "moderator_note": data.moderator_note,
        "resolved_by": ObjectId(current_user["id"]),
        "resolved_at": int(time.time()),
    }
    moderation_appeals_collection.update_one({"_id": ObjectId(appeal_id)}, {"$set": update})
    if data.status == "accepted":
        notes_collection.update_one(
            {"_id": appeal["note_id"]},
            {"$set": {"status": "pending", "appeal_reopened_at": int(time.time())}},
        )
    notify(str(appeal["creator_id"]), "appeal", f"Your appeal was {data.status}.", "/my-uploads")
    log_audit_event("appeal_resolved", current_user["id"], str(appeal["note_id"]), {"status": data.status})
    return {"message": f"Appeal {data.status}"}


@router.get("/confidence-trend")
def confidence_trend(days: int = Query(default=14, ge=1, le=180), current_user=Depends(require_role(["admin", "moderator"]))):
    cutoff = int(time.time()) - days * 24 * 3600
    reports = list(ai_reports_collection.find({"analysis_info.analyzed_at": {"$gte": cutoff}}))
    by_day = defaultdict(lambda: {"total": 0, "valid": 0, "avg_risk": 0.0})
    for r in reports:
        ts = r.get("analysis_info", {}).get("analyzed_at", cutoff)
        day = time.strftime("%Y-%m-%d", time.localtime(ts))
        by_day[day]["total"] += 1
        if r.get("report_status", {}).get("validation_success"):
            by_day[day]["valid"] += 1
        by_day[day]["avg_risk"] += float(r.get("report_status", {}).get("risk_score", 50))
    points = []
    for day, v in sorted(by_day.items()):
        total = v["total"] or 1
        points.append(
            {
                "day": day,
                "total": v["total"],
                "valid_rate": round(v["valid"] / total, 3),
                "avg_risk": round(v["avg_risk"] / total, 2),
            }
        )
    return {"days": days, "points": points}


@router.get("/duplicates/{note_id}")
def find_duplicates(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    target = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not target:
        raise HTTPException(status_code=404, detail="Note not found")
    target_text = (target.get("title", "") + " " + (target.get("description") or "")).lower()
    report = ai_reports_collection.find_one({"note_id": ObjectId(note_id)}) or {}
    if report.get("summary"):
        target_text += " " + report.get("summary", "").lower()

    sims = []
    others = notes_collection.find({"_id": {"$ne": ObjectId(note_id)}, "status": {"$in": ["pending", "approved"]}}).limit(300)
    for other in others:
        other_text = (other.get("title", "") + " " + (other.get("description") or "")).lower()
        other_report = ai_reports_collection.find_one({"note_id": other["_id"]}) or {}
        if other_report.get("summary"):
            other_text += " " + other_report.get("summary", "").lower()
        score = SequenceMatcher(a=target_text[:2000], b=other_text[:2000]).ratio()
        if score >= 0.72:
            sims.append({"note_id": str(other["_id"]), "title": other.get("title"), "similarity": round(score, 3)})
    sims.sort(key=lambda x: x["similarity"], reverse=True)
    return {"note_id": note_id, "duplicates": sims[:20]}


@router.post("/suggest-tags/{note_id}")
def suggest_tags(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    report = ai_reports_collection.find_one({"note_id": ObjectId(note_id)}) or {}
    topics = [t for t in (report.get("topics") or []) if isinstance(t, str)]
    suggestions = list(dict.fromkeys([t.lower().strip() for t in topics if len(t.strip()) >= 3]))[:8]
    base = [str(note.get("subject", "")).lower(), str(note.get("dept", "")).lower()]
    for b in base:
        if b and b not in suggestions:
            suggestions.append(b)
    return {"note_id": note_id, "current_tags": note.get("tags", []), "suggested_tags": suggestions[:10]}


@router.get("/creator-trust/{creator_id}")
def creator_trust(creator_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(creator_id):
        raise HTTPException(status_code=400, detail="Invalid creator id")
    trust = calculate_seller_trust_level(ObjectId(creator_id), None)
    reports = list(
        ai_reports_collection.aggregate(
            [
                {"$match": {"note_info.note_uploader_id": ObjectId(creator_id)}},
                {"$group": {"_id": None, "avg_risk": {"$avg": "$report_status.risk_score"}, "count": {"$sum": 1}}},
            ]
        )
    )
    quality = reports[0] if reports else {"avg_risk": 50, "count": 0}
    trust["avg_ai_risk"] = round(float(quality.get("avg_risk", 50)), 2)
    trust["analyzed_notes"] = int(quality.get("count", 0))
    return trust


@router.get("/analytics")
def moderation_analytics(days: int = Query(default=30, ge=1, le=365), current_user=Depends(require_role(["admin", "moderator"]))):
    cutoff = int(time.time()) - days * 24 * 3600
    pending_count = notes_collection.count_documents({"status": "pending"})
    approved_count = notes_collection.count_documents({"status": "approved", "approved_at": {"$gte": cutoff}})
    rejected_count = notes_collection.count_documents({"status": "rejected", "rejected_at": {"$gte": cutoff}})
    open_appeals = moderation_appeals_collection.count_documents({"status": "open"})
    ai_total = ai_reports_collection.count_documents({"analysis_info.analyzed_at": {"$gte": cutoff}})
    ai_valid = ai_reports_collection.count_documents({"analysis_info.analyzed_at": {"$gte": cutoff}, "report_status.validation_success": True})
    return {
        "days": days,
        "queue": {"pending": pending_count, "open_appeals": open_appeals},
        "decisions": {"approved": approved_count, "rejected": rejected_count},
        "ai": {
            "total": ai_total,
            "valid_rate": round((ai_valid / ai_total), 3) if ai_total else 0.0,
        },
    }


@router.post("/revalidate/run")
def revalidate_run(data: RevalidateRunRequest, current_user=Depends(require_role(["admin", "moderator"]))):
    rules = _get_rules()
    cutoff = int(time.time()) - int(rules.get("revalidate_after_days", 14)) * 24 * 3600
    targets = list(
        ai_reports_collection.find({"analysis_info.analyzed_at": {"$lte": cutoff}}).sort("analysis_info.analyzed_at", 1).limit(data.limit)
    )
    job_doc = {
        "status": "completed" if data.run_now else "scheduled",
        "created_at": int(time.time()),
        "requested_by": ObjectId(current_user["id"]),
        "target_count": len(targets),
    }
    revalidation_jobs_collection.insert_one(job_doc)
    rerun = []
    if data.run_now and targets:
        from app.routes.ai_routes import analyze_note

        for r in targets:
            nid = str(r.get("note_id"))
            try:
                analyze_note(nid, force=True, current_user=current_user)
                rerun.append({"note_id": nid, "ok": True})
            except Exception as exc:
                rerun.append({"note_id": nid, "ok": False, "error": str(exc)})
    log_audit_event("revalidation_run", current_user["id"], None, {"count": len(targets), "run_now": data.run_now})
    return {"scheduled_targets": len(targets), "results": rerun}


@router.get("/timeline/{note_id}")
def timeline(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    oid = ObjectId(note_id)
    events = []
    for log in moderation_logs_collection.find({"note_id": oid}):
        events.append({"ts": log.get("created_at", 0), "type": "moderation_log", "payload": {"action": log.get("action"), "reason": log.get("reason")}})
    for a in moderation_appeals_collection.find({"note_id": oid}):
        events.append({"ts": a.get("created_at", 0), "type": "appeal_created", "payload": {"status": a.get("status"), "message": a.get("message")}})
        if a.get("resolved_at"):
            events.append({"ts": a.get("resolved_at", 0), "type": "appeal_resolved", "payload": {"status": a.get("status"), "moderator_note": a.get("moderator_note")}})
    report = ai_reports_collection.find_one({"note_id": oid})
    if report:
        ts = report.get("analysis_info", {}).get("analyzed_at", 0)
        events.append(
            {
                "ts": ts,
                "type": "ai_analysis",
                "payload": {
                    "provider": report.get("analysis_info", {}).get("api_provider"),
                    "risk_score": report.get("report_status", {}).get("risk_score"),
                    "bucket": report.get("report_status", {}).get("moderation_bucket"),
                },
            }
        )
    for ev in audit_events_collection.find({"note_id": oid}):
        events.append({"ts": ev.get("created_at", 0), "type": ev.get("event_type"), "payload": ev.get("payload", {})})
    events.sort(key=lambda x: x["ts"], reverse=True)
    return {"note_id": note_id, "events": events}


@router.get("/explain/{note_id}")
def explain_flag(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    report = ai_reports_collection.find_one({"note_id": ObjectId(note_id)})
    if not report:
        raise HTTPException(status_code=404, detail="AI report not found")
    status = report.get("report_status", {})
    reasons = report.get("critical_issues", []) or report.get("warnings", [])
    if not reasons:
        reasons = ["No major issues found; classification driven by aggregate risk."]
    text = (
        f"Provider {report.get('analysis_info', {}).get('api_provider', 'rules')} assigned risk "
        f"{status.get('risk_score', 50)} and bucket {status.get('moderation_bucket', 'needs_moderator_review')}. "
        f"Top reasons: {'; '.join(reasons[:3])}"
    )
    return {"note_id": note_id, "explanation": text, "reasons": reasons[:10]}


@router.get("/quality-gate/check/{note_id}")
def quality_gate_check(note_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    rules = _get_rules()
    if not note.get("is_paid", False):
        return {"note_id": note_id, "passed": True, "reason": "Note is free"}
    quality = _note_quality_score(note)
    minimum = float(rules.get("quality_gate_paid_min_quality", 0.55))
    passed = quality >= minimum
    return {
        "note_id": note_id,
        "passed": passed,
        "quality_score": quality,
        "minimum_required": minimum,
        "reason": "Quality score meets threshold" if passed else "Quality score below threshold for paid notes",
    }
