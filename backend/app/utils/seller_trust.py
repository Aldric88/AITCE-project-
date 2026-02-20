"""
Seller Trust Level Calculation Utility

Calculates seller trust levels based on:
- Total sales count
- Average rating
- Account age
- Dispute rate
"""

from datetime import datetime, timedelta
from bson import ObjectId


def calculate_seller_trust_level(seller_id: ObjectId, db) -> dict:
    """
    Calculate seller trust level and stats.
    
    Returns:
        {
            "trust_level": "new" | "trusted" | "top",
            "total_sales": int,
            "avg_rating": float,
            "account_age_days": int,
            "dispute_rate": float
        }
    """
    from app.database import users_collection, purchases_collection, reviews_collection, disputes_collection
    
    # Get user account age
    user = users_collection.find_one({"_id": seller_id})
    if not user:
        return {
            "trust_level": "new",
            "total_sales": 0,
            "avg_rating": 0,
            "account_age_days": 0,
            "dispute_rate": 0
        }
    
    account_created = user.get("_id").generation_time
    account_age_days = (datetime.utcnow() - account_created).days
    
    # Count total sales (successful purchases of seller's notes)
    pipeline = [
        {
            "$lookup": {
                "from": "notes",
                "localField": "note_id",
                "foreignField": "_id",
                "as": "note"
            }
        },
        {"$unwind": "$note"},
        {
            "$match": {
                "note.uploader_id": seller_id,
                "status": "success"
            }
        },
        {"$count": "total"}
    ]
    
    sales_result = list(purchases_collection.aggregate(pipeline))
    total_sales = sales_result[0]["total"] if sales_result else 0
    
    # Calculate average rating from reviews on seller's notes
    rating_pipeline = [
        {
            "$lookup": {
                "from": "notes",
                "localField": "note_id",
                "foreignField": "_id",
                "as": "note"
            }
        },
        {"$unwind": "$note"},
        {
            "$match": {
                "note.uploader_id": seller_id
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_rating": {"$avg": "$rating"}
            }
        }
    ]
    
    rating_result = list(reviews_collection.aggregate(rating_pipeline))
    avg_rating = round(rating_result[0]["avg_rating"], 2) if rating_result else 0
    
    # Calculate dispute rate
    dispute_pipeline = [
        {
            "$lookup": {
                "from": "notes",
                "localField": "note_id",
                "foreignField": "_id",
                "as": "note"
            }
        },
        {"$unwind": "$note"},
        {
            "$match": {
                "note.uploader_id": seller_id,
                "status": {"$in": ["open", "resolved_buyer"]}  # Disputes against seller
            }
        },
        {"$count": "total"}
    ]
    
    dispute_result = list(disputes_collection.aggregate(dispute_pipeline))
    total_disputes = dispute_result[0]["total"] if dispute_result else 0
    dispute_rate = (total_disputes / total_sales * 100) if total_sales > 0 else 0
    
    # Determine trust level
    trust_level = "new"
    
    if total_sales >= 20 and avg_rating >= 4.5 and dispute_rate < 5:
        trust_level = "top"
    elif total_sales >= 5 and avg_rating >= 4.0 and account_age_days >= 30:
        trust_level = "trusted"
    
    return {
        "trust_level": trust_level,
        "total_sales": total_sales,
        "avg_rating": avg_rating,
        "account_age_days": account_age_days,
        "dispute_rate": round(dispute_rate, 2)
    }


def get_trust_badge_info(trust_level: str) -> dict:
    """
    Get display information for trust badge.
    
    Returns:
        {
            "emoji": str,
            "label": str,
            "color": str
        }
    """
    badges = {
        "new": {
            "emoji": "🆕",
            "label": "New Seller",
            "color": "gray"
        },
        "trusted": {
            "emoji": "✅",
            "label": "Trusted Seller",
            "color": "blue"
        },
        "top": {
            "emoji": "⭐",
            "label": "Top Seller",
            "color": "yellow"
        }
    }
    
    return badges.get(trust_level, badges["new"])
