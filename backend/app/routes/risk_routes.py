from fastapi import APIRouter, Depends, Query
from bson import ObjectId

from app.database import (
    users_collection,
    notes_collection,
    reports_collection,
    disputes_collection,
    requests_collection,
    purchases_collection,
)
from app.utils.dependencies import get_current_user, require_role
from app.services.risk_service import compute_user_risk_score

router = APIRouter(prefix="/risk", tags=["Risk"])


def _deps():
    return {
        "users_collection": users_collection,
        "notes_collection": notes_collection,
        "reports_collection": reports_collection,
        "disputes_collection": disputes_collection,
        "requests_collection": requests_collection,
        "purchases_collection": purchases_collection,
    }


@router.get("/me")
def my_risk(current_user=Depends(get_current_user)):
    return compute_user_risk_score(current_user["id"], _deps())


@router.post("/recompute/{user_id}")
def recompute_user_risk(user_id: str, current_user=Depends(require_role(["admin", "moderator"]))):
    return compute_user_risk_score(user_id, _deps())


@router.get("/users")
def list_high_risk_users(
    min_score: int = Query(default=45, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(require_role(["admin", "moderator"])),
):
    rows = list(
        users_collection.find(
            {"risk_score": {"$gte": min_score}},
            {"name": 1, "email": 1, "dept": 1, "risk_score": 1, "risk_level": 1, "role": 1},
        )
        .sort("risk_score", -1)
        .limit(limit)
    )
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "name": r.get("name"),
                "email": r.get("email"),
                "dept": r.get("dept"),
                "role": r.get("role", "student"),
                "risk_score": int(r.get("risk_score", 0)),
                "risk_level": r.get("risk_level", "low"),
            }
        )
    return {"count": len(out), "users": out}
