def note_helper(note) -> dict:
    return {
        "id": str(note["_id"]),
        "title": note["title"],
        "description": note.get("description"),
        "dept": note["dept"],
        "semester": note["semester"],
        "subject": note["subject"],
        "unit": note.get("unit"),
        "tags": note.get("tags", []),
        "note_type": note["note_type"],
        "file_url": note.get("file_url"),
        "external_link": note.get("external_link"),
        "status": note.get("status", "pending"),
        "uploader_id": str(note["uploader_id"]),
        "is_paid": note.get("is_paid", False),
        "price": note.get("price", 0),
    }
