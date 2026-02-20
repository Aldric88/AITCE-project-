import json
import os
import re
import time
import urllib.error
import urllib.request

from bson import ObjectId

from app.database import (
    college_domains_collection,
    colleges_collection,
    clusters_collection,
    cluster_inference_candidates_collection,
)


UNIVERSITY_TYPE_ALIASES = {
    "anna": "anna_affiliated",
    "anna_affiliated": "anna_affiliated",
    "anna_university": "anna_affiliated",
    "affiliated": "anna_affiliated",
    "autonomous": "autonomous",
    "deemed": "deemed",
    "deemed_university": "deemed",
}


def _normalize_university_type(value):
    if not value:
        return None
    key = str(value).strip().lower()
    return UNIVERSITY_TYPE_ALIASES.get(key, key)


def _normalize_id(value):
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value):
        return ObjectId(value)
    return value


def _default_cluster_for_university_type(university_type):
    if not university_type:
        return None

    cluster = clusters_collection.find_one(
        {"university_type": university_type, "is_default": True}
    )
    if cluster:
        return cluster.get("_id")

    # Backward-compatible fallback for older cluster docs using `type`.
    cluster = clusters_collection.find_one({"type": university_type})
    if cluster:
        return cluster.get("_id")

    return None


def _extract_domain_tokens(domain):
    left = domain.split(".")[0]
    tokens = [t for t in re.split(r"[^a-z0-9]+", left.lower()) if t]
    return tokens[:6]


def _heuristic_university_type_from_domain(domain):
    tokens = set(_extract_domain_tokens(domain))
    if not tokens:
        return None

    deemed_hints = {"deemed", "univ", "university", "vit", "srm", "amrita"}
    anna_hints = {"anna", "ceg", "mit", "au"}
    autonomous_hints = {"autonomous", "psgtech", "cit", "ssn", "kongu"}

    if tokens & deemed_hints:
        return "deemed"
    if tokens & anna_hints:
        return "anna_affiliated"
    if tokens & autonomous_hints:
        return "autonomous"
    return None


def _ai_classify_university_type(domain):
    mode = os.getenv("CLUSTER_AI_MODE", "auto").strip().lower()
    if mode in {"off", "disabled", "rules"}:
        return None

    ollama_url = os.getenv("CLUSTER_AI_OLLAMA_URL", os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"))
    ollama_model = os.getenv("CLUSTER_AI_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
    timeout = float(os.getenv("CLUSTER_AI_TIMEOUT_SECONDS", "2.5"))

    payload = {
        "model": ollama_model,
        "stream": False,
        "format": "json",
        "prompt": (
            "Classify the likely university_type for a college email domain.\n"
            "Allowed values: anna_affiliated, autonomous, deemed, unknown.\n"
            "Return strict JSON with keys: university_type, confidence, reason.\n"
            f"domain: {domain}\n"
        ),
    }
    req = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        parsed = json.loads((data.get("response", "") or "").strip().replace("```json", "").replace("```", "").strip())
        utype = _normalize_university_type(parsed.get("university_type"))
        if utype == "unknown":
            return None
        confidence = float(parsed.get("confidence", 0))
        return {
            "university_type": utype,
            "confidence": confidence,
            "reason": str(parsed.get("reason", "")),
        }
    except (ValueError, KeyError, TypeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        if mode == "ollama":
            raise
        return None


def _record_inference_candidate(domain, university_type, confidence, source, requires_manual_selection):
    now = int(time.time())
    update = {
        "$set": {
            "domain": domain,
            "last_inferred_university_type": university_type,
            "last_confidence": confidence,
            "last_source": source,
            "requires_manual_selection": requires_manual_selection,
            "review_status": "pending",
            "updated_at": now,
        },
        "$setOnInsert": {
            "created_at": now,
        },
        "$inc": {"inference_count": 1},
    }
    cluster_inference_candidates_collection.update_one({"domain": domain}, update, upsert=True)


def resolve_user_cluster_metadata(email):
    email_domain = email.split("@")[1].lower().strip()

    domain_mapping = college_domains_collection.find_one(
        {"domain": email_domain, "is_active": {"$ne": False}}
    ) or college_domains_collection.find_one({"domain": email_domain})

    if not domain_mapping:
        ai_result = _ai_classify_university_type(email_domain)
        inferred_type = None
        inferred_confidence = 0.0
        if ai_result:
            inferred_type = _normalize_university_type(ai_result.get("university_type"))
            inferred_confidence = float(ai_result.get("confidence", 0) or 0)
        if not inferred_type:
            inferred_type = _heuristic_university_type_from_domain(email_domain)
            if inferred_type:
                inferred_confidence = 0.55

        auto_assign_threshold = float(os.getenv("CLUSTER_AI_AUTO_ASSIGN_MIN_CONFIDENCE", "0.8"))
        inferred_cluster_id = _default_cluster_for_university_type(inferred_type) if inferred_type else None
        auto_assigned = bool(inferred_cluster_id and inferred_confidence >= auto_assign_threshold)
        source = "ai_inferred" if ai_result else ("heuristic_inferred" if inferred_type else "unmapped")

        _record_inference_candidate(
            email_domain,
            inferred_type,
            round(inferred_confidence, 3),
            source,
            not auto_assigned,
        )

        return {
            "cluster_id": inferred_cluster_id if auto_assigned else None,
            "college_id": None,
            "university_type": inferred_type,
            "verified_by_domain": False,
            "requires_manual_selection": not auto_assigned,
            "cluster_source": source,
            "inference_confidence": round(inferred_confidence, 3),
        }

    cluster_id = _normalize_id(domain_mapping.get("cluster_id"))
    college_id = _normalize_id(domain_mapping.get("college_id"))

    university_type = _normalize_university_type(domain_mapping.get("university_type"))
    if not university_type and college_id:
        college = colleges_collection.find_one({"_id": college_id})
        if college:
            university_type = _normalize_university_type(
                college.get("university_type") or college.get("type")
            )

    if not cluster_id and university_type:
        cluster_id = _default_cluster_for_university_type(university_type)

    return {
        "cluster_id": cluster_id,
        "college_id": college_id,
        "university_type": university_type,
        "verified_by_domain": True,
        "requires_manual_selection": cluster_id is None,
        "cluster_source": "domain_mapping",
        "inference_confidence": 1.0,
    }
