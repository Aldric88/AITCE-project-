import os
import re
import json
import fitz  # PyMuPDF
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

import google.generativeai as genai

from app.database import notes_collection, ai_reports_collection, uploads_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI Moderation (Gemini)"])


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


# ✅ helper: personal info detection (basic)
def detect_personal_info(text: str):
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"\b\d{10}\b", text)
    return {
        "emails": list(set(emails))[:5],
        "phones": list(set(phones))[:5],
    }


@router.post("/analyze/{note_id}")
def analyze_note(note_id: str, current_user=Depends(get_current_user)):
    # ✅ Only admin/moderator can run AI
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY missing in backend .env")

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

    # ✅ Gemini init
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are a strict academic notes moderator.

Analyze the note snippet and return STRICT JSON ONLY (no markdown, no explanation).

Return format:
{{
  "spam_score": 0-100,
  "is_spam": true/false,
  "is_relevant": true/false,
  "summary": "short summary (max 2 lines)",
  "topics": ["topic1","topic2","topic3"],
  "warnings": ["warning1","warning2"]
}}

Note snippet:
\"\"\"{extracted_text[:4500]}\"\"\"
"""

    try:
        resp = model.generate_content(prompt)
        raw = resp.text.strip()

        # ✅ Sometimes Gemini wraps json in ```json ... ```
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini analysis failed: {str(e)}")

    # ✅ Save report
    ai_reports_collection.update_one(
        {"note_id": ObjectId(note_id)},
        {
            "$set": {
                "note_id": ObjectId(note_id),
                "spam_score": int(result.get("spam_score", 0)),
                "is_spam": bool(result.get("is_spam", False)),
                "is_relevant": bool(result.get("is_relevant", True)),
                "summary": result.get("summary", ""),
                "topics": result.get("topics", []),
                "warnings": result.get("warnings", []),
                "personal_info": personal_info,
            }
        },
        upsert=True,
    )

    return {
        "message": "AI analysis completed ✅",
        "report": result,
        "personal_info": personal_info,
    }


@router.get("/report/{note_id}")
def get_ai_report(note_id: str, current_user=Depends(get_current_user)):
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
