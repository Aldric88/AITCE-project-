from bson import ObjectId
from fastapi import APIRouter, Depends
from app.database import notes_collection, purchases_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/seller", tags=["Seller Dashboard"])

@router.get("/dashboard")
def seller_dashboard(current_user=Depends(get_current_user)):
    # notes uploaded by seller
    my_notes = list(
        notes_collection.find(
            {"uploader_id": ObjectId(current_user["id"])},
            {"title": 1, "subject": 1, "price": 1, "is_paid": 1},
        )
    )

    note_ids = [n["_id"] for n in my_notes]
    if not note_ids:
        return {
            "seller_id": current_user["id"],
            "total_notes": 0,
            "total_sales": 0,
            "total_earnings": 0,
            "top_notes": [],
        }

    sales_by_note = {}
    total_sales = 0
    total_earnings = 0
    for row in purchases_collection.aggregate(
        [
            {"$match": {"note_id": {"$in": note_ids}, "status": "success"}},
            {
                "$group": {
                    "_id": "$note_id",
                    "sales": {"$sum": 1},
                    "earnings": {"$sum": {"$toInt": {"$ifNull": ["$amount", 0]}}},
                }
            },
        ]
    ):
        nid = row["_id"]
        sales = int(row.get("sales", 0))
        earnings = int(row.get("earnings", 0))
        sales_by_note[nid] = {"sales": sales, "earnings": earnings}
        total_sales += sales
        total_earnings += earnings

    top_notes = []
    for n in my_notes:
        note_sales = sales_by_note.get(n["_id"], {}).get("sales", 0)
        top_notes.append({
            "id": str(n["_id"]),
            "title": n.get("title"),
            "subject": n.get("subject"),
            "price": n.get("price", 0),
            "is_paid": n.get("is_paid", False),
            "sales": note_sales
        })

    top_notes = sorted(top_notes, key=lambda x: x["sales"], reverse=True)[:10]

    return {
        "seller_id": current_user["id"],
        "total_notes": len(my_notes),
        "total_sales": total_sales,
        "total_earnings": total_earnings,
        "top_notes": top_notes
    }
