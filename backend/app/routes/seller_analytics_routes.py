from bson import ObjectId
from fastapi import APIRouter, Depends
from app.database import notes_collection, purchases_collection
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/seller", tags=["Seller Dashboard"])

@router.get("/dashboard")
def seller_dashboard(current_user=Depends(get_current_user)):
    # notes uploaded by seller
    my_notes = list(notes_collection.find({"uploader_id": ObjectId(current_user["id"])}))

    note_ids = [n["_id"] for n in my_notes]

    # purchases of seller notes
    sales = list(purchases_collection.find({"note_id": {"$in": note_ids}, "status": "success"}))

    total_sales = len(sales)
    total_earnings = sum([s.get("amount", 0) for s in sales])

    top_notes = []
    for n in my_notes:
        note_sales = purchases_collection.count_documents({"note_id": n["_id"], "status": "success"})
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
