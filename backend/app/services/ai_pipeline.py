import logging
import os
import time

from app.database import uploads_collection
from app.utils.text_extract import extract_text_from_pdf
from app.services.hybrid_moderation import analyze_with_hybrid_fallback, detect_personal_info

logger = logging.getLogger(__name__)


def analyze_note_sync(file_url: str, meta: dict) -> dict:
    """
    Run AI analysis synchronously on an uploaded note file.
    Returns {"approved": bool, "reason": str, "ai": dict}
    Non-PDF files are auto-approved (no text to scan).
    """
    upload_doc = uploads_collection.find_one({"file_url": file_url})
    if not upload_doc or upload_doc.get("file_ext", "").lower() != ".pdf":
        return {"approved": True, "reason": "", "ai": None}

    stored_name = upload_doc.get("stored_name")
    if not stored_name:
        return {"approved": True, "reason": "", "ai": None}

    file_path = None
    for candidate in (
        os.path.join("uploads/private", stored_name),
        os.path.join("uploads", stored_name),
    ):
        if os.path.exists(candidate):
            file_path = candidate
            break

    if not file_path:
        # File not found locally — auto-approve rather than blocking upload
        return {"approved": True, "reason": "", "ai": None}

    try:
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
            "moderation_bucket": runtime.get("moderation_bucket", "auto_approved"),
            "risk_score": runtime.get("risk_score", 50),
            "analyzed_at": int(time.time()),
        }

        reject_reason = ""
        if ai_doc["pii_found"]:
            reject_reason = "Your note contains personal information (email/phone). Remove it and try again."
        elif ai_doc["spam_score"] >= 0.75:
            reject_reason = "Your note was flagged as spam or unrelated content."
        elif ai_doc["quality_score"] <= 0.35:
            reject_reason = "Your note content quality is too low. Ensure the PDF has readable academic content."
        elif ai_doc["relevance_score"] <= 0.35:
            reject_reason = "Your note does not appear relevant to the stated subject."
        elif ai_doc.get("subject_mismatch") is True:
            reject_reason = f"Subject mismatch: {ai_doc.get('subject_mismatch_reason', 'Content does not match the subject you selected.')}"

        return {
            "approved": reject_reason == "",
            "reason": reject_reason,
            "ai": ai_doc,
        }
    except Exception:
        logger.exception("Sync AI analysis failed for file_url=%s — auto-approving", file_url)
        return {"approved": True, "reason": "", "ai": None}
