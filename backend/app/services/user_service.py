from app.database import users_collection
from app.utils.security import hash_password, verify_password
from app.models.user_model import user_helper


def get_user_by_email(email: str):
    return users_collection.find_one({"email": email})


def create_user(user_data: dict):
    user_data["password"] = hash_password(user_data["password"])
    user_data["role"] = "student"  # default role
    user_data["is_active"] = True
    user_data["verified_seller"] = False  # default: not verified seller
    user_data["is_email_verified"] = False  # email verification
    user_data["email_otp"] = None
    user_data["email_otp_expiry"] = None
    result = users_collection.insert_one(user_data)
    new_user = users_collection.find_one({"_id": result.inserted_id})
    return user_helper(new_user)


def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None

    if user.get("is_active", True) is False:
        return "BANNED"

    if not verify_password(password, user["password"]):
        return None

    return user_helper(user)
