import time
import secrets
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import class_spaces_collection, space_memberships_collection, space_announcements_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/spaces", tags=["Class Spaces"])


class SpaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    dept: str
    semester: int
    section: Optional[str] = None
    is_private: bool = True


class AnnouncementCreate(BaseModel):
    message: str = Field(min_length=2, max_length=500)


def _space_membership(space_id: ObjectId, user_id: ObjectId):
    return space_memberships_collection.find_one({"space_id": space_id, "user_id": user_id})


@router.post("/")
def create_space(data: SpaceCreate, current_user=Depends(get_current_user)):
    invite_code = secrets.token_hex(4)
    space = {
        "name": data.name.strip(),
        "dept": data.dept,
        "semester": data.semester,
        "section": data.section,
        "is_private": data.is_private,
        "invite_code": invite_code,
        "created_by": ObjectId(current_user["id"]),
        "created_at": int(time.time()),
    }
    res = class_spaces_collection.insert_one(space)
    space_memberships_collection.insert_one(
        {
            "space_id": res.inserted_id,
            "user_id": ObjectId(current_user["id"]),
            "role": "owner",
            "created_at": int(time.time()),
        }
    )
    return {"id": str(res.inserted_id), "invite_code": invite_code, "message": "Space created ✅"}


@router.get("/my")
def my_spaces(current_user=Depends(get_current_user)):
    member_rows = list(space_memberships_collection.find({"user_id": ObjectId(current_user["id"])}))
    space_ids = [m["space_id"] for m in member_rows]
    if not space_ids:
        return []
    role_by_space = {str(m["space_id"]): m.get("role", "member") for m in member_rows}
    spaces = list(class_spaces_collection.find({"_id": {"$in": space_ids}}).sort("created_at", -1))
    out = []
    for s in spaces:
        out.append(
            {
                "id": str(s["_id"]),
                "name": s.get("name"),
                "dept": s.get("dept"),
                "semester": s.get("semester"),
                "section": s.get("section"),
                "is_private": s.get("is_private", True),
                "invite_code": s.get("invite_code"),
                "role": role_by_space.get(str(s["_id"]), "member"),
            }
        )
    return out


@router.post("/join/{invite_code}")
def join_space(invite_code: str, current_user=Depends(get_current_user)):
    space = class_spaces_collection.find_one({"invite_code": invite_code.lower()})
    if not space:
        space = class_spaces_collection.find_one({"invite_code": invite_code})
    if not space:
        raise HTTPException(status_code=404, detail="Invite code not found")

    user_oid = ObjectId(current_user["id"])
    if _space_membership(space["_id"], user_oid):
        return {"message": "Already joined ✅", "space_id": str(space["_id"])}

    space_memberships_collection.insert_one(
        {
            "space_id": space["_id"],
            "user_id": user_oid,
            "role": "member",
            "created_at": int(time.time()),
        }
    )
    return {"message": "Joined space ✅", "space_id": str(space["_id"])}


@router.get("/{space_id}/announcements")
def list_announcements(space_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(space_id):
        raise HTTPException(status_code=400, detail="Invalid space id")
    space_oid = ObjectId(space_id)
    if not _space_membership(space_oid, ObjectId(current_user["id"])):
        raise HTTPException(status_code=403, detail="Join this space first")
    rows = list(space_announcements_collection.find({"space_id": space_oid}).sort("created_at", -1).limit(100))
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "message": r.get("message"),
                "created_by": str(r.get("created_by")),
                "created_at": r.get("created_at"),
            }
        )
    return out


@router.post("/{space_id}/announcements")
def post_announcement(space_id: str, data: AnnouncementCreate, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(space_id):
        raise HTTPException(status_code=400, detail="Invalid space id")
    space_oid = ObjectId(space_id)
    membership = _space_membership(space_oid, ObjectId(current_user["id"]))
    if not membership:
        raise HTTPException(status_code=403, detail="Join this space first")
    if membership.get("role") not in {"owner", "moderator"}:
        raise HTTPException(status_code=403, detail="Only space owner can post announcements")
    res = space_announcements_collection.insert_one(
        {
            "space_id": space_oid,
            "message": data.message.strip(),
            "created_by": ObjectId(current_user["id"]),
            "created_at": int(time.time()),
        }
    )
    return {"id": str(res.inserted_id), "message": "Announcement posted ✅"}
