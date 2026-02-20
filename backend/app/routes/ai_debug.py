import os
import re
import json
import fitz  # PyMuPDF
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import notes_collection, ai_reports_collection, uploads_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI Debug"])


def _load_gemini_client():
    try:
        import google.generativeai as genai  # type: ignore
        return genai
    except Exception:
        return None

@router.get("/test")
def test_ai(current_user=Depends(get_current_user)):
    """Test Gemini API directly"""
    if current_user.get("role") not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "GEMINI_API_KEY missing"}

        genai = _load_gemini_client()
        if genai is None:
            return {"error": "google-generativeai package not installed"}

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content("Hello test")
        
        return {
            "status": "success",
            "response": response.text,
            "model": "gemini-2.5-flash",
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/test-full/{note_id}")
def test_full_ai(note_id: str, current_user=Depends(get_current_user)):
    """Test full AI pipeline"""
    if current_user.get("role") not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        if not ObjectId.is_valid(note_id):
            return {"error": "Invalid note_id"}
        
        note = notes_collection.find_one({"_id": ObjectId(note_id)})
        if not note:
            return {"error": "Note not found"}
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "GEMINI_API_KEY missing"}
        genai = _load_gemini_client()
        if genai is None:
            return {"error": "google-generativeai package not installed"}
        
        file_url = note.get("file_url")
        if not file_url:
            return {"error": "No file attached"}
        
        upload_doc = uploads_collection.find_one({"file_url": file_url})
        if not upload_doc:
            return {"error": "Uploaded file record not found"}

        stored_name = upload_doc.get("stored_name")
        if not stored_name:
            return {"error": "File metadata corrupted"}

        file_path = os.path.join("uploads/private", stored_name)
        if not os.path.exists(file_path):
            return {"error": "File not found"}
        
        # Test text extraction
        doc = fitz.open(file_path)
        pages = min(doc.page_count, 3)
        text = []
        for i in range(pages):
            page = doc.load_page(i)
            text.append(page.get_text("text"))
        doc.close()
        extracted_text = "\n".join(text).strip()
        
        # Test Gemini (optional debug only)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f'''You are a strict academic notes moderator.

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
'''
        
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        
        return {
            "status": "success",
            "text_length": len(extracted_text),
            "api_response": result
        }
        
    except Exception as e:
        return {"error": str(e)}
