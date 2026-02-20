import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.database import requests_collection, users_collection, notes_collection, reports_collection, disputes_collection, purchases_collection
from app.utils.dependencies import get_current_user
from app.services.risk_service import compute_user_risk_score

router = APIRouter(prefix="/requests", tags=["Note Requests"])


class RequestCreate(BaseModel):
    title: str
    dept: str
    semester: int
    subject: str
    unit: str
    description: Optional[str] = None


@router.post("/")
def create_request(data: RequestCreate, current_user=Depends(get_current_user)):
    if len(data.title.strip()) < 3:
        raise HTTPException(status_code=400, detail="Title too short")
    risk = compute_user_risk_score(
        current_user["id"],
        {
            "users_collection": users_collection,
            "notes_collection": notes_collection,
            "reports_collection": reports_collection,
            "disputes_collection": disputes_collection,
            "requests_collection": requests_collection,
            "purchases_collection": purchases_collection,
        },
    )
    if risk["risk_score"] >= 90:
        raise HTTPException(status_code=403, detail="Account risk too high. Contact support.")

    doc = {
        "title": data.title.strip(),
        "dept": data.dept,
        "semester": data.semester,
        "subject": data.subject,
        "unit": data.unit,
        "description": data.description,
        "status": "open",  # open / closed
        "created_by": ObjectId(current_user["id"]),
        "votes": [],
        "vote_count": 0,
        "created_at": int(time.time())
    }

    res = requests_collection.insert_one(doc)

    return {"message": "Request created ✅", "id": str(res.inserted_id)}


@router.get("/")
def list_requests():
    reqs = requests_collection.find({"status": "open"}).sort("_id", -1)

    out = []
    for r in reqs:
        out.append({
            "id": str(r["_id"]),
            "title": r.get("title"),
            "dept": r.get("dept"),
            "semester": r.get("semester"),
            "subject": r.get("subject"),
            "unit": r.get("unit"),
            "description": r.get("description"),
            "status": r.get("status"),
            "created_by": str(r.get("created_by")) if r.get("created_by") else None,
            "vote_count": int(r.get("vote_count", len(r.get("votes", [])))),
        })
    return out


@router.patch("/{request_id}/close")
def close_request(request_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request_id")

    req = requests_collection.find_one({"_id": ObjectId(request_id)})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # only owner can close
    if str(req["created_by"]) != current_user["id"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "closed"}}
    )

    return {"message": "Request closed ✅"}


@router.post("/{request_id}/vote")
def vote_request(request_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request_id")
    req = requests_collection.find_one({"_id": ObjectId(request_id), "status": "open"})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    user_oid = ObjectId(current_user["id"])
    votes = req.get("votes", [])
    has_voted = user_oid in votes
    if has_voted:
        requests_collection.update_one(
            {"_id": req["_id"]},
            {"$pull": {"votes": user_oid}, "$inc": {"vote_count": -1}},
        )
        return {"message": "Vote removed", "voted": False}
    requests_collection.update_one(
        {"_id": req["_id"]},
        {"$addToSet": {"votes": user_oid}, "$inc": {"vote_count": 1}},
    )
    return {"message": "Voted ✅", "voted": True}


@router.get("/insights/demand-heatmap")
def request_demand_heatmap():
    rows = list(requests_collection.find({"status": "open"}))
    by_subject = {}
    by_unit = {}
    by_dept = {}
    for r in rows:
        s = r.get("subject", "Unknown")
        u = str(r.get("unit", "Unknown"))
        d = r.get("dept", "Unknown")
        by_subject[s] = by_subject.get(s, 0) + 1
        by_unit[u] = by_unit.get(u, 0) + 1
        by_dept[d] = by_dept.get(d, 0) + 1

    top_subjects = sorted(
        [{"subject": k, "count": v} for k, v in by_subject.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:12]
    top_units = sorted(
        [{"unit": k, "count": v} for k, v in by_unit.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:12]
    top_requests = sorted(
        [
            {
                "id": str(r["_id"]),
                "title": r.get("title", ""),
                "subject": r.get("subject", ""),
                "unit": r.get("unit", ""),
                "dept": r.get("dept", ""),
                "vote_count": int(r.get("vote_count", len(r.get("votes", [])))),
            }
            for r in rows
        ],
        key=lambda x: x["vote_count"],
        reverse=True,
    )[:12]

    return {
        "total_open_requests": len(rows),
        "top_subjects": top_subjects,
        "top_units": top_units,
        "by_dept": [{"dept": k, "count": v} for k, v in sorted(by_dept.items(), key=lambda x: x[1], reverse=True)],
        "top_requests": top_requests,
    }
