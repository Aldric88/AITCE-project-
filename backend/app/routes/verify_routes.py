import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import users_collection
from app.utils.otp_utils import generate_otp
from app.utils.email_service import send_email

router = APIRouter(prefix="/verify", tags=["Email Verification"])


class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


@router.post("/send-otp")
def send_otp(data: SendOtpRequest):
    user = users_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_email_verified"):
        return {"message": "Email already verified ✅"}

    otp = generate_otp()
    expiry = int(time.time()) + 5 * 60  # 5 min

    users_collection.update_one(
        {"email": data.email},
        {"$set": {
            "email_otp": otp,
            "email_otp_expiry": expiry
        }}
    )

    # Send email
    email_sent = send_email(
        to_email=data.email,
        subject="Your Notes Market OTP Verification",
        body=f"Your OTP is: {otp}\n\nValid for 5 minutes."
    )

    if email_sent:
        return {"message": "OTP sent ✅"}
    else:
        # For development, return OTP in response if email not configured
        return {"message": "OTP generated ✅", "otp": otp, "note": "Email not configured - OTP returned for testing"}


@router.post("/confirm-otp")
def confirm_otp(data: VerifyOtpRequest):
    user = users_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_email_verified"):
        return {"message": "Email already verified ✅"}

    if not user.get("email_otp") or not user.get("email_otp_expiry"):
        raise HTTPException(status_code=400, detail="OTP not requested")

    if int(time.time()) > user["email_otp_expiry"]:
        raise HTTPException(status_code=400, detail="OTP expired ❌")

    if user["email_otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP ❌")

    users_collection.update_one(
        {"email": data.email},
        {"$set": {"is_email_verified": True},
         "$unset": {"email_otp": "", "email_otp_expiry": ""}}
    )

    return {"message": "Email verified successfully ✅"}
