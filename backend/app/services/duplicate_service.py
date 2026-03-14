import re
from difflib import SequenceMatcher
from bson import ObjectId


def _tokens(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(t) > 2}


def _compose_note_text(note: dict, ai_report: dict | None = None) -> str:
    chunks = [
        str(note.get("title", "")),
        str(note.get("description", "")),
        str(note.get("subject", "")),
        " ".join([str(t) for t in (note.get("tags") or [])]),
    ]
    if ai_report:
        chunks.append(str(ai_report.get("summary", "")))
        chunks.append(" ".join([str(t) for t in (ai_report.get("topics") or [])]))
    return " ".join(chunks).strip().lower()


def _similarity_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    seq = SequenceMatcher(a=a[:3000], b=b[:3000]).ratio()
    ta = _tokens(a)
    tb = _tokens(b)
    jaccard = (len(ta.intersection(tb)) / max(len(ta.union(tb)), 1)) if ta and tb else 0.0
    return round((seq * 0.65) + (jaccard * 0.35), 4)


def find_near_duplicates(
    note_id: str,
    notes_collection,
    ai_reports_collection,
    *,
    threshold: float = 0.6,
    scan_limit: int = 400,
    top_k: int = 20,
):
    target = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not target:
        return []
    target_report = ai_reports_collection.find_one({"note_id": target["_id"]}) or {}
    target_text = _compose_note_text(target, target_report)
    if not target_text:
        return []

    others = list(
        notes_collection.find(
            {"_id": {"$ne": ObjectId(note_id)}, "status": {"$in": ["pending", "approved"]}}
        ).limit(scan_limit)
    )
    if not others:
        return []

    # Batch-fetch all AI reports in one query instead of N separate find_one calls
    other_ids = [o["_id"] for o in others]
    reports_map = {
        r["note_id"]: r
        for r in ai_reports_collection.find({"note_id": {"$in": other_ids}})
    }

    dupes = []
    for other in others:
        other_report = reports_map.get(other["_id"]) or {}
        score = _similarity_score(target_text, _compose_note_text(other, other_report))
        if score >= threshold:
            dupes.append(
                {
                    "note_id": str(other["_id"]),
                    "title": other.get("title"),
                    "subject": other.get("subject"),
                    "similarity": score,
                }
            )
    dupes.sort(key=lambda row: row["similarity"], reverse=True)
    return dupes[:top_k]
