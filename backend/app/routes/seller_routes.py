from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.database import users_collection
from app.utils.dependencies import require_role

router = APIRouter(prefix="/sellers", tags=["Verified Sellers"])


@router.patch("/{user_id}/verify")
def verify_seller(user_id: str, current_user=Depends(require_role(["admin"]))):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verified_seller": True}}
    )

    return {"message": "Seller verified ✅", "user_id": user_id}


@router.patch("/{user_id}/unverify")
def unverify_seller(user_id: str, current_user=Depends(require_role(["admin"]))):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verified_seller": False}}
    )

    return {"message": "Seller unverified ✅", "user_id": user_id}
