from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional

from app.database import users_collection
from app.database import notes_collection, purchases_collection, reviews_collection, view_sessions_collection
from app.database import (
    college_domains_collection,
    colleges_collection,
    clusters_collection,
    cluster_inference_candidates_collection,
)
from app.utils.dependencies import require_role
from app.models.user_model import user_helper
from bson import ObjectId
import time

router = APIRouter(prefix="/admin", tags=["Admin"])

RoleType = Literal["student", "moderator", "admin"]


class UpdateUserRoleRequest(BaseModel):
    role: RoleType


class BanUserRequest(BaseModel):
    is_active: bool  # false = banned, true = unbanned


class ApproveDomainCandidateRequest(BaseModel):
    college_name: str
    university_type: Literal["anna_affiliated", "autonomous", "deemed"]


class RejectDomainCandidateRequest(BaseModel):
    reason: Optional[str] = None


def _default_cluster_for_university_type(university_type: str):
    cluster = clusters_collection.find_one(
        {"university_type": university_type, "is_default": True}
    )
    if cluster:
        return cluster
    return clusters_collection.find_one({"type": university_type})


def _candidate_helper(doc: dict):
    return {
        "id": str(doc["_id"]),
        "domain": doc.get("domain"),
        "last_inferred_university_type": doc.get("last_inferred_university_type"),
        "last_confidence": doc.get("last_confidence"),
        "last_source": doc.get("last_source"),
        "inference_count": int(doc.get("inference_count", 0)),
        "requires_manual_selection": bool(doc.get("requires_manual_selection", True)),
        "review_status": doc.get("review_status", "pending"),
        "review_reason": doc.get("review_reason"),
        "reviewed_by": doc.get("reviewed_by"),
        "updated_at": int(doc.get("updated_at", 0)),
        "created_at": int(doc.get("created_at", 0)),
    }


@router.get("/users")
def get_all_users(
    role: Optional[str] = Query(default=None),
    dept: Optional[str] = Query(default=None),
    active: Optional[bool] = Query(default=None),
    current_user=Depends(require_role(["admin"])),
):
    query = {}

    if role:
        query["role"] = role
    if dept:
        query["dept"] = dept
    if active is not None:
        query["is_active"] = active

    users = users_collection.find(query).sort("name", 1)
    return {
        "count": users_collection.count_documents(query),
        "users": [user_helper(u) for u in users],
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    data: UpdateUserRoleRequest,
    current_user=Depends(require_role(["admin"])),
):
    # Validate user_id format
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Optional safety: prevent admin from demoting themselves
    if str(user["_id"]) == current_user["id"] and data.role != "admin":
        raise HTTPException(
            status_code=400, detail="Admin cannot change their own role"
        )

    users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"role": data.role}}
    )

    return {
        "message": f"Role updated successfully to '{data.role}'",
        "user_id": user_id,
    }


@router.patch("/users/{user_id}/ban")
def ban_or_unban_user(
    user_id: str,
    data: BanUserRequest,
    current_user=Depends(require_role(["admin"])),
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # prevent admin banning themselves
    if str(user["_id"]) == current_user["id"] and data.is_active is False:
        raise HTTPException(
            status_code=400, detail="Admin cannot ban themselves"
        )

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": data.is_active}},
    )

    return {
        "message": "User status updated",
        "user_id": user_id,
        "is_active": data.is_active,
    }


@router.get("/analytics/funnel")
def analytics_funnel(days: int = Query(default=30, ge=1, le=365), current_user=Depends(require_role(["admin"]))):
    since = int(time.time()) - (days * 24 * 60 * 60)
    note_stats = list(
        notes_collection.aggregate(
            [
                {"$match": {"status": "approved"}},
                {
                    "$group": {
                        "_id": "$uploader_id",
                        "notes": {"$sum": 1},
                        "views": {"$sum": {"$toInt": {"$ifNull": ["$views", 0]}}},
                    }
                },
            ]
        )
    )
    approved_notes_count = sum(int(r.get("notes", 0)) for r in note_stats)
    total_views = sum(int(r.get("views", 0)) for r in note_stats)
    previews = view_sessions_collection.count_documents({"created_at": {"$gte": since}})
    reviews = reviews_collection.count_documents({"created_at": {"$gte": since}})

    # Single $facet: purchase count + sales-by-creator in one round-trip
    purchase_facet = list(
        purchases_collection.aggregate(
            [
                {"$match": {"status": "success", "created_at": {"$gte": since}}},
                {
                    "$facet": {
                        "count": [{"$count": "n"}],
                        "sales_by_creator": [
                            {
                                "$lookup": {
                                    "from": "notes",
                                    "localField": "note_id",
                                    "foreignField": "_id",
                                    "as": "note",
                                }
                            },
                            {"$unwind": "$note"},
                            {"$match": {"note.status": "approved"}},
                            {
                                "$group": {
                                    "_id": "$note.uploader_id",
                                    "sales": {"$sum": {"$toInt": {"$ifNull": ["$amount", 0]}}},
                                }
                            },
                        ],
                    }
                },
            ]
        )
    )
    purchase_facet_result = purchase_facet[0] if purchase_facet else {}
    purchases = (purchase_facet_result.get("count") or [{}])[0].get("n", 0)
    sales_stats = purchase_facet_result.get("sales_by_creator", [])

    top_creators = []
    by_creator = {}
    for row in note_stats:
        creator_id = row.get("_id")
        if not creator_id:
            continue
        cid = str(creator_id)
        by_creator[cid] = {
            "creator_id": cid,
            "notes": int(row.get("notes", 0)),
            "views": int(row.get("views", 0)),
            "sales": 0,
        }

    for row in sales_stats:
        creator_id = row.get("_id")
        if not creator_id:
            continue
        cid = str(creator_id)
        by_creator.setdefault(cid, {"creator_id": cid, "notes": 0, "views": 0, "sales": 0})
        by_creator[cid]["sales"] = int(row.get("sales", 0))

    if by_creator:
        creator_oids = [ObjectId(cid) for cid in by_creator.keys() if ObjectId.is_valid(cid)]
        user_map = {
            str(u["_id"]): u
            for u in users_collection.find({"_id": {"$in": creator_oids}}, {"name": 1, "dept": 1})
        }
        for cid, data in by_creator.items():
            u = user_map.get(cid, {})
            data["creator_name"] = u.get("name", "Unknown")
            data["dept"] = u.get("dept", "")
            top_creators.append(data)

    top_creators.sort(key=lambda x: x["sales"], reverse=True)

    # Single $facet: cohort-by-dept + churn count in one round-trip
    user_facet = list(
        users_collection.aggregate(
            [
                {
                    "$facet": {
                        "cohort": [
                            {"$match": {"is_active": True}},
                            {"$group": {"_id": "$dept", "count": {"$sum": 1}}},
                        ],
                        "churn": [
                            {"$match": {"is_active": False}},
                            {"$count": "n"},
                        ],
                    }
                }
            ]
        )
    )
    user_facet_result = user_facet[0] if user_facet else {}
    cohort = {(r.get("_id") or "Unknown"): r["count"] for r in user_facet_result.get("cohort", [])}
    churn = (user_facet_result.get("churn") or [{}])[0].get("n", 0)
    return {
        "window_days": days,
        "funnel": {
            "views": total_views,
            "previews": previews,
            "purchases": purchases,
            "reviews": reviews,
        },
        "cohorts_by_dept": [{"dept": k, "active_users": v} for k, v in sorted(cohort.items(), key=lambda x: x[1], reverse=True)],
        "top_creators": top_creators[:15],
        "churn_signals": {
            "inactive_users": churn,
            "approved_notes": approved_notes_count,
        },
    }


@router.get("/domain-candidates")
def list_domain_candidates(
    review_status: Literal["pending", "approved", "rejected", "all"] = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(require_role(["admin"])),
):
    query = {}
    if review_status != "all":
        query["review_status"] = review_status

    rows = list(
        cluster_inference_candidates_collection.find(query)
        .sort([("updated_at", -1)])
        .limit(limit)
    )
    return {"count": len(rows), "items": [_candidate_helper(r) for r in rows]}


@router.post("/domain-candidates/{domain}/approve")
def approve_domain_candidate(
    domain: str,
    data: ApproveDomainCandidateRequest,
    current_user=Depends(require_role(["admin"])),
):
    domain = domain.strip().lower()
    candidate = cluster_inference_candidates_collection.find_one({"domain": domain})
    if not candidate:
        raise HTTPException(status_code=404, detail="Domain candidate not found")

    cluster = _default_cluster_for_university_type(data.university_type)
    if not cluster:
        raise HTTPException(status_code=400, detail="No default cluster configured for university_type")

    college_update = {
        "name": data.college_name.strip(),
        "university_type": data.university_type,
        "cluster_key": cluster.get("cluster_key"),
        "updated_at": int(time.time()),
    }
    college_result = colleges_collection.update_one(
        {"name": data.college_name.strip()},
        {"$set": college_update, "$setOnInsert": {"created_at": int(time.time())}},
        upsert=True,
    )
    college_doc = colleges_collection.find_one({"name": data.college_name.strip()})
    college_id = college_result.upserted_id or (college_doc or {}).get("_id")

    if not college_id:
        raise HTTPException(status_code=500, detail="Failed to create/read college")

    college_domains_collection.update_one(
        {"domain": domain},
        {
            "$set": {
                "domain": domain,
                "college_id": college_id,
                "cluster_id": cluster["_id"],
                "university_type": data.university_type,
                "is_active": True,
                "updated_at": int(time.time()),
            },
            "$setOnInsert": {"created_at": int(time.time())},
        },
        upsert=True,
    )

    cluster_inference_candidates_collection.update_one(
        {"domain": domain},
        {
            "$set": {
                "review_status": "approved",
                "review_reason": None,
                "reviewed_by": current_user["email"],
                "reviewed_at": int(time.time()),
                "requires_manual_selection": False,
                "updated_at": int(time.time()),
            }
        },
    )

    return {
        "message": "Domain candidate approved and mapped",
        "domain": domain,
        "college_name": data.college_name.strip(),
        "university_type": data.university_type,
        "cluster_id": str(cluster["_id"]),
    }


@router.post("/domain-candidates/{domain}/reject")
def reject_domain_candidate(
    domain: str,
    data: RejectDomainCandidateRequest,
    current_user=Depends(require_role(["admin"])),
):
    domain = domain.strip().lower()
    candidate = cluster_inference_candidates_collection.find_one({"domain": domain})
    if not candidate:
        raise HTTPException(status_code=404, detail="Domain candidate not found")

    cluster_inference_candidates_collection.update_one(
        {"domain": domain},
        {
            "$set": {
                "review_status": "rejected",
                "review_reason": data.reason,
                "reviewed_by": current_user["email"],
                "reviewed_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        },
    )
    return {"message": "Domain candidate rejected", "domain": domain}


# ── Upload violation management ───────────────────────────────────────────────

@router.get("/violations")
def list_upload_violations(current_user=Depends(require_role(["admin"]))):
    """List users with upload violations."""
    users = users_collection.find(
        {"upload_violations": {"$gt": 0}},
        {"_id": 1, "name": 1, "email": 1, "upload_violations": 1, "can_upload": 1},
    ).sort("upload_violations", -1)
    return [
        {
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "upload_violations": u.get("upload_violations", 0),
            "can_upload": u.get("can_upload", True),
        }
        for u in users
    ]


@router.post("/violations/{user_id}/reset")
def reset_user_violations(user_id: str, current_user=Depends(require_role(["admin"]))):
    """Reset a user's violation count and restore upload access."""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    result = users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"upload_violations": 0, "can_upload": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Violations reset and upload access restored."}

