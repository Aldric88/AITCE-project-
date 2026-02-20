import os
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_RE = r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"


def detect_pii(text: str):
    emails = re.findall(EMAIL_RE, text)
    phones = re.findall(PHONE_RE, text)
    pii = list(set(emails + phones))
    return pii


def analyze_note_text(text: str, meta: dict):
    """
    Uses OpenAI to return summary, topics, spam/relevance/quality scoring + suggestion.
    """
    title = meta.get("title", "")
    subject = meta.get("subject", "")
    dept = meta.get("dept", "")
    unit = meta.get("unit", "")

    prompt = f"""
You are an AI moderator for a college notes marketplace.

You will receive extracted text from a notes file and metadata.

Goals:
1) Detect spam / irrelevant content
2) Summarize the note (short)
3) Extract 5-10 key topics
4) Generate 3-5 quick revision bullet points
5) Generate 2-4 important exam questions
6) Give quality score (0-1)
7) Suggest approve or reject
8) Give reasons

Also check if the content does NOT match the metadata subject/unit.
If mismatch, set subject_mismatch=true and explain why.

Metadata:
title={title}
subject={subject}
dept={dept}
unit={unit}

Extracted Text:
{text[:6000]}

Return STRICT JSON like:
{{
  "summary": "string",
  "topics": ["t1","t2"],
  "revision_bullets": ["b1","b2","b3"],
  "important_questions": ["q1","q2"],
  "spam_score": 0.0,
  "relevance_score": 0.0,
  "quality_score": 0.0,
  "subject_mismatch": false,
  "subject_mismatch_reason": "string",
  "suggested_status": "approve" or "reject",
  "reason": "short reason"
}}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )

    content = res.choices[0].message.content.strip()

    # OpenAI usually returns JSON correctly, but keep safe fallback
    import json
    try:
        return json.loads(content)
    except:
        # fallback minimal result
        return {
            "summary": "AI summary failed",
            "topics": [],
            "revision_bullets": [],
            "important_questions": [],
            "spam_score": 0.5,
            "relevance_score": 0.5,
            "quality_score": 0.5,
            "subject_mismatch": False,
            "subject_mismatch_reason": "",
            "suggested_status": "pending",
            "reason": "AI returned invalid JSON"
        }
