import time
import secrets
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    class_spaces_collection,
    space_memberships_collection,
    space_announcements_collection,
    space_notes_collection,
    notes_collection,
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/spaces", tags=["Class Spaces"])

PRIVILEGED_ROLES = {"owner", "moderator"}


# ── Pydantic models ────────────────────────────────────────────────────────────

class SpaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    dept: str
    semester: int
    section: Optional[str] = None
    is_private: bool = True


class SpaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=80)
    dept: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None


class AnnouncementCreate(BaseModel):
    message: str = Field(min_length=2, max_length=500)


class ShareNoteBody(BaseModel):
    note_id: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_space_or_404(space_id: str) -> dict:
    if not ObjectId.is_valid(space_id):
        raise HTTPException(status_code=400, detail="Invalid space id")
    space = class_spaces_collection.find_one({"_id": ObjectId(space_id)})
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


def _get_membership_or_403(space_oid: ObjectId, user_oid: ObjectId) -> dict:
    membership = space_memberships_collection.find_one({"space_id": space_oid, "user_id": user_oid})
    if not membership:
        raise HTTPException(status_code=403, detail="Join this space first")
    return membership


def _require_privileged(membership: dict):
    if membership.get("role") not in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Only the space owner or moderator can do this")


def _require_owner(membership: dict):
    if membership.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Only the space owner can do this")


def _member_count(space_oid: ObjectId) -> int:
    return space_memberships_collection.count_documents({"space_id": space_oid})


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/")
def create_space(data: SpaceCreate, current_user=Depends(get_current_user)):
    invite_code = secrets.token_hex(4)  # 8 lowercase hex chars
    space = {
        "name": data.name.strip(),
        "dept": data.dept.upper().strip(),
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
    return {"id": str(res.inserted_id), "invite_code": invite_code, "message": "Space created"}


@router.get("/my")
def my_spaces(current_user=Depends(get_current_user)):
    user_oid = ObjectId(current_user["id"])
    member_rows = list(space_memberships_collection.find({"user_id": user_oid}))
    if not member_rows:
        return []
    space_ids = [m["space_id"] for m in member_rows]
    role_by_space = {str(m["space_id"]): m.get("role", "member") for m in member_rows}
    spaces = list(class_spaces_collection.find({"_id": {"$in": space_ids}}).sort("created_at", -1))
    out = []
    for s in spaces:
        sid = s["_id"]
        out.append(
            {
                "id": str(sid),
                "name": s.get("name"),
                "dept": s.get("dept"),
                "semester": s.get("semester"),
                "section": s.get("section"),
                "is_private": s.get("is_private", True),
                "invite_code": s.get("invite_code"),
                "role": role_by_space.get(str(sid), "member"),
                "member_count": _member_count(sid),
            }
        )
    return out


@router.get("/{space_id}")
def get_space(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    return {
        "id": str(space_oid),
        "name": space.get("name"),
        "dept": space.get("dept"),
        "semester": space.get("semester"),
        "section": space.get("section"),
        "is_private": space.get("is_private", True),
        "invite_code": space.get("invite_code"),
        "created_at": space.get("created_at"),
        "role": membership.get("role", "member"),
        "member_count": _member_count(space_oid),
    }


@router.patch("/{space_id}")
def update_space(space_id: str, data: SpaceUpdate, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_owner(membership)

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in updates:
        updates["name"] = updates["name"].strip()
    if "dept" in updates:
        updates["dept"] = updates["dept"].upper().strip()

    class_spaces_collection.update_one({"_id": space_oid}, {"$set": updates})
    return {"message": "Space updated"}


@router.delete("/{space_id}")
def delete_space(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_owner(membership)

    space_memberships_collection.delete_many({"space_id": space_oid})
    space_announcements_collection.delete_many({"space_id": space_oid})
    space_notes_collection.delete_many({"space_id": space_oid})
    class_spaces_collection.delete_one({"_id": space_oid})
    return {"message": "Space deleted"}


@router.post("/join/{invite_code}")
def join_space(invite_code: str, current_user=Depends(get_current_user)):
    # Codes are stored as lowercase hex — normalise input
    code = invite_code.strip().lower()
    space = class_spaces_collection.find_one({"invite_code": code})
    if not space:
        raise HTTPException(status_code=404, detail="Invite code not found")

    user_oid = ObjectId(current_user["id"])
    if space_memberships_collection.find_one({"space_id": space["_id"], "user_id": user_oid}):
        raise HTTPException(status_code=409, detail="You are already a member of this space")

    space_memberships_collection.insert_one(
        {
            "space_id": space["_id"],
            "user_id": user_oid,
            "role": "member",
            "created_at": int(time.time()),
        }
    )
    return {"message": "Joined space", "space_id": str(space["_id"])}


@router.post("/{space_id}/leave")
def leave_space(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    user_oid = ObjectId(current_user["id"])
    membership = _get_membership_or_403(space_oid, user_oid)

    if membership.get("role") == "owner":
        # Prevent orphaning the space — must transfer ownership or delete
        other_members = space_memberships_collection.count_documents(
            {"space_id": space_oid, "user_id": {"$ne": user_oid}}
        )
        if other_members > 0:
            raise HTTPException(
                status_code=400,
                detail="Transfer ownership before leaving, or delete the space if you are the sole owner",
            )
        # Owner is alone — delete the whole space
        space_memberships_collection.delete_many({"space_id": space_oid})
        space_announcements_collection.delete_many({"space_id": space_oid})
        space_notes_collection.delete_many({"space_id": space_oid})
        class_spaces_collection.delete_one({"_id": space_oid})
        return {"message": "Space deleted (you were the sole member)"}

    space_memberships_collection.delete_one({"space_id": space_oid, "user_id": user_oid})
    return {"message": "Left space"}


@router.post("/{space_id}/transfer-ownership/{new_owner_id}")
def transfer_ownership(space_id: str, new_owner_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_owner(membership)

    if not ObjectId.is_valid(new_owner_id):
        raise HTTPException(status_code=400, detail="Invalid new owner id")
    new_owner_oid = ObjectId(new_owner_id)

    target = space_memberships_collection.find_one({"space_id": space_oid, "user_id": new_owner_oid})
    if not target:
        raise HTTPException(status_code=404, detail="Target user is not a member of this space")

    # Demote current owner → member, promote target → owner
    space_memberships_collection.update_one(
        {"space_id": space_oid, "user_id": ObjectId(current_user["id"])},
        {"$set": {"role": "member"}},
    )
    space_memberships_collection.update_one(
        {"space_id": space_oid, "user_id": new_owner_oid},
        {"$set": {"role": "owner"}},
    )
    return {"message": "Ownership transferred"}


# ── Members ────────────────────────────────────────────────────────────────────

@router.get("/{space_id}/members")
def list_members(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    rows = list(space_memberships_collection.find({"space_id": space_oid}).sort("created_at", 1))
    user_ids = [r["user_id"] for r in rows]
    from app.database import users_collection
    users = {str(u["_id"]): u for u in users_collection.find({"_id": {"$in": user_ids}}, {"name": 1, "email": 1})}

    out = []
    for r in rows:
        uid = str(r["user_id"])
        u = users.get(uid, {})
        out.append(
            {
                "user_id": uid,
                "name": u.get("name", "Unknown"),
                "email": u.get("email", ""),
                "role": r.get("role", "member"),
                "joined_at": r.get("created_at"),
            }
        )
    return out


@router.delete("/{space_id}/members/{target_user_id}")
def kick_member(space_id: str, target_user_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_privileged(membership)

    if not ObjectId.is_valid(target_user_id):
        raise HTTPException(status_code=400, detail="Invalid user id")
    target_oid = ObjectId(target_user_id)

    if target_oid == ObjectId(current_user["id"]):
        raise HTTPException(status_code=400, detail="Use the leave endpoint to exit the space")

    target_membership = space_memberships_collection.find_one({"space_id": space_oid, "user_id": target_oid})
    if not target_membership:
        raise HTTPException(status_code=404, detail="User is not a member of this space")

    # Moderators cannot kick the owner or other moderators
    if membership.get("role") == "moderator" and target_membership.get("role") in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Moderators can only kick regular members")

    space_memberships_collection.delete_one({"space_id": space_oid, "user_id": target_oid})
    return {"message": "Member removed"}


@router.patch("/{space_id}/members/{target_user_id}/role")
def update_member_role(
    space_id: str,
    target_user_id: str,
    role: str,
    current_user=Depends(get_current_user),
):
    if role not in {"member", "moderator"}:
        raise HTTPException(status_code=400, detail="Role must be 'member' or 'moderator'")

    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_owner(membership)

    if not ObjectId.is_valid(target_user_id):
        raise HTTPException(status_code=400, detail="Invalid user id")
    target_oid = ObjectId(target_user_id)

    target = space_memberships_collection.find_one({"space_id": space_oid, "user_id": target_oid})
    if not target:
        raise HTTPException(status_code=404, detail="User is not a member of this space")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot demote the owner. Use transfer-ownership instead")

    space_memberships_collection.update_one(
        {"space_id": space_oid, "user_id": target_oid},
        {"$set": {"role": role}},
    )
    return {"message": f"Role updated to {role}"}


@router.post("/{space_id}/regenerate-invite")
def regenerate_invite(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_owner(membership)

    new_code = secrets.token_hex(4)
    class_spaces_collection.update_one({"_id": space_oid}, {"$set": {"invite_code": new_code}})
    return {"invite_code": new_code, "message": "Invite code regenerated"}


# ── Announcements ──────────────────────────────────────────────────────────────

@router.get("/{space_id}/announcements")
def list_announcements(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    rows = list(space_announcements_collection.find({"space_id": space_oid}).sort("created_at", -1).limit(50))
    from app.database import users_collection
    user_ids = list({r["created_by"] for r in rows})
    users = {str(u["_id"]): u.get("name", "Unknown") for u in users_collection.find({"_id": {"$in": user_ids}}, {"name": 1})}

    out = []
    for r in rows:
        out.append(
            {
                "id": str(r["_id"]),
                "message": r.get("message"),
                "created_by": str(r.get("created_by")),
                "created_by_name": users.get(str(r.get("created_by")), "Unknown"),
                "created_at": r.get("created_at"),
            }
        )
    return out


@router.post("/{space_id}/announcements")
def post_announcement(space_id: str, data: AnnouncementCreate, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))
    _require_privileged(membership)

    res = space_announcements_collection.insert_one(
        {
            "space_id": space_oid,
            "message": data.message.strip(),
            "created_by": ObjectId(current_user["id"]),
            "created_at": int(time.time()),
        }
    )
    return {"id": str(res.inserted_id), "message": "Announcement posted"}


@router.delete("/{space_id}/announcements/{announcement_id}")
def delete_announcement(space_id: str, announcement_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    if not ObjectId.is_valid(announcement_id):
        raise HTTPException(status_code=400, detail="Invalid announcement id")
    ann_oid = ObjectId(announcement_id)

    ann = space_announcements_collection.find_one({"_id": ann_oid, "space_id": space_oid})
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Owner/moderator can delete any; regular member can delete only their own
    is_author = str(ann.get("created_by")) == current_user["id"]
    if not is_author and membership.get("role") not in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Not allowed to delete this announcement")

    space_announcements_collection.delete_one({"_id": ann_oid})
    return {"message": "Announcement deleted"}


# ── Shared Notes ───────────────────────────────────────────────────────────────

@router.get("/{space_id}/notes")
def list_space_notes(space_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    rows = list(space_notes_collection.find({"space_id": space_oid}).sort("shared_at", -1).limit(50))
    note_ids = [r["note_id"] for r in rows]
    notes = {
        str(n["_id"]): n
        for n in notes_collection.find(
            {"_id": {"$in": note_ids}},
            {"title": 1, "subject": 1, "dept": 1, "semester": 1, "is_paid": 1, "price": 1},
        )
    }

    from app.database import users_collection
    user_ids = list({r["shared_by"] for r in rows})
    users = {str(u["_id"]): u.get("name", "Unknown") for u in users_collection.find({"_id": {"$in": user_ids}}, {"name": 1})}

    out = []
    for r in rows:
        note = notes.get(str(r["note_id"]), {})
        out.append(
            {
                "id": str(r["_id"]),
                "note_id": str(r["note_id"]),
                "title": note.get("title", "Deleted Note"),
                "subject": note.get("subject"),
                "dept": note.get("dept"),
                "semester": note.get("semester"),
                "is_paid": note.get("is_paid", False),
                "price": note.get("price"),
                "shared_by": str(r["shared_by"]),
                "shared_by_name": users.get(str(r["shared_by"]), "Unknown"),
                "shared_at": r.get("shared_at"),
            }
        )
    return out


@router.post("/{space_id}/notes")
def share_note_to_space(space_id: str, body: ShareNoteBody, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    if not ObjectId.is_valid(body.note_id):
        raise HTTPException(status_code=400, detail="Invalid note id")
    note_oid = ObjectId(body.note_id)

    note = notes_collection.find_one({"_id": note_oid, "status": "approved"})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not approved")

    # Prevent duplicate shares
    existing = space_notes_collection.find_one({"space_id": space_oid, "note_id": note_oid})
    if existing:
        raise HTTPException(status_code=409, detail="This note is already shared in this space")

    res = space_notes_collection.insert_one(
        {
            "space_id": space_oid,
            "note_id": note_oid,
            "shared_by": ObjectId(current_user["id"]),
            "shared_at": int(time.time()),
        }
    )
    return {"id": str(res.inserted_id), "message": "Note shared to space"}


@router.delete("/{space_id}/notes/{share_id}")
def remove_shared_note(space_id: str, share_id: str, current_user=Depends(get_current_user)):
    space = _get_space_or_404(space_id)
    space_oid = space["_id"]
    membership = _get_membership_or_403(space_oid, ObjectId(current_user["id"]))

    if not ObjectId.is_valid(share_id):
        raise HTTPException(status_code=400, detail="Invalid share id")

    share = space_notes_collection.find_one({"_id": ObjectId(share_id), "space_id": space_oid})
    if not share:
        raise HTTPException(status_code=404, detail="Shared note not found")

    is_sharer = str(share.get("shared_by")) == current_user["id"]
    if not is_sharer and membership.get("role") not in PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Not allowed to remove this shared note")

    space_notes_collection.delete_one({"_id": ObjectId(share_id)})
    return {"message": "Shared note removed"}
