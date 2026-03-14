"""
College domain validation.

Priority:
  1. Blocklist  — personal/corporate emails → reject immediately.
  2. Academic TLDs — .ac.in, .edu, .edu.in … → accept immediately.
  3. DB cache   — previously AI-validated result in college_domain_cache.
  4. Gemini AI  — ask "is this a college domain?" and cache the answer.
  5. Fallback   — if AI unavailable, accept with a warning flag.
"""

import json
import os
import time
import urllib.error
import urllib.request

from app.database import db

_cache_collection = db["college_domain_cache"]

# ── personal / corporate blocklist ──────────────────────────────────────────
PERSONAL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "hotmail.com", "outlook.com",
    "live.com", "icloud.com", "me.com", "protonmail.com", "proton.me",
    "rediffmail.com", "ymail.com", "aol.com", "zoho.com",
}

# ── well-known academic TLD suffixes ────────────────────────────────────────
ACADEMIC_TLDS = (
    ".ac.in", ".edu", ".edu.in", ".edu.au", ".edu.sg", ".edu.hk",
    ".ac.uk", ".ac.nz", ".ac.za", ".ac.jp", ".ac.kr",
)


def _is_academic_tld(domain: str) -> bool:
    for tld in ACADEMIC_TLDS:
        if domain.endswith(tld):
            return True
    return False


def _cached_result(domain: str):
    doc = _cache_collection.find_one({"domain": domain})
    if doc and doc.get("expires_at", 0) > int(time.time()):
        return doc
    return None


def _save_cache(domain: str, is_college: bool, institution_name: str, source: str):
    ttl = int(os.getenv("DOMAIN_CACHE_TTL_SECONDS", str(30 * 24 * 3600)))  # 30 days
    _cache_collection.update_one(
        {"domain": domain},
        {"$set": {
            "domain": domain,
            "is_college": is_college,
            "institution_name": institution_name,
            "source": source,
            "checked_at": int(time.time()),
            "expires_at": int(time.time()) + ttl,
        }},
        upsert=True,
    )


def _ask_gemini(domain: str):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    prompt = (
        "You are a domain verification assistant.\n"
        "Determine whether the following email domain belongs to an accredited "
        "educational institution (college, university, or school).\n"
        "Return STRICT JSON with exactly these keys:\n"
        '  "is_college": true or false\n'
        '  "institution_name": string (full name, or "" if not a college)\n'
        '  "reason": one short sentence\n'
        f"domain: {domain}\n"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            raw = resp.read().decode()
        data = json.loads(raw)
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        parsed = json.loads(text.strip().replace("```json", "").replace("```", "").strip())
        return {
            "is_college": bool(parsed.get("is_college")),
            "institution_name": str(parsed.get("institution_name", "")),
            "reason": str(parsed.get("reason", "")),
        }
    except Exception:
        return None


def validate_college_domain(email: str) -> dict:
    """
    Returns:
        {
          "allowed": bool,
          "reason": str,           # human-readable message
          "institution_name": str, # empty string if unknown / rejected
          "source": str,           # "academic_tld" | "ai_verified" | "blocklist" | "cache" | "fallback"
          "verified_by_domain": bool,
        }
    """
    if "@" not in email:
        return {
            "allowed": False,
            "reason": "Invalid email format.",
            "institution_name": "",
            "source": "blocklist",
            "verified_by_domain": False,
        }
    domain = email.split("@", 1)[1].lower().strip()
    if not domain:
        return {
            "allowed": False,
            "reason": "Invalid email format (empty domain).",
            "institution_name": "",
            "source": "blocklist",
            "verified_by_domain": False,
        }

    # 1. Hard block personal emails
    if domain in PERSONAL_DOMAINS:
        return {
            "allowed": False,
            "reason": f"Personal email addresses ({domain}) are not accepted. Please use your college email.",
            "institution_name": "",
            "source": "blocklist",
            "verified_by_domain": False,
        }

    # 2. Academic TLD → instant approve
    if _is_academic_tld(domain):
        return {
            "allowed": True,
            "reason": "Academic institution domain confirmed.",
            "institution_name": "",
            "source": "academic_tld",
            "verified_by_domain": True,
        }

    # 3. DB cache
    cached = _cached_result(domain)
    if cached:
        return {
            "allowed": cached["is_college"],
            "reason": "Verified from domain cache." if cached["is_college"] else "Domain is not a recognized college.",
            "institution_name": cached.get("institution_name", ""),
            "source": "cache",
            "verified_by_domain": cached["is_college"],
        }

    # 4. Gemini AI
    ai = _ask_gemini(domain)
    if ai is not None:
        _save_cache(domain, ai["is_college"], ai["institution_name"], "ai")
        return {
            "allowed": ai["is_college"],
            "reason": ai["reason"] if not ai["is_college"] else f"AI verified: {ai['institution_name'] or domain}",
            "institution_name": ai["institution_name"],
            "source": "ai_verified",
            "verified_by_domain": ai["is_college"],
        }

    # 5. Fallback — AI unavailable, accept with warning (dev/offline mode)
    _save_cache(domain, True, "", "fallback")
    return {
        "allowed": True,
        "reason": "Domain could not be verified automatically — accepted with manual review pending.",
        "institution_name": "",
        "source": "fallback",
        "verified_by_domain": False,
    }
