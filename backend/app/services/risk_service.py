from bson import ObjectId


def compute_user_risk_score(user_id: str, deps: dict) -> dict:
    user_oid = ObjectId(user_id)
    notes_collection = deps["notes_collection"]
    reports_collection = deps["reports_collection"]
    disputes_collection = deps["disputes_collection"]
    requests_collection = deps["requests_collection"]
    purchases_collection = deps["purchases_collection"]
    users_collection = deps["users_collection"]

    total_notes = notes_collection.count_documents({"uploader_id": user_oid})
    rejected_notes = notes_collection.count_documents({"uploader_id": user_oid, "status": "rejected"})
    reports_against_notes = reports_collection.count_documents({"note_owner_id": user_oid})
    disputes_against_sales = disputes_collection.count_documents({"seller_id": user_oid, "status": "approved"})
    frequent_requests = requests_collection.count_documents({"created_by": user_oid})
    failed_purchases = purchases_collection.count_documents({"buyer_id": user_oid, "status": "failed"})

    rejection_ratio = (rejected_notes / total_notes) if total_notes > 0 else 0.0
    score = 0
    score += min(int(rejection_ratio * 100 * 0.45), 45)
    score += min(reports_against_notes * 4, 20)
    score += min(disputes_against_sales * 6, 20)
    score += min(frequent_requests // 8 * 3, 10)
    score += min(failed_purchases * 2, 10)
    score = max(0, min(score, 100))

    if score >= 80:
        level = "high"
    elif score >= 45:
        level = "medium"
    else:
        level = "low"

    users_collection.update_one(
        {"_id": user_oid},
        {"$set": {"risk_score": score, "risk_level": level}},
    )

    return {
        "user_id": user_id,
        "risk_score": score,
        "risk_level": level,
        "signals": {
            "total_notes": total_notes,
            "rejected_notes": rejected_notes,
            "reports_against_notes": reports_against_notes,
            "approved_disputes_against_sales": disputes_against_sales,
            "requests_count": frequent_requests,
            "failed_purchases": failed_purchases,
        },
    }
