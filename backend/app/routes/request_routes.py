import time
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.database import (
    requests_collection,
    request_pledges_collection,
    users_collection,
    notes_collection,
    reports_collection,
    disputes_collection,
    purchases_collection,
)
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


class PledgeCreate(BaseModel):
    amount: int = Field(ge=1, le=50000)


def _refresh_bounty_stats(request_oid: ObjectId):
    rows = list(request_pledges_collection.find({"request_id": request_oid}, {"amount": 1}))
    total = sum(int(r.get("amount", 0)) for r in rows)
    count = len(rows)
    requests_collection.update_one(
        {"_id": request_oid},
        {"$set": {"bounty_total": total, "pledge_count": count}},
    )
    return total, count


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
        "bounty_total": 0,
        "pledge_count": 0,
        "created_at": int(time.time())
    }

    res = requests_collection.insert_one(doc)

    return {"message": "Request created ✅", "id": str(res.inserted_id)}


@router.get("/")
def list_requests(current_user=Depends(get_current_user)):
    reqs = requests_collection.find({"status": "open"}, {"votes": 0}).sort("_id", -1)

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
            "vote_count": int(r.get("vote_count", 0)),
            "bounty_total": int(r.get("bounty_total", 0)),
            "pledge_count": int(r.get("pledge_count", 0)),
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


@router.post("/{request_id}/pledge")
def pledge_request(request_id: str, data: PledgeCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request_id")
    request_oid = ObjectId(request_id)
    req = requests_collection.find_one({"_id": request_oid, "status": "open"})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    amount = int(data.amount)
    if amount < 1 or amount > 50000:
        raise HTTPException(status_code=400, detail="Pledge amount must be between INR 1 and INR 50000")

    request_pledges_collection.update_one(
        {"request_id": request_oid, "user_id": ObjectId(current_user["id"])},
        {
            "$set": {
                "amount": amount,
                "updated_at": int(time.time()),
            },
            "$setOnInsert": {
                "created_at": int(time.time()),
            },
        },
        upsert=True,
    )
    total, count = _refresh_bounty_stats(request_oid)
    return {
        "message": "Pledge saved ✅",
        "request_id": request_id,
        "bounty_total": total,
        "pledge_count": count,
    }


@router.delete("/{request_id}/pledge")
def unpledge_request(request_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request_id")
    request_oid = ObjectId(request_id)
    request_pledges_collection.delete_one(
        {"request_id": request_oid, "user_id": ObjectId(current_user["id"])}
    )
    total, count = _refresh_bounty_stats(request_oid)
    return {
        "message": "Pledge removed",
        "request_id": request_id,
        "bounty_total": total,
        "pledge_count": count,
    }


@router.get("/{request_id}/bounty")
def request_bounty(request_id: str):
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request_id")
    request_oid = ObjectId(request_id)
    req = requests_collection.find_one({"_id": request_oid})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    rows = list(
        request_pledges_collection.find({"request_id": request_oid}).sort("amount", -1).limit(20)
    )
    user_ids = [r.get("user_id") for r in rows if r.get("user_id")]
    user_map = {}
    if user_ids:
        for u in users_collection.find({"_id": {"$in": user_ids}}, {"name": 1}):
            user_map[u["_id"]] = u.get("name", "User")

    total = int(req.get("bounty_total", 0))
    if total <= 0:
        total = sum(int(r.get("amount", 0)) for r in rows)
    return {
        "request_id": request_id,
        "bounty_total": total,
        "pledge_count": int(req.get("pledge_count", len(rows))),
        "top_pledges": [
            {
                "user_id": str(r.get("user_id")) if r.get("user_id") else None,
                "user_name": user_map.get(r.get("user_id"), "User"),
                "amount": int(r.get("amount", 0)),
            }
            for r in rows
        ],
    }


@router.get("/insights/demand-heatmap")
def request_demand_heatmap(current_user=Depends(get_current_user)):
    results = list(
        requests_collection.aggregate(
            [
                {"$match": {"status": "open"}},
                {
                    "$facet": {
                        "total": [{"$count": "n"}],
                        "by_subject": [
                            {"$group": {"_id": {"$ifNull": ["$subject", "Unknown"]}, "count": {"$sum": 1}}},
                            {"$sort": {"count": -1}},
                            {"$limit": 12},
                        ],
                        "by_unit": [
                            {"$group": {"_id": {"$toString": {"$ifNull": ["$unit", "Unknown"]}}, "count": {"$sum": 1}}},
                            {"$sort": {"count": -1}},
                            {"$limit": 12},
                        ],
                        "by_dept": [
                            {"$group": {"_id": {"$ifNull": ["$dept", "Unknown"]}, "count": {"$sum": 1}}},
                            {"$sort": {"count": -1}},
                        ],
                        "top_requests": [
                            {"$sort": {"vote_count": -1}},
                            {"$limit": 12},
                            {
                                "$project": {
                                    "title": 1,
                                    "subject": 1,
                                    "unit": 1,
                                    "dept": 1,
                                    "vote_count": 1,
                                    "bounty_total": 1,
                                }
                            },
                        ],
                    }
                },
            ]
        )
    )
    facet = results[0] if results else {}
    return {
        "total_open_requests": (facet.get("total") or [{}])[0].get("n", 0),
        "top_subjects": [{"subject": r["_id"], "count": r["count"]} for r in facet.get("by_subject", [])],
        "top_units": [{"unit": r["_id"], "count": r["count"]} for r in facet.get("by_unit", [])],
        "by_dept": [{"dept": r["_id"], "count": r["count"]} for r in facet.get("by_dept", [])],
        "top_requests": [
            {
                "id": str(r["_id"]),
                "title": r.get("title", ""),
                "subject": r.get("subject", ""),
                "unit": r.get("unit", ""),
                "dept": r.get("dept", ""),
                "vote_count": int(r.get("vote_count", 0)),
                "bounty_total": int(r.get("bounty_total", 0)),
            }
            for r in facet.get("top_requests", [])
        ],
    }
