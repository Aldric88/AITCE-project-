"""Normalize purchases documents to canonical schema.

Canonical fields:
- buyer_id: ObjectId
- note_id: ObjectId
- status: one of success|pending|failed
- amount: int/float
- purchase_type: direct|free|razorpay|unknown

Usage:
  python migrate_purchases_schema.py           # dry run
  python migrate_purchases_schema.py --apply   # write changes
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any, Dict

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.database import purchases_collection


STATUS_MAP = {
    "paid": "success",
    "free": "success",
    "success": "success",
    "pending": "pending",
    "failed": "failed",
}


def normalize_status(status: Any) -> str:
    raw = str(status or "").strip().lower()
    return STATUS_MAP.get(raw, "success")


def infer_purchase_type(doc: Dict[str, Any], normalized_status: str) -> str:
    existing = str(doc.get("purchase_type") or "").strip().lower()
    if existing in {"direct", "free", "razorpay", "unknown"}:
        return existing

    amount = doc.get("amount", 0) or 0
    if amount == 0:
        return "free"
    if doc.get("razorpay_order_id") or doc.get("razorpay_payment_id"):
        return "razorpay"
    if normalized_status == "pending":
        return "unknown"
    return "direct"


def needs_update(doc: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    buyer_id = doc.get("buyer_id")
    user_id = doc.get("user_id")

    # Canonical identity field
    if buyer_id is None and isinstance(user_id, ObjectId):
        updates["buyer_id"] = user_id
    elif buyer_id is None and user_id is not None:
        try:
            updates["buyer_id"] = ObjectId(str(user_id))
        except Exception:
            pass

    # Normalize status
    normalized_status = normalize_status(doc.get("status"))
    if doc.get("status") != normalized_status:
        updates["status"] = normalized_status

    # Canonical purchase type
    purchase_type = infer_purchase_type(doc, normalized_status)
    if doc.get("purchase_type") != purchase_type:
        updates["purchase_type"] = purchase_type

    return updates


def run(apply: bool) -> int:
    try:
        total = purchases_collection.count_documents({})
    except PyMongoError as exc:
        print(f"ERROR: Could not connect/read purchases collection: {exc}")
        return 2

    print(f"Found {total} purchase documents")

    counters = Counter()
    for doc in purchases_collection.find({}):
        counters["scanned"] += 1
        updates = needs_update(doc)

        if not updates:
            counters["unchanged"] += 1
            continue

        counters["to_update"] += 1
        if "buyer_id" in updates:
            counters["fix_buyer_id"] += 1
        if "status" in updates:
            counters["fix_status"] += 1
        if "purchase_type" in updates:
            counters["fix_purchase_type"] += 1

        if apply:
            purchases_collection.update_one({"_id": doc["_id"]}, {"$set": updates})
            counters["updated"] += 1

    print("--- Summary ---")
    print(f"Scanned: {counters['scanned']}")
    print(f"Unchanged: {counters['unchanged']}")
    print(f"Needs update: {counters['to_update']}")
    print(f"buyer_id fixes: {counters['fix_buyer_id']}")
    print(f"status fixes: {counters['fix_status']}")
    print(f"purchase_type fixes: {counters['fix_purchase_type']}")

    if apply:
        print(f"Updated: {counters['updated']}")
    else:
        print("Dry run only. Re-run with --apply to persist changes.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize purchases schema")
    parser.add_argument("--apply", action="store_true", help="Apply changes to DB")
    args = parser.parse_args()
    return run(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
