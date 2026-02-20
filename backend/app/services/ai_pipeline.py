import logging
import os
import time

from bson import ObjectId
from pymongo import ReturnDocument

from app.database import notes_collection, uploads_collection, ai_jobs_collection
from app.config import settings
from app.utils.text_extract import extract_text_from_pdf
from app.services.hybrid_moderation import analyze_with_hybrid_fallback, detect_personal_info

logger = logging.getLogger(__name__)


def _mark_job_terminal(job_id, status: str, error: str | None = None):
    payload = {"status": status, "finished_at": int(time.time())}
    if error:
        payload["error"] = error
    ai_jobs_collection.update_one({"_id": job_id}, {"$set": payload})


def _mark_job_failure(job: dict, error_code: str):
    attempts = int(job.get("attempts", 1))
    max_attempts = max(1, int(settings.AI_JOB_MAX_ATTEMPTS))
    if attempts >= max_attempts:
        _mark_job_terminal(job["_id"], "dead_letter", error_code)
        logger.error("AI job moved to dead-letter note_id=%s attempts=%s error=%s", job.get("note_id"), attempts, error_code)
        return
    ai_jobs_collection.update_one(
        {"_id": job["_id"]},
        {
            "$set": {
                "status": "queued",
                "error": error_code,
                "retry_at": int(time.time()) + min(60 * attempts, 300),
            }
        },
    )

def enqueue_note_ai_analysis(note_id: str, file_url: str, meta: dict):
    ai_jobs_collection.insert_one(
        {
            "note_id": ObjectId(note_id),
            "file_url": file_url,
            "meta": meta,
            "status": "queued",
            "attempts": 0,
            "created_at": int(time.time()),
        }
    )


def process_next_ai_job() -> bool:
    now = int(time.time())
    job = ai_jobs_collection.find_one_and_update(
        {
            "status": "queued",
            "$or": [{"retry_at": {"$exists": False}}, {"retry_at": {"$lte": now}}],
        },
        {
            "$set": {"status": "processing", "started_at": now},
            "$inc": {"attempts": 1},
            "$unset": {"retry_at": ""},
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if not job:
        return False
    note_id = str(job["note_id"])
    file_url = job["file_url"]
    meta = job.get("meta", {})

    try:
        upload_doc = uploads_collection.find_one({"file_url": file_url})
        if not upload_doc or upload_doc.get("file_ext", "").lower() != ".pdf":
            _mark_job_terminal(job["_id"], "done")
            return True

        stored_name = upload_doc.get("stored_name")
        if not stored_name:
            _mark_job_terminal(job["_id"], "done")
            return True

        file_path = None
        for candidate in (
            os.path.join("uploads/private", stored_name),
            os.path.join("uploads", stored_name),
        ):
            if os.path.exists(candidate):
                file_path = candidate
                break
        if not file_path:
            logger.warning("AI analysis skipped, file not found for note_id=%s", note_id)
            _mark_job_failure(job, "file_not_found")
            return True

        extracted_text = extract_text_from_pdf(file_path)
        pii = detect_personal_info(extracted_text)
        ai_result, runtime = analyze_with_hybrid_fallback(extracted_text, meta)

        ai_doc = {
            "summary": ai_result.get("summary", ""),
            "topics": ai_result.get("topics", []),
            "revision_bullets": ai_result.get("revision_bullets", []),
            "important_questions": ai_result.get("important_questions", []),
            "spam_score": ai_result.get("spam_score", 0.0),
            "relevance_score": ai_result.get("relevance_score", 0.0),
            "quality_score": ai_result.get("quality_score", 0.0),
            "subject_mismatch": ai_result.get("subject_mismatch", False),
            "subject_mismatch_reason": ai_result.get("subject_mismatch_reason", ""),
            "suggested_status": ai_result.get("suggested_status", "pending"),
            "reason": ai_result.get("reason", ""),
            "pii_found": bool(pii.get("emails") or pii.get("phones")),
            "pii_matches": (pii.get("emails", []) + pii.get("phones", [])),
            "provider": runtime.get("provider", "rules"),
            "moderation_bucket": runtime.get("moderation_bucket", "needs_moderator_review"),
            "risk_score": runtime.get("risk_score", 50),
            "analyzed_at": int(time.time()),
        }

        auto_reject = False
        reject_reason = ""

        if ai_doc["pii_found"]:
            auto_reject = True
            reject_reason = "Rejected: Personal info detected (PII)."
        elif ai_doc["spam_score"] >= 0.75:
            auto_reject = True
            reject_reason = "Rejected: AI spam score too high."
        elif ai_doc["quality_score"] <= 0.35:
            auto_reject = True
            reject_reason = "Rejected: AI quality score too low."
        elif ai_doc["relevance_score"] <= 0.35:
            auto_reject = True
            reject_reason = "Rejected: AI relevance score too low."
        elif ai_doc.get("subject_mismatch") is True:
            auto_reject = True
            reject_reason = (
                "Rejected: Subject mismatch detected. "
                f"{ai_doc.get('subject_mismatch_reason', '')}"
            )

        update = {"ai": ai_doc}
        if auto_reject:
            update.update(
                {
                    "status": "rejected",
                    "rejected_reason": reject_reason,
                    "rejected_at": int(time.time()),
                }
            )

        notes_collection.update_one({"_id": ObjectId(note_id)}, {"$set": update})
        _mark_job_terminal(job["_id"], "done")
    except Exception:
        logger.exception("Async note AI analysis failed for note_id=%s", note_id)
        _mark_job_failure(job, "processing_exception")
    return True


def run_ai_worker_loop(poll_seconds: int = 2):
    logger.info("AI worker started with poll_seconds=%s", poll_seconds)
    while True:
        found = process_next_ai_job()
        if not found:
            time.sleep(poll_seconds)


def get_ai_queue_stats() -> dict:
    now = int(time.time())
    queued = ai_jobs_collection.count_documents({"status": "queued"})
    processing = ai_jobs_collection.count_documents({"status": "processing"})
    dead_letter = ai_jobs_collection.count_documents({"status": "dead_letter"})
    failed = ai_jobs_collection.count_documents({"status": "failed"})
    oldest = ai_jobs_collection.find_one({"status": "queued"}, sort=[("created_at", 1)])
    lag_seconds = (now - int(oldest.get("created_at", now))) if oldest else 0
    return {
        "queued": queued,
        "processing": processing,
        "failed": failed,
        "dead_letter": dead_letter,
        "queue_lag_seconds": max(lag_seconds, 0),
        "max_attempts": int(settings.AI_JOB_MAX_ATTEMPTS),
    }
