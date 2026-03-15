import os
import time
import logging
import fitz  # PyMuPDF
from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.database import notes_collection, ai_reports_collection, uploads_collection
from app.utils.dependencies import get_current_user
from app.utils.notify import notify
from app.utils.audit import log_audit_event
from app.services.hybrid_moderation import (
    analyze_with_hybrid_fallback,
    detect_personal_info,
)
from app.config import settings

router = APIRouter(prefix="/ai", tags=["AI Moderation (Gemini)"])
logger = logging.getLogger(__name__)


def _model_for_provider(provider: str) -> str:
    provider = (provider or "rules").lower()
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if provider == "ollama":
        return os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    if provider == "cached":
        return "cached"
    return "rules"


# ✅ helper: extract text from first few pages
def extract_text_from_pdf(path: str, max_pages: int = 3) -> str:
    doc = fitz.open(path)
    pages = min(doc.page_count, max_pages)

    text = []
    for i in range(pages):
        page = doc.load_page(i)
        text.append(page.get_text("text"))

    doc.close()
    return "\n".join(text).strip()


@router.post("/analyze/{note_id}")
def analyze_note(note_id: str, force: bool = False, current_user=Depends(get_current_user)):
    # ✅ Only admin/moderator can run AI
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    file_url = note.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="No file attached")

    upload_doc = uploads_collection.find_one({"file_url": file_url})
    if not upload_doc:
        raise HTTPException(status_code=404, detail="Uploaded file record not found")

    stored_name = upload_doc.get("stored_name")
    if not stored_name:
        raise HTTPException(status_code=500, detail="File metadata corrupted")

    file_path = os.path.join("uploads/private", stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    extracted_text = ""
    if str(file_path).lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path, max_pages=3)

    if not extracted_text:
        extracted_text = "No text extracted (maybe scanned PDF)."

    personal_info = detect_personal_info(extracted_text)
    file_hash = upload_doc.get("file_hash")

    # ✅ Get note metadata for validation
    title = note.get("title", "")
    description = note.get("description", "")
    subject = note.get("subject", "")
    tags = note.get("tags", [])
    dept = note.get("dept", "")
    unit = note.get("unit", "")

    meta_payload = {
        "title": title,
        "description": description,
        "subject": subject,
        "tags": tags,
        "dept": dept,
        "unit": unit,
    }

    # Reuse previous AI result by file hash to avoid paying/rerunning repeatedly.
    if file_hash and not force:
        cached = ai_reports_collection.find_one(
            {
                "file_hash": file_hash,
                "analysis_version": 2,
                "report_status.validation_success": {"$exists": True},
            },
            sort=[("analysis_info.analyzed_at", -1)],
        )
        if cached:
            result = cached.get("report", {}) or {
                "content_valid": cached.get("content_valid", False),
                "title_match": cached.get("title_match", False),
                "description_match": cached.get("description_match", False),
                "subject_match": cached.get("subject_match", False),
                "tags_relevance": cached.get("tags_relevance", False),
                "spam_score": cached.get("spam_score", 0),
                "is_spam": cached.get("is_spam", False),
                "is_relevant": cached.get("is_relevant", True),
                "summary": cached.get("summary", ""),
                "topics": cached.get("topics", []),
                "warnings": cached.get("warnings", []),
                "validation_details": cached.get("validation_details", {}),
                "critical_issues": cached.get("critical_issues", []),
            }
            analysis_runtime = {
                "provider": cached.get("analysis_info", {}).get("api_provider", "cached"),
                "fallback_used": cached.get("analysis_info", {}).get("fallback_used", False),
                "moderation_bucket": cached.get("report_status", {}).get("moderation_bucket", "needs_moderator_review"),
                "risk_score": cached.get("report_status", {}).get("risk_score", 50),
                "cached_reuse": True,
            }
        else:
            result, analysis_runtime = analyze_with_hybrid_fallback(extracted_text, meta_payload)
    else:
        result, analysis_runtime = analyze_with_hybrid_fallback(extracted_text, meta_payload)

    # ✅ Save comprehensive AI report with detailed information
    ai_reports_collection.update_one(
        {"note_id": ObjectId(note_id)},
        {
            "$set": {
                "note_id": ObjectId(note_id),
                "content_valid": bool(result.get("content_valid", False)),
                "title_match": bool(result.get("title_match", False)),
                "description_match": bool(result.get("description_match", False)),
                "subject_match": bool(result.get("subject_match", False)),
                "tags_relevance": bool(result.get("tags_relevance", False)),
                "spam_score": int(result.get("spam_score", 0)),
                "is_spam": bool(result.get("is_spam", False)),
                "is_relevant": bool(result.get("is_relevant", True)),
                "summary": result.get("summary", ""),
                "report": result,
                "topics": result.get("topics", []),
                "warnings": result.get("warnings", []),
                "personal_info": personal_info,
                "validation_details": result.get("validation_details", {}),
                "critical_issues": result.get("critical_issues", []),
                "file_hash": file_hash,
                "analysis_version": 2,
                "metadata_validated": {
                    "title": title,
                    "description": description,
                    "subject": subject,
                    "tags": tags,
                    "dept": dept,
                    "unit": unit
                },
                "analysis_info": {
                    "analyzed_by": current_user["id"],
                    "analyzed_by_name": current_user["name"],
                    "analyzed_by_email": current_user["email"],
                    "analyzed_by_role": current_user["role"],
                    "analyzed_at": int(time.time()),
                    "analysis_timestamp": datetime.now().isoformat(),
                    "ai_model": _model_for_provider(analysis_runtime.get("provider", "rules")),
                    "api_provider": analysis_runtime.get("provider", "rules"),
                    "fallback_used": analysis_runtime.get("fallback_used", False),
                    "cached_reuse": analysis_runtime.get("cached_reuse", False),
                    "analysis_duration_ms": 0,  # Could be added if needed
                },
                "note_info": {
                    "note_id": ObjectId(note_id),
                    "note_title": note.get("title", ""),
                    "note_description": note.get("description", ""),
                    "note_subject": note.get("subject", ""),
                    "note_dept": note.get("dept", ""),
                    "note_unit": note.get("unit", ""),
                    "note_tags": note.get("tags", []),
                    "note_is_paid": note.get("is_paid", False),
                    "note_price": note.get("price", 0),
                    "note_status": note.get("status", "pending"),
                    "note_uploader_id": note.get("uploader_id"),
                    "note_file_url": note.get("file_url", ""),
                    "note_created_at": note.get("created_at"),
                    "note_updated_at": note.get("updated_at")
                },
                "report_status": {
                    "validation_success": bool(result.get("content_valid", False)) and bool(result.get("title_match", False)) and bool(result.get("subject_match", False)) and not bool(result.get("is_spam", True)) and int(result.get("spam_score", 100)) < 50 and len(result.get("critical_issues", [])) == 0,
                    "validation_message": "✅ VALID: Content matches metadata perfectly" if bool(result.get("content_valid", False)) and bool(result.get("title_match", False)) and bool(result.get("subject_match", False)) and not bool(result.get("is_spam", True)) and int(result.get("spam_score", 100)) < 50 and len(result.get("critical_issues", [])) == 0 else "⚠️ NEEDS REVIEW: Some validation checks failed" if len(result.get("critical_issues", [])) > 0 else "❌ INVALID: " + "; ".join(result.get("critical_issues", [])[:2]),
                    "critical_issues_count": len(result.get("critical_issues", [])),
                    "warnings_count": len(result.get("warnings", [])),
                    "recommendation": "auto_generated",
                    "moderation_bucket": analysis_runtime.get("moderation_bucket", "needs_moderator_review"),
                    "risk_score": analysis_runtime.get("risk_score", 50),
                }
            }
        },
        upsert=True,
    )

    # Keep note.ai in sync so moderator UI and quality gate checks are consistent
    note_ai = {
        "summary": result.get("summary", ""),
        "topics": result.get("topics", []),
        "revision_bullets": result.get("revision_bullets", []),
        "important_questions": result.get("important_questions", []),
        "spam_score": float(result.get("spam_score", 0)) / 100.0,
        "relevance_score": float(result.get("relevance_score", 0.0)),
        "quality_score": float(result.get("quality_score", 0.0)),
        "subject_mismatch": not bool(result.get("subject_match", False)),
        "subject_mismatch_reason": "" if bool(result.get("subject_match", False)) else "Subject mismatch detected by AI.",
        "suggested_status": "reject" if analysis_runtime.get("risk_score", 50) >= 70 else "approve",
        "reason": "; ".join((result.get("critical_issues") or result.get("warnings") or [])[:2]),
        "pii_found": bool(personal_info.get("emails") or personal_info.get("phones")),
        "pii_matches": (personal_info.get("emails", []) + personal_info.get("phones", [])),
        "provider": analysis_runtime.get("provider", "rules"),
        "moderation_bucket": analysis_runtime.get("moderation_bucket", "needs_moderator_review"),
        "risk_score": int(analysis_runtime.get("risk_score", 50)),
        "analyzed_at": int(time.time()),
    }
    notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": {"ai": note_ai}})

    # ✅ Determine overall success (more strict)
    critical_issues = result.get("critical_issues", [])
    has_critical_issues = len(critical_issues) > 0
    
    validation_success = (
        result.get("content_valid", False) and
        result.get("title_match", False) and
        result.get("subject_match", False) and
        not result.get("is_spam", True) and
        result.get("spam_score", 100) < 50 and
        not has_critical_issues
    )

    # ✅ Create clear validation message
    if has_critical_issues:
        validation_message = f"❌ INVALID: {'; '.join(critical_issues[:2])}"
    elif validation_success:
        validation_message = "✅ VALID: Content matches metadata perfectly"
    else:
        validation_message = "⚠️ NEEDS REVIEW: Some validation checks failed"

    # Smart notifications for creators and audit timeline
    try:
        bucket = analysis_runtime.get("moderation_bucket", "needs_moderator_review")
        uploader_id = str(note.get("uploader_id")) if note.get("uploader_id") else None
        if uploader_id:
            if bucket == "auto_reject_candidate":
                notify(
                    uploader_id,
                    "ai",
                    f"AI flagged your note '{title}' as high risk for moderation.",
                    f"/notes/{note_id}",
                )
            elif bucket == "needs_moderator_review":
                notify(
                    uploader_id,
                    "ai",
                    f"AI routed your note '{title}' for manual review.",
                    f"/notes/{note_id}",
                )
            else:
                notify(
                    uploader_id,
                    "ai",
                    f"AI completed validation for your note '{title}'.",
                    f"/notes/{note_id}",
                )
        log_audit_event(
            "ai_analysis",
            current_user["id"],
            note_id,
            {
                "provider": analysis_runtime.get("provider", "rules"),
                "bucket": bucket,
                "risk_score": analysis_runtime.get("risk_score", 50),
                "cached_reuse": analysis_runtime.get("cached_reuse", False),
            },
        )
    except Exception as exc:
        logger.warning("Could not emit AI notifications/audit for note %s: %s", note_id, exc)

    return {
        "message": "AI analysis completed ✅",
        "validation_success": validation_success,
        "validation_message": validation_message,
        "critical_issues": critical_issues,
        "report": result,
        "moderation_bucket": analysis_runtime.get("moderation_bucket", "needs_moderator_review"),
        "provider": analysis_runtime.get("provider", "rules"),
        "cached_reuse": analysis_runtime.get("cached_reuse", False),
        "personal_info": personal_info,
        "metadata": {
            "title": title,
            "description": description,
            "subject": subject,
            "tags": tags,
            "dept": dept,
            "unit": unit
        }
    }


@router.get("/reports")
def get_all_ai_reports(current_user=Depends(get_current_user)):
    """Get all AI analysis reports (admin/moderator only)"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    try:
        # Get all AI reports with detailed information
        reports = list(ai_reports_collection.find(
            {}, 
            {"sort": [("analysis_timestamp", -1)]}
        ))
        
        # Convert ObjectId to string for JSON serialization
        for report in reports:
            report["_id"] = str(report["_id"])
            report["note_id"] = str(report["note_id"])
        
        return {
            "total_reports": len(reports),
            "reports": reports,
            "analysis_summary": {
                "total_analyzed": len(reports),
                "valid_reports": len([r for r in reports if r.get("report_status", {}).get("validation_success", False)]),
                "invalid_reports": len([r for r in reports if not r.get("report_status", {}).get("validation_success", False)]),
                "high_risk_reports": len([r for r in reports if r.get("spam_score", 0) > 70]),
                "avg_spam_score": sum(r.get("spam_score", 0) for r in reports) / len(reports) if reports else 0,
                "most_common_topics": _get_most_common_topics(reports),
                "last_analysis": reports[0]["analysis_info"]["analysis_timestamp"] if reports else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports: {str(e)}")


def _get_most_common_topics(reports):
    """Helper function to get most common topics from AI reports"""
    topic_count = {}
    for report in reports:
        topics = report.get("topics", [])
        for topic in topics:
            topic_count[topic] = topic_count.get(topic, 0) + 1
    
    # Sort by count and return top 10
    sorted_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)
    return [{"topic": topic, "count": count} for topic, count in sorted_topics[:10]]


@router.get("/reports/note/{note_id}")
def get_note_ai_report(note_id: str, current_user=Depends(get_current_user)):
    """Get AI report for a specific note"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    
    report = ai_reports_collection.find_one({"note_id": ObjectId(note_id)})
    if not report:
        return {"exists": False}
    
    report["_id"] = str(report["_id"])
    report["note_id"] = str(report["note_id"])
    
    return {"exists": True, "report": report}


@router.get("/reports/summary")
def get_ai_reports_summary(current_user=Depends(get_current_user)):
    """Get AI analysis summary statistics (admin/moderator only)"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    try:
        # Get basic statistics
        reports = list(ai_reports_collection.find({}))
        total_reports = len(reports)
        valid_reports = len([r for r in reports if r.get("report_status", {}).get("validation_success", False)])
        invalid_reports = total_reports - valid_reports
        high_risk_reports = len([r for r in reports if r.get("spam_score", 0) > 70])
        avg_spam_score = sum(r.get("spam_score", 0) for r in reports) / total_reports if reports else 0
        
        return {
            "total_analyzed": total_reports,
            "validation_summary": {
                "valid": valid_reports,
                "invalid": invalid_reports,
                "success_rate": (valid_reports / total_reports * 100) if total_reports > 0 else 0
            },
            "spam_summary": {
                "high_risk": high_risk_reports,
                "avg_score": avg_spam_score
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.post("/reports/export")
def export_ai_reports(current_user=Depends(get_current_user)):
    """Export AI reports to CSV (admin/moderator only)"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    try:
        reports = list(ai_reports_collection.find(
            {}, 
            {"sort": [("analysis_timestamp", -1)]}
        ))
        
        # Create CSV content
        csv_lines = ["Note ID,Note Title,Note Subject,Validation Success,Spam Score,Content Valid,Title Match,Subject Match,Tags Relevant,Analyzed By,Analyzed At,AI Model,Recommendation,Critical Issues,Warnings,Topics"]
        
        for report in reports:
            note_id = str(report["note_id"])
            note_title = report.get("note_info", {}).get("note_title", "")
            note_subject = report.get("note_info", {}).get("note_subject", "")
            validation_success = report.get("report_status", {}).get("validation_success", False)
            spam_score = report.get("spam_score", 0)
            content_valid = report.get("content_valid", False)
            title_match = report.get("title_match", False)
            subject_match = report.get("subject_match", False)
            tags_relevance = report.get("tags_relevance", False)
            analyzed_by = report.get("analysis_info", {}).get("analyzed_by_name", "Unknown")
            analyzed_at = report.get("analysis_info", {}).get("analysis_timestamp", "")
            ai_model = report.get("analysis_info", {}).get("ai_model", "Unknown")
            recommendation = report.get("report_status", {}).get("recommendation", "auto_generated")
            critical_issues = report.get("critical_issues", [])
            warnings = report.get("warnings", [])
            topics = report.get("topics", [])
            
            topics_str = ",".join(topics) if topics else ""
            csv_lines.append(f"{note_id},\"{note_title}\",\"{note_subject}\",{validation_success},{spam_score},{content_valid},{title_match},{subject_match},{tags_relevance},\"{analyzed_by}\",\"{analyzed_at}\",\"{ai_model}\",\"{recommendation}\",\"{len(critical_issues)}\",\"{len(warnings)}\",\"{topics_str}\"")
        
        csv_content = "\n".join(csv_lines)
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ai_reports.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export reports: {str(e)}")


@router.post("/reports/{note_id}/regenerate")
def regenerate_ai_report(note_id: str, current_user=Depends(get_current_user)):
    """Regenerate AI analysis for a specific note (admin/moderator only)"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    
    try:
        # Re-run the analysis
        return analyze_note(note_id, force=True, current_user=current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate report: {str(e)}")


@router.get("/moderation-queue")
def moderation_queue(current_user=Depends(get_current_user)):
    """
    Return notes where AI risk indicates manual moderator review is most useful.
    """
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    reports = list(
        ai_reports_collection.find(
            {"report_status.moderation_bucket": "needs_moderator_review"},
            sort=[("analysis_info.analyzed_at", -1)],
            limit=100,
        )
    )
    note_ids = [r.get("note_id") for r in reports if r.get("note_id")]
    notes_map = {
        n["_id"]: n
        for n in notes_collection.find(
            {"_id": {"$in": note_ids}, "status": {"$in": ["pending", "approved", "rejected"]}}
        )
    }
    queue = []
    for report in reports:
        note = notes_map.get(report.get("note_id"))
        if not note:
            continue
        queue.append(
            {
                "note_id": str(note["_id"]),
                "title": note.get("title", ""),
                "subject": note.get("subject", ""),
                "status": note.get("status", "pending"),
                "risk_score": report.get("report_status", {}).get("risk_score", 50),
                "provider": report.get("analysis_info", {}).get("api_provider", "rules"),
                "validation_message": report.get("report_status", {}).get("validation_message", ""),
            }
        )

    return {"count": len(queue), "items": queue}


@router.post("/analyze-note/{note_id}")
def analyze_note_legacy(note_id: str, force: bool = False, current_user=Depends(get_current_user)):
    """
    Legacy endpoint to match frontend calls
    """
    return analyze_note(note_id, force=force, current_user=current_user)


@router.get("/worker/health")
def ai_worker_health(current_user=Depends(get_current_user)):
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")
    mode = os.getenv("MODERATION_AI_MODE", "rules").lower()
    uses_paid = mode in {"gemini", "auto"} and bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "status": "ok",
        "moderation_mode": mode,
        "uses_paid_api": uses_paid,
        "fallback_provider": "ollama/rules" if mode == "auto" else "rules",
    }
