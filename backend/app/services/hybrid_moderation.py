import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_RE = r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"


def detect_personal_info(text: str) -> Dict[str, Any]:
    emails = list(set(re.findall(EMAIL_RE, text)))[:5]
    phones = list(set(re.findall(PHONE_RE, text)))[:5]
    return {"emails": emails, "phones": phones}


def _safe_json_loads(raw: str):
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def _rules_based_analysis(text: str, meta: dict) -> dict:
    lowered_text = (text or "").lower()
    title = str(meta.get("title", "")).lower()
    description = str(meta.get("description", "")).lower()
    subject = str(meta.get("subject", "")).lower()
    tags = [str(t).lower() for t in (meta.get("tags") or [])]

    def overlap_score(tokens):
        tokens = [t for t in tokens if len(t) > 2]
        if not tokens:
            return 0.5
        matches = sum(1 for t in tokens if t in lowered_text)
        return matches / max(len(tokens), 1)

    title_tokens = re.findall(r"[a-z0-9]+", title)
    description_tokens = re.findall(r"[a-z0-9]+", description)
    subject_tokens = re.findall(r"[a-z0-9]+", subject)
    tag_tokens = []
    for tag in tags:
        tag_tokens.extend(re.findall(r"[a-z0-9]+", tag))

    title_score = overlap_score(title_tokens)
    description_score = overlap_score(description_tokens)
    subject_score = overlap_score(subject_tokens)
    tags_score = overlap_score(tag_tokens)

    short_text = len(re.findall(r"[a-zA-Z0-9]", lowered_text)) < 120
    repeated_char_noise = bool(re.search(r"(.)\1{8,}", lowered_text))

    critical_issues = []
    if subject_score < 0.15:
        critical_issues.append("Content does not match the specified subject.")
    if title_score < 0.15:
        critical_issues.append("Content appears unrelated to note title.")
    if short_text:
        critical_issues.append("Extracted content is too short for validation.")

    spam_score = 0
    if repeated_char_noise:
        spam_score += 35
    if short_text:
        spam_score += 25
    if subject_score < 0.15 and title_score < 0.15:
        spam_score += 35
    spam_score = min(100, spam_score)

    content_valid = subject_score >= 0.15 and title_score >= 0.15 and not short_text
    is_spam = spam_score >= 60
    is_relevant = (subject_score >= 0.2) or (tags_score >= 0.2)

    warnings = []
    if description_score < 0.2:
        warnings.append("Description alignment is weak.")
    if tags_score < 0.2 and tags:
        warnings.append("Tags are weakly represented in extracted text.")

    summary = "Rules-based analysis completed."
    if critical_issues:
        summary = "Validation found critical mismatches with metadata."
    elif content_valid:
        summary = "Content appears aligned with metadata."

    topics = sorted(set(re.findall(r"[a-z]{4,}", lowered_text)))[:8]

    return {
        "content_valid": content_valid,
        "title_match": title_score >= 0.15,
        "description_match": description_score >= 0.2,
        "subject_match": subject_score >= 0.15,
        "tags_relevance": tags_score >= 0.2 if tags else True,
        "spam_score": int(spam_score),
        "is_spam": is_spam,
        "is_relevant": is_relevant,
        "summary": summary,
        "topics": topics,
        "warnings": warnings,
        "validation_details": {
            "title_analysis": f"title overlap score={title_score:.2f}",
            "description_analysis": f"description overlap score={description_score:.2f}",
            "subject_analysis": f"subject overlap score={subject_score:.2f}",
            "tags_analysis": f"tags overlap score={tags_score:.2f}",
            "overall_assessment": summary,
        },
        "critical_issues": critical_issues,
    }


def _ollama_analysis(text: str, meta: dict) -> dict:
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    payload = {
        "model": ollama_model,
        "stream": False,
        "format": "json",
        "prompt": f"""
You are a strict academic notes moderator.
Return JSON with keys:
content_valid,title_match,description_match,subject_match,tags_relevance,spam_score,is_spam,is_relevant,summary,topics,warnings,validation_details,critical_issues
Metadata:
title={meta.get("title","")}
description={meta.get("description","")}
subject={meta.get("subject","")}
dept={meta.get("dept","")}
unit={meta.get("unit","")}
tags={meta.get("tags",[])}
Text:
{text[:4500]}
""",
    }
    req = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    llm_json = _safe_json_loads(data.get("response", ""))
    return llm_json


def _moderation_bucket(report: dict) -> Tuple[str, int]:
    spam_score = int(report.get("spam_score", 0))
    critical = report.get("critical_issues", []) or []
    title_match = bool(report.get("title_match", False))
    subject_match = bool(report.get("subject_match", False))
    content_valid = bool(report.get("content_valid", False))

    risk_score = min(
        100,
        spam_score
        + (30 if not content_valid else 0)
        + (25 if not subject_match else 0)
        + (20 if not title_match else 0)
        + min(len(critical) * 10, 30),
    )
    if risk_score <= 20 and content_valid and subject_match and title_match and not critical:
        return "auto_approve_candidate", risk_score
    if risk_score >= 70:
        return "auto_reject_candidate", risk_score
    return "needs_moderator_review", risk_score


def analyze_with_hybrid_fallback(text: str, meta: dict) -> Tuple[dict, dict]:
    mode = os.getenv("MODERATION_AI_MODE", "rules").lower()
    errors = []

    if mode in {"auto", "ollama"}:
        try:
            result = _ollama_analysis(text, meta)
            bucket, risk_score = _moderation_bucket(result)
            return result, {"provider": "ollama", "fallback_used": False, "moderation_bucket": bucket, "risk_score": risk_score}
        except (ValueError, KeyError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"ollama_failed:{exc}")
            if mode == "ollama":
                raise

    result = _rules_based_analysis(text, meta)
    bucket, risk_score = _moderation_bucket(result)
    return result, {
        "provider": "rules",
        "fallback_used": True,
        "fallback_reason": "; ".join(errors) if errors else "rules_only_mode",
        "moderation_bucket": bucket,
        "risk_score": risk_score,
    }
