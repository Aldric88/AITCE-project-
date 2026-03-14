import time
from bson import ObjectId


def append_trust_lookups(pipeline: list, include_college: bool = False):
    pipeline.append(
        {
            "$lookup": {
                "from": "users",
                "localField": "uploader_id",
                "foreignField": "_id",
                "as": "uploader",
            }
        }
    )
    if include_college:
        pipeline.append(
            {
                "$lookup": {
                    "from": "colleges",
                    "localField": "uploader.cluster_id",
                    "foreignField": "_id",
                    "as": "college",
                }
            }
        )
    pipeline.append(
        {
            "$lookup": {
                "from": "reviews",
                "localField": "_id",
                "foreignField": "note_id",
                "as": "reviews",
            }
        }
    )
    pipeline.append(
        {
            "$lookup": {
                "from": "purchases",
                "let": {"uploader_id": "$uploader_id"},
                "pipeline": [
                    {
                        "$lookup": {
                            "from": "notes",
                            "localField": "note_id",
                            "foreignField": "_id",
                            "as": "note",
                        }
                    },
                    {"$unwind": "$note"},
                    {
                        "$match": {
                            "$expr": {"$eq": ["$note.uploader_id", "$$uploader_id"]},
                            "status": "success",
                        }
                    },
                ],
                "as": "seller_purchases",
            }
        }
    )


def _seller_trust_level_expr() -> dict:
    avg_rating_expr = {
        "$cond": {
            "if": {"$gt": [{"$size": "$reviews"}, 0]},
            "then": {"$avg": "$reviews.rating"},
            "else": 0,
        }
    }
    return {
        "$cond": {
            "if": {
                "$and": [
                    {"$gte": [{"$size": "$seller_purchases"}, 20]},
                    {"$gte": [avg_rating_expr, 4.5]},
                ]
            },
            "then": "top",
            "else": {
                "$cond": {
                    "if": {
                        "$and": [
                            {"$gte": [{"$size": "$seller_purchases"}, 5]},
                            {"$gte": [avg_rating_expr, 4.0]},
                        ]
                    },
                    "then": "trusted",
                    "else": "new",
                }
            },
        }
    }


def append_trust_fields(pipeline: list, include_college: bool = False):
    fields = {
        "uploader_name": {"$arrayElemAt": ["$uploader.name", 0]},
        "verified_seller": {"$arrayElemAt": ["$uploader.verified_seller", 0]},
        "avg_rating": {
            "$cond": {
                "if": {"$gt": [{"$size": "$reviews"}, 0]},
                "then": {"$avg": "$reviews.rating"},
                "else": 0,
            }
        },
        "review_count": {"$size": "$reviews"},
        "seller_total_sales": {"$size": "$seller_purchases"},
        "seller_trust_level": _seller_trust_level_expr(),
    }
    if include_college:
        fields["college_name"] = {"$arrayElemAt": ["$college.name", 0]}
    pipeline.append({"$addFields": fields})


def append_access_fields(pipeline: list, current_user_id: ObjectId | None):
    if current_user_id is None:
        pipeline.append({"$addFields": {"has_access": {"$eq": ["$is_paid", False]}}})
        return

    now_ts = int(time.time())
    pipeline.append(
        {
            "$lookup": {
                "from": "purchases",
                "let": {"note_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$note_id", "$$note_id"]},
                                    {
                                        "$or": [
                                            {
                                                "$and": [
                                                    {"$eq": ["$buyer_id", current_user_id]},
                                                    {"$eq": ["$status", "success"]},
                                                ]
                                            },
                                            {
                                                "$and": [
                                                    {"$eq": ["$user_id", current_user_id]},
                                                    {"$in": ["$status", ["success", "paid", "free"]]},
                                                ]
                                            },
                                        ]
                                    },
                                ]
                            }
                        }
                    }
                ],
                "as": "user_purchase",
            }
        }
    )
    pipeline.append(
        {
            "$lookup": {
                "from": "pass_subscriptions",
                "let": {"seller_id": "$uploader_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$buyer_id", current_user_id]},
                                    {"$eq": ["$seller_id", "$$seller_id"]},
                                    {"$eq": ["$status", "active"]},
                                    {"$gte": ["$expires_at", now_ts]},
                                ]
                            }
                        }
                    }
                ],
                "as": "user_passes",
            }
        }
    )
    pipeline.append(
        {
            "$addFields": {
                "has_access": {
                    "$or": [
                        {"$eq": ["$uploader_id", current_user_id]},
                        {"$eq": ["$is_paid", False]},
                        {"$gt": [{"$size": "$user_purchase"}, 0]},
                        {"$gt": [{"$size": "$user_passes"}, 0]},
                    ]
                }
            }
        }
    )
