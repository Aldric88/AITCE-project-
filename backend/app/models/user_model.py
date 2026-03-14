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
        "is_email_verified": user.get("is_email_verified", False),
        "profile_pic_url": user.get("profile_pic_url"),
        "cluster_id": str(user.get("cluster_id")) if user.get("cluster_id") else None,
        "verified_by_domain": user.get("verified_by_domain", False),
        "wallet_points": int(user.get("wallet_points", 0)),
    }
