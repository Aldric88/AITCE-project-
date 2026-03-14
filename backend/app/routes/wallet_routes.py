from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from typing import Optional
import time as _time

from app.database import leaderboard_collection, users_collection
from app.utils.dependencies import get_current_user, require_role
from app.services.points_service import get_wallet_balance, award_points
from app.config import settings

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.get("/me")
def wallet_me(current_user=Depends(get_current_user)):
    return {
        "user_id": current_user["id"],
        "wallet_points": get_wallet_balance(current_user["id"]),
    }


@router.get("/transactions")
def wallet_transactions(
    limit: int = 50,
    txn_type: Optional[str] = Query(default=None, pattern="^(credit|debit)$"),
    reason: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    query: dict = {"user_id": ObjectId(current_user["id"])}
    if txn_type:
        query["txn_type"] = txn_type
    if reason:
        query["reason"] = reason  # exact match — prevents regex injection
    rows = list(
        leaderboard_collection.find(query)
        .sort("created_at", -1)
        .limit(max(1, min(limit, 200)))
    )
    return {
        "wallet_points": get_wallet_balance(current_user["id"]),
        "transactions": [
            {
                "id": str(r["_id"]),
                "points": int(r.get("points", 0)),
                "txn_type": r.get("txn_type", "credit" if int(r.get("points", 0)) >= 0 else "debit"),
                "reason": r.get("reason", "unknown"),
                "meta": r.get("meta", {}),
                "created_at": int(r.get("created_at", 0)),
            }
            for r in rows
        ],
    }


@router.get("/transactions/export")
def export_wallet_transactions(current_user=Depends(get_current_user)):
    rows = list(
        leaderboard_collection.find({"user_id": ObjectId(current_user["id"])})
        .sort("created_at", -1)
        .limit(1000)
    )
    lines = ["id,points,txn_type,reason,created_at"]
    for r in rows:
        ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(int(r.get("created_at", 0))))
        lines.append(
            f"{r['_id']},{int(r.get('points', 0))},{r.get('txn_type', '')},\"{r.get('reason', '')}\",{ts}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wallet_transactions.csv"},
    )


@router.post("/bootstrap-initial")
def bootstrap_initial_points(
    limit: int = Query(default=500, ge=1, le=5000),
    current_user=Depends(require_role(["admin"])),
):
    amount = int(settings.INITIAL_WALLET_POINTS)
    if amount <= 0:
        return {"awarded": 0, "detail": "INITIAL_WALLET_POINTS is disabled"}

    reason = "signup_bonus_backfill:v1"
    candidates = list(
        users_collection.find(
            {"$or": [{"wallet_points": {"$exists": False}}, {"wallet_points": {"$lte": 0}}]},
            {"_id": 1},
        ).limit(limit)
    )
    from app.services.points_service import MAX_WALLET_POINTS

    awarded = 0
    for user in candidates:
        user_id = user.get("_id")
        if not user_id:
            continue
        # Atomic upsert: only inserts the ledger row if none exists for this reason.
        # Eliminates the find_one + insert race under concurrent admin calls.
        result = leaderboard_collection.update_one(
            {"user_id": user_id, "reason": reason},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "points": amount,
                    "reason": reason,
                    "txn_type": "credit",
                    "meta": {"source": "wallet.bootstrap"},
                    "created_at": int(_time.time()),
                }
            },
            upsert=True,
        )
        if result.upserted_id:
            users_collection.update_one({"_id": user_id}, {"$inc": {"wallet_points": amount}})
            users_collection.update_one(
                {"_id": user_id, "wallet_points": {"$gt": MAX_WALLET_POINTS}},
                {"$set": {"wallet_points": MAX_WALLET_POINTS}},
            )
            awarded += 1

    return {"awarded": awarded, "points_each": amount, "reason": reason}
