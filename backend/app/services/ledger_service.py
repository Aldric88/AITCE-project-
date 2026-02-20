import time
from bson import ObjectId

from app.database import ledger_entries_collection


def add_ledger_entry(
    *,
    purchase_id: ObjectId,
    buyer_id: ObjectId,
    seller_id: ObjectId,
    note_id: ObjectId,
    amount: int,
    currency: str,
    entry_type: str,
    source: str,
    metadata: dict | None = None,
):
    ledger_entries_collection.insert_one(
        {
            "purchase_id": purchase_id,
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "note_id": note_id,
            "amount": amount,
            "currency": currency,
            "entry_type": entry_type,
            "source": source,
            "metadata": metadata or {},
            "created_at": int(time.time()),
        }
    )
