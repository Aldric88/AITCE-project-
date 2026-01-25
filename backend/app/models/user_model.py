def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "dept": user["dept"],
        "year": user["year"],
        "section": user["section"],
        "role": user.get("role", "student"),
        "is_active": user.get("is_active", True),
        "verified_seller": user.get("verified_seller", False),
    }
