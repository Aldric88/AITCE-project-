import os
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from typing import Optional
from pydantic import BaseModel

from app.database import (
    notes_collection,
    uploads_collection,
    leaderboard_collection,
    reviews_collection,
    purchases_collection,
    likes_collection,
    colleges_collection,
    users_collection,
)
from app.schemas.note_schema import NoteCreate, NoteUpdate
from app.models.note_model import note_helper
from app.utils.dependencies import get_current_user, get_optional_current_user
from app.utils.rate_limiter import search_limiter
from app.services.ai_pipeline import enqueue_note_ai_analysis
from app.utils.cache import cache_get_json, cache_set_json
from app.utils.observability import log_if_slow
from app.services.risk_service import compute_user_risk_score
from app.database import reports_collection, disputes_collection, requests_collection

router = APIRouter(prefix="/notes", tags=["Notes"])
logger = logging.getLogger(__name__)


def _add_points(user_id, points: int, reason: str):
    leaderboard_collection.insert_one(
        {
            "user_id": user_id,
            "points": points,
            "reason": reason,
            "created_at": int(time.time()),
        }
    )


# Student uploads note (always pending)
@router.post("/")
def create_note(note: NoteCreate, current_user=Depends(get_current_user)):
    new_note = note.model_dump()
    uploader_id = ObjectId(current_user["id"])

    risk = compute_user_risk_score(
        current_user["id"],
        {
            "users_collection": users_collection,
            "notes_collection": notes_collection,
            "reports_collection": reports_collection,
            "disputes_collection": disputes_collection,
            "requests_collection": requests_collection,
            "purchases_collection": purchases_collection,
        },
    )
    if risk["risk_score"] >= 90:
        raise HTTPException(status_code=403, detail="Account risk too high. Contact support.")

    if not current_user.get("is_email_verified", False):
        raise HTTPException(status_code=403, detail="Verify your email to upload notes")

    # ✅ Pricing validation
    if new_note.get("is_paid"):
        if new_note.get("price") is None:
            raise HTTPException(status_code=400, detail="Price required for paid notes")

        if new_note.get("price") < 1:
            raise HTTPException(status_code=400, detail="Price must be at least ₹1")

        if new_note.get("price") > 150:
            raise HTTPException(status_code=400, detail="Max price allowed is ₹150")
    else:
        new_note["price"] = 0

    # ✅ only verified sellers can post paid notes
    if new_note.get("is_paid") is True:
        if current_user.get("verified_seller") is not True:
            raise HTTPException(
                status_code=403,
                detail="Only verified sellers can upload paid notes"
            )

    # uploader info
    new_note["uploader_id"] = uploader_id
    new_note["status"] = "pending"
    new_note["ai"] = None  # AI analysis field
    
    # ✅ Cluster assignment (Trust Architecture)
    if current_user.get("cluster_id"):
        new_note["cluster_id"] = ObjectId(current_user["cluster_id"])
    else:
        # If user has no cluster (manual user?), explicitly set None or handle logic
        # For now, allow but maybe flag?
        new_note["cluster_id"] = None

    # validate note type requirements
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        if not note.file_url:
            raise HTTPException(
                status_code=400,
                detail="file_url is required for this note_type",
            )

        # SECURITY: file_url must exist in uploads collection
        upload_doc = uploads_collection.find_one({"file_url": note.file_url})
        if not upload_doc:
            raise HTTPException(
                status_code=400,
                detail="Invalid file_url (file not found). Upload the file first.",
            )

        # SECURITY: file must belong to same user
        if upload_doc["uploader_id"] != uploader_id:
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to use this file_url (not your upload).",
            )

        # SECURITY: prevent reusing same uploaded file in multiple notes
        if upload_doc.get("is_linked") is True:
            raise HTTPException(
                status_code=400,
                detail="This file is already linked to another note.",
            )

    elif note.note_type == "link":
        if not note.external_link:
            raise HTTPException(
                status_code=400,
                detail="external_link is required for link note_type",
            )

    elif note.note_type == "text":
        pass

    else:
        raise HTTPException(status_code=400, detail="Invalid note_type")

    # insert note
    result = notes_collection.insert_one(new_note)
    saved_note = notes_collection.find_one({"_id": result.inserted_id})

    # mark upload as linked to this note (only for file-based notes)
    if note.note_type in ["pdf", "doc", "ppt", "image"]:
        uploads_collection.update_one(
            {"file_url": note.file_url},
            {"$set": {"is_linked": True, "linked_note_id": saved_note["_id"]}},
        )

    file_url = new_note.get("file_url")
    if file_url:
        enqueue_note_ai_analysis(
            note_id=str(result.inserted_id),
            file_url=file_url,
            meta={
                "title": new_note.get("title"),
                "subject": new_note.get("subject"),
                "dept": new_note.get("dept"),
                "unit": new_note.get("unit"),
            },
        )

    return note_helper(saved_note)


# Approved notes feed (public but cluster-aware)
@router.get("/")
def get_approved_notes(
    dept: Optional[str] = Query(default=None),
    semester: Optional[int] = Query(default=None),
    subject: Optional[str] = Query(default=None),
    exam_tag: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    cluster_id: Optional[str] = Query(default=None), 
    sort: Optional[str] = Query(default="newest", pattern="^(newest|oldest|downloads|rating|price_high|price_low|free_first)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user = Depends(get_optional_current_user),
    _ = Depends(search_limiter)
):
    query = {"status": "approved"}

    if current_user and current_user.get("cluster_id"):
        query["cluster_id"] = ObjectId(current_user["cluster_id"])
    elif cluster_id and ObjectId.is_valid(cluster_id):
        query["cluster_id"] = ObjectId(cluster_id)
    
    if dept:
        query["dept"] = dept
    if semester:
        query["semester"] = semester
    if subject:
        query["subject"] = {"$regex": subject, "$options": "i"} 
    if exam_tag:
        query["exam_tag"] = exam_tag
    text_score_needed = False
    if search:
        search_term = search.strip()
        if search_term:
            query["$text"] = {"$search": search_term}
            text_score_needed = True
    
    # Build aggregation pipeline for trust data
    pipeline = [
        {"$match": query},
    ]
    
    # Join with users collection for uploader trust data
    pipeline.append({
        "$lookup": {
            "from": "users",
            "localField": "uploader_id",
            "foreignField": "_id",
            "as": "uploader"
        }
    })
    
    # Join with colleges collection for college name
    pipeline.append({
        "$lookup": {
            "from": "colleges",
            "localField": "uploader.cluster_id",
            "foreignField": "_id",
            "as": "college"
        }
    })
    
    # Join with reviews for rating
    pipeline.append({
        "$lookup": {
            "from": "reviews",
            "localField": "_id",
            "foreignField": "note_id",
            "as": "reviews"
        }
    })
    
    # Join with purchases to count seller sales
    pipeline.append({
        "$lookup": {
            "from": "purchases",
            "let": {"uploader_id": "$uploader_id"},
            "pipeline": [
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
                        "$expr": {"$eq": ["$note.uploader_id", "$$uploader_id"]},
                        "status": "success"
                    }
                }
            ],
            "as": "seller_purchases"
        }
    })
    
    # Add computed fields
    pipeline.append({
        "$addFields": {
            "uploader_name": {"$arrayElemAt": ["$uploader.name", 0]},
            "verified_seller": {"$arrayElemAt": ["$uploader.verified_seller", 0]},
            "college_name": {"$arrayElemAt": ["$college.name", 0]},
            "avg_rating": {
                "$cond": {
                    "if": {"$gt": [{"$size": "$reviews"}, 0]},
                    "then": {"$avg": "$reviews.rating"},
                    "else": 0
                }
            },
            "review_count": {"$size": "$reviews"},
            "seller_total_sales": {"$size": "$seller_purchases"},
            # Calculate seller trust level inline
            "seller_trust_level": {
                "$cond": {
                    "if": {
                        "$and": [
                            {"$gte": [{"$size": "$seller_purchases"}, 20]},
                            {"$gte": [
                                {
                                    "$cond": {
                                        "if": {"$gt": [{"$size": "$reviews"}, 0]},
                                        "then": {"$avg": "$reviews.rating"},
                                        "else": 0
                                    }
                                },
                                4.5
                            ]}
                        ]
                    },
                    "then": "top",
                    "else": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$gte": [{"$size": "$seller_purchases"}, 5]},
                                    {"$gte": [
                                        {
                                            "$cond": {
                                                "if": {"$gt": [{"$size": "$reviews"}, 0]},
                                                "then": {"$avg": "$reviews.rating"},
                                                "else": 0
                                            }
                                        },
                                        4.0
                                    ]}
                                ]
                            },
                            "then": "trusted",
                            "else": "new"
                        }
                    }
                }
            }
        }
    })
    
    if text_score_needed:
        pipeline.append({"$addFields": {"_text_score": {"$meta": "textScore"}}})

    # Sort
    if sort == "newest":
        pipeline.append({"$sort": {"_id": -1}})
    elif sort == "oldest":
        pipeline.append({"$sort": {"_id": 1}})
    elif sort == "downloads":
        pipeline.append({"$sort": {"downloads": -1}})
    elif sort == "views":
        pipeline.append({"$sort": {"views": -1}})
    elif sort == "rating":
        pipeline.append({"$sort": {"avg_rating": -1}})
    elif sort == "price_high":
        pipeline.append({"$sort": {"price": -1}})
    elif sort == "price_low":
        pipeline.append({"$sort": {"price": 1}})
    elif sort == "free_first":
        pipeline.append({"$sort": {"price": 1}})
    if text_score_needed:
        pipeline.append({"$sort": {"_text_score": -1, "_id": -1}})
    
    # Access check (if user logged in)
    if current_user:
        user_id = ObjectId(current_user["id"])
        pipeline.append({
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
                                                    {"$eq": ["$buyer_id", user_id]},
                                                    {"$eq": ["$status", "success"]},
                                                ]
                                            },
                                            {
                                                "$and": [
                                                    {"$eq": ["$user_id", user_id]},
                                                    {"$in": ["$status", ["success", "paid", "free"]]},
                                                ]
                                            },
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ],
                "as": "user_purchase"
            }
        })
        pipeline.append({
            "$addFields": {
                "has_access": {
                    "$or": [
                        {"$eq": ["$uploader_id", user_id]},
                        {"$eq": ["$is_paid", False]},
                        {"$gt": [{"$size": "$user_purchase"}, 0]}
                    ]
                }
            }
        })
    else:
        pipeline.append({
            "$addFields": {
                "has_access": {"$eq": ["$is_paid", False]}
            }
        })
    
    # Pagination
    pipeline.append({"$skip": skip})
    pipeline.append({"$limit": limit})
    
    started = time.time()
    notes = list(notes_collection.aggregate(pipeline))
    log_if_slow(
        logger,
        "notes.feed.aggregate",
        started,
        result_count=len(notes),
        skip=skip,
        limit=limit,
        sort=sort,
    )
    return [note_helper(n) for n in notes]


# My uploaded notes
@router.get("/my")
def my_notes(current_user=Depends(get_current_user)):
    notes = notes_collection.find(
        {"uploader_id": ObjectId(current_user["id"])}
    ).sort("_id", -1)
    return [note_helper(n) for n in notes]


@router.get("/my-uploads")
def my_notes_alias(current_user=Depends(get_current_user)):
    return my_notes(current_user=current_user)


# Edit note metadata (owner only)
@router.patch("/{note_id}")
def update_note(
    note_id: str,
    data: NoteUpdate,
    current_user=Depends(get_current_user),
):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only owner can edit
    if str(note["uploader_id"]) != current_user["id"]:
        raise HTTPException(
            status_code=403, detail="You can only edit your own note"
        )
        
    # ABAC: Prevent "Bait & Switch". Approved notes cannot be edited by students.
    if note.get("status") == "approved" and current_user.get("role") != "admin":
         raise HTTPException(
            status_code=403, detail="Approved notes cannot be edited. Contact admin."
        )

    updates = {k: v for k, v in data.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(
            status_code=400, detail="No fields provided to update"
        )

    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$set": updates},
    )

    updated = notes_collection.find_one({"_id": ObjectId(note_id)})
    return note_helper(updated)


# Delete note + unlink upload, remove file from disk (owner or admin)
@router.delete("/{note_id}")
def delete_note(note_id: str, current_user=Depends(get_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    note = notes_collection.find_one({"_id": ObjectId(note_id)})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Only owner OR admin can delete
    if str(note["uploader_id"]) != current_user["id"] and current_user[
        "role"
    ] != "admin":
        raise HTTPException(
            status_code=403, detail="Not allowed to delete this note"
        )

    # unlink upload and remove file if it is file-based
    file_url = note.get("file_url")
    if file_url:
        upload_doc = uploads_collection.find_one({"file_url": file_url})

        if upload_doc:
            # unlink in DB
            uploads_collection.update_one(
                {"file_url": file_url},
                {"$set": {"is_linked": False, "linked_note_id": None}},
            )

            # delete actual file from disk
            stored_name = upload_doc.get("stored_name")
            if stored_name:
                local_path = os.path.join("uploads", stored_name)
                if os.path.exists(local_path):
                    os.remove(local_path)

            # delete upload record
            uploads_collection.delete_one({"file_url": file_url})

    # delete the note
    notes_collection.delete_one({"_id": ObjectId(note_id)})

    return {"message": "Note deleted successfully ✅", "note_id": note_id}


@router.get("/{note_id}/details")
def note_details(note_id: str, current_user=Depends(get_optional_current_user)):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=400, detail="Invalid note_id")

    pipeline = [{"$match": {"_id": ObjectId(note_id), "status": "approved"}}]

    # Joins
    pipeline.append({
        "$lookup": {
            "from": "users",
            "localField": "uploader_id",
            "foreignField": "_id",
            "as": "uploader"
        }
    })
    
    pipeline.append({
        "$lookup": {
            "from": "colleges",
            "localField": "uploader.cluster_id",
            "foreignField": "_id",
            "as": "college"
        }
    })

    pipeline.append({
        "$lookup": {
            "from": "reviews",
            "localField": "_id",
            "foreignField": "note_id",
            "as": "reviews"
        }
    })
    
    pipeline.append({
        "$lookup": {
            "from": "purchases",
            "let": {"uploader_id": "$uploader_id"},
            "pipeline": [
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
                        "$expr": {"$eq": ["$note.uploader_id", "$$uploader_id"]},
                        "status": "success"
                    }
                }
            ],
            "as": "seller_purchases"
        }
    })

    # Computed fields
    pipeline.append({
        "$addFields": {
            "uploader_name": {"$arrayElemAt": ["$uploader.name", 0]},
            "verified_seller": {"$arrayElemAt": ["$uploader.verified_seller", 0]},
            "college_name": {"$arrayElemAt": ["$college.name", 0]},
            "avg_rating": {
                "$cond": {
                    "if": {"$gt": [{"$size": "$reviews"}, 0]},
                    "then": {"$avg": "$reviews.rating"},
                    "else": 0
                }
            },
            "review_count": {"$size": "$reviews"},
            "seller_total_sales": {"$size": "$seller_purchases"},
            "seller_trust_level": {
                "$cond": {
                    "if": {
                        "$and": [
                            {"$gte": [{"$size": "$seller_purchases"}, 20]},
                            {"$gte": [{"$cond": {"if": {"$gt": [{"$size": "$reviews"}, 0]}, "then": {"$avg": "$reviews.rating"}, "else": 0}}, 4.5]}
                        ]
                    },
                    "then": "top",
                    "else": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$gte": [{"$size": "$seller_purchases"}, 5]},
                                    {"$gte": [{"$cond": {"if": {"$gt": [{"$size": "$reviews"}, 0]}, "then": {"$avg": "$reviews.rating"}, "else": 0}}, 4.0]}
                                ]
                            },
                            "then": "trusted",
                            "else": "new"
                        }
                    }
                }
            }
        }
    })

    # Access check
    if current_user:
        user_id = ObjectId(current_user["id"])
        pipeline.append({
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
                                                    {"$eq": ["$buyer_id", user_id]},
                                                    {"$eq": ["$status", "success"]},
                                                ]
                                            },
                                            {
                                                "$and": [
                                                    {"$eq": ["$user_id", user_id]},
                                                    {"$in": ["$status", ["success", "paid", "free"]]},
                                                ]
                                            },
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ],
                "as": "user_purchase"
            }
        })
        pipeline.append({
            "$addFields": {
                "has_access": {
                    "$or": [
                        {"$eq": ["$uploader_id", user_id]},
                        {"$eq": ["$is_paid", False]},
                        {"$gt": [{"$size": "$user_purchase"}, 0]}
                    ]
                }
            }
        })
    else:
        pipeline.append({"$addFields": {"has_access": {"$eq": ["$is_paid", False]}}})

    # Increment views
    notes_collection.update_one(
        {"_id": ObjectId(note_id)},
        {"$inc": {"views": 1}}
    )

    notes = list(notes_collection.aggregate(pipeline))
    if not notes:
        raise HTTPException(status_code=404, detail="Note not found")

    return note_helper(notes[0])


@router.get("/trending")
def trending_notes(current_user=Depends(get_optional_current_user)):
    cache_user_scope = current_user.get("cluster_id") if current_user else "public"
    cache_key = f"notes:trending:{cache_user_scope}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    # Security: Filter by cluster
    query = {"status": "approved"}
    
    if current_user and current_user.get("cluster_id"):
        query["cluster_id"] = ObjectId(current_user["cluster_id"])
        
    pipeline = [{"$match": query}]
    
    # Standard trust joins
    pipeline.append({
        "$lookup": {
            "from": "users",
            "localField": "uploader_id",
            "foreignField": "_id",
            "as": "uploader"
        }
    })
    
    pipeline.append({
        "$lookup": {
            "from": "colleges",
            "localField": "uploader.cluster_id",
            "foreignField": "_id",
            "as": "college"
        }
    })

    pipeline.append({
        "$lookup": {
            "from": "reviews",
            "localField": "_id",
            "foreignField": "note_id",
            "as": "reviews"
        }
    })
    
    pipeline.append({
        "$lookup": {
            "from": "purchases",
            "let": {"uploader_id": "$uploader_id"},
            "pipeline": [
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
                        "$expr": {"$eq": ["$note.uploader_id", "$$uploader_id"]},
                        "status": "success"
                    }
                }
            ],
            "as": "seller_purchases"
        }
    })

    # Computed fields
    pipeline.append({
        "$addFields": {
            "uploader_name": {"$arrayElemAt": ["$uploader.name", 0]},
            "verified_seller": {"$arrayElemAt": ["$uploader.verified_seller", 0]},
            "college_name": {"$arrayElemAt": ["$college.name", 0]},
            "avg_rating": {
                "$cond": {
                    "if": {"$gt": [{"$size": "$reviews"}, 0]},
                    "then": {"$avg": "$reviews.rating"},
                    "else": 0
                }
            },
            "review_count": {"$size": "$reviews"},
            "seller_total_sales": {"$size": "$seller_purchases"},
            "seller_trust_level": {
                "$cond": {
                    "if": {
                        "$and": [
                            {"$gte": [{"$size": "$seller_purchases"}, 20]},
                            {"$gte": [{"$cond": {"if": {"$gt": [{"$size": "$reviews"}, 0]}, "then": {"$avg": "$reviews.rating"}, "else": 0}}, 4.5]}
                        ]
                    },
                    "then": "top",
                    "else": {
                        "$cond": {
                            "if": {
                                "$and": [
                                    {"$gte": [{"$size": "$seller_purchases"}, 5]},
                                    {"$gte": [{"$cond": {"if": {"$gt": [{"$size": "$reviews"}, 0]}, "then": {"$avg": "$reviews.rating"}, "else": 0}}, 4.0]}
                                ]
                            },
                            "then": "trusted",
                            "else": "new"
                        }
                    }
                }
            }
        }
    })

    # Access check (if user logged in)
    if current_user:
        user_id = ObjectId(current_user["id"])
        pipeline.append({
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
                                                    {"$eq": ["$buyer_id", user_id]},
                                                    {"$eq": ["$status", "success"]},
                                                ]
                                            },
                                            {
                                                "$and": [
                                                    {"$eq": ["$user_id", user_id]},
                                                    {"$in": ["$status", ["success", "paid", "free"]]},
                                                ]
                                            },
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ],
                "as": "user_purchase"
            }
        })
        pipeline.append({
            "$addFields": {
                "has_access": {
                    "$or": [
                        {"$eq": ["$uploader_id", user_id]},
                        {"$eq": ["$is_paid", False]},
                        {"$gt": [{"$size": "$user_purchase"}, 0]}
                    ]
                }
            }
        })
    else:
        pipeline.append({"$addFields": {"has_access": {"$eq": ["$is_paid", False]}}})

    pipeline.append({"$sort": {"views": -1}})
    pipeline.append({"$limit": 20})

    notes = list(notes_collection.aggregate(pipeline))
    result = [note_helper(n) for n in notes]
    cache_set_json(cache_key, result, ttl=120)
    return result
