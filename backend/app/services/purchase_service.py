from bson import ObjectId


def purchase_query(user_id: str, note_id: str) -> dict:
    return {
        "note_id": ObjectId(note_id),
        "$or": [
            {"buyer_id": ObjectId(user_id), "status": "success"},
            {"user_id": ObjectId(user_id), "status": {"$in": ["success", "paid", "free"]}},
        ],
    }


def list_user_purchase_rows(user_id: str, purchases_collection, notes_collection) -> list[dict]:
    rows = list(
        purchases_collection.find(
            {
                "$or": [
                    {"buyer_id": ObjectId(user_id)},
                    {"user_id": ObjectId(user_id)},
                ]
            }
        ).sort("_id", -1)
    )

    note_ids = [p.get("note_id") for p in rows if isinstance(p.get("note_id"), ObjectId)]
    notes_by_id = {}
    if note_ids:
        for note in notes_collection.find(
            {"_id": {"$in": note_ids}},
            {
                "title": 1,
                "subject": 1,
                "unit": 1,
                "semester": 1,
                "dept": 1,
                "description": 1,
                "is_paid": 1,
                "price": 1,
            },
        ):
            notes_by_id[note["_id"]] = {
                "id": str(note["_id"]),
                "title": note.get("title", "Untitled"),
                "subject": note.get("subject", ""),
                "unit": note.get("unit"),
                "semester": note.get("semester"),
                "dept": note.get("dept"),
                "description": note.get("description"),
                "is_paid": note.get("is_paid", False),
                "price": note.get("price", 0),
            }

    out = []
    for p in rows:
        note_doc = notes_by_id.get(p.get("note_id"))
        amount = p.get("amount", 0)
        purchase_type = p.get("purchase_type") or ("free" if amount == 0 else "paid")
        out.append(
            {
                "id": str(p["_id"]),
                "purchase_id": str(p["_id"]),
                "note_id": str(p["note_id"]),
                "amount": amount,
                "status": p.get("status"),
                "created_at": p.get("created_at"),
                "unlocked_type": purchase_type,
                "unlocked_at": p.get("created_at"),
                "note": note_doc,
            }
        )
    return out
