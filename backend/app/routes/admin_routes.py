from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional

from app.database import users_collection
from app.utils.dependencies import require_role
from app.models.user_model import user_helper
from bson import ObjectId

router = APIRouter(prefix="/admin", tags=["Admin"])

RoleType = Literal["student", "moderator", "admin"]


class UpdateUserRoleRequest(BaseModel):
    role: RoleType


class BanUserRequest(BaseModel):
    is_active: bool  # false = banned, true = unbanned


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
