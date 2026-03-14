import time
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.database import users_collection
from app.utils.otp_utils import generate_otp
from app.utils.email_service import send_email_html

router = APIRouter(prefix="/verify", tags=["Email Verification"])

OTP_EXPIRY_SECONDS = 10 * 60      # 10 minutes
OTP_MAX_ATTEMPTS   = 3            # wrong guesses before invalidation
OTP_RESEND_COOLDOWN = 60          # seconds before resend is allowed


class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


def _otp_email_html(otp: str, email: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Arial', sans-serif; background: #f5f5f5; margin: 0; padding: 0; }}
    .container {{ max-width: 480px; margin: 40px auto; background: #ffffff;
                  border: 2px solid #000; padding: 0; }}
    .header {{ background: #000; padding: 24px 32px; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 20px;
                  font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; }}
    .body {{ padding: 32px; }}
    .otp-box {{ background: #f5f5f5; border: 2px solid #000; padding: 24px;
                text-align: center; margin: 24px 0; }}
    .otp {{ font-size: 48px; font-weight: 900; letter-spacing: 0.3em;
             color: #000; font-family: 'Courier New', monospace; }}
    .meta {{ font-size: 12px; color: #666; text-transform: uppercase;
              letter-spacing: 0.1em; margin-top: 8px; }}
    .footer {{ border-top: 1px solid #e5e5e5; padding: 16px 32px;
               font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.08em; }}
    p {{ font-size: 14px; color: #333; line-height: 1.6; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Notes Market — Email Verification</h1>
    </div>
    <div class="body">
      <p>Hi there,</p>
      <p>Enter the OTP below to verify your college email address <strong>{email}</strong> and unlock full access to Notes Market.</p>
      <div class="otp-box">
        <div class="otp">{otp}</div>
        <div class="meta">Valid for 10 minutes &nbsp;·&nbsp; Do not share</div>
      </div>
      <p>If you didn't sign up for Notes Market, ignore this email.</p>
    </div>
    <div class="footer">
      Notes Market &nbsp;·&nbsp; College-only notes platform
    </div>
  </div>
</body>
</html>
"""


@router.post("/send-otp")
def send_otp(data: SendOtpRequest, background_tasks: BackgroundTasks):
    user = users_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_email_verified"):
        return {"message": "Email already verified ✅"}

    # Resend cooldown
    last_sent = user.get("otp_sent_at", 0)
    if int(time.time()) - last_sent < OTP_RESEND_COOLDOWN:
        remaining = OTP_RESEND_COOLDOWN - (int(time.time()) - last_sent)
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining} seconds before requesting a new OTP.",
        )

    otp = generate_otp()
    expiry = int(time.time()) + OTP_EXPIRY_SECONDS

    users_collection.update_one(
        {"email": data.email},
        {"$set": {
            "email_otp": otp,
            "email_otp_expiry": expiry,
            "email_otp_attempts": 0,
            "otp_sent_at": int(time.time()),
        }},
    )

    from app.utils.email_service import EMAIL_USER
    html_body = _otp_email_html(otp, data.email)

    if EMAIL_USER:
        background_tasks.add_task(
            send_email_html,
            to_email=data.email,
            subject="Your Notes Market Verification Code",
            html_body=html_body,
        )
        return {"message": "OTP sent to your college email ✅"}
    else:
        # Dev fallback — return OTP in response when SMTP not configured
        return {
            "message": "OTP generated ✅ (Email not configured — dev mode)",
            "otp": otp,
            "note": "Configure EMAIL_USER and EMAIL_PASS in .env to send real emails",
        }


@router.post("/confirm-otp")
def confirm_otp(data: VerifyOtpRequest):
    user = users_collection.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("is_email_verified"):
        return {"message": "Email already verified ✅"}

    if not user.get("email_otp") or not user.get("email_otp_expiry"):
        raise HTTPException(status_code=400, detail="No OTP requested. Please request a new OTP.")

    # Attempt limit
    attempts = int(user.get("email_otp_attempts", 0))
    if attempts >= OTP_MAX_ATTEMPTS:
        # Invalidate the OTP
        users_collection.update_one(
            {"email": data.email},
            {"$unset": {"email_otp": "", "email_otp_expiry": "", "email_otp_attempts": ""}},
        )
        raise HTTPException(
            status_code=400,
            detail="Too many wrong attempts. Please request a new OTP.",
        )

    # Expiry check
    if int(time.time()) > user["email_otp_expiry"]:
        users_collection.update_one(
            {"email": data.email},
            {"$unset": {"email_otp": "", "email_otp_expiry": "", "email_otp_attempts": ""}},
        )
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    # Wrong OTP — increment attempt counter
    if user["email_otp"] != data.otp.strip():
        users_collection.update_one(
            {"email": data.email},
            {"$inc": {"email_otp_attempts": 1}},
        )
        remaining = OTP_MAX_ATTEMPTS - (attempts + 1)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
        )

    # ✅ Correct
    users_collection.update_one(
        {"email": data.email},
        {
            "$set": {"is_email_verified": True},
            "$unset": {"email_otp": "", "email_otp_expiry": "", "email_otp_attempts": "", "otp_sent_at": ""},
        },
    )

    return {"message": "Email verified successfully ✅ Welcome to Notes Market!"}


@router.get("/status")
def verification_status(email: str):
    """Quick status check — used by frontend to poll after sending OTP."""
    user = users_collection.find_one({"email": email}, {"is_email_verified": 1, "otp_sent_at": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "is_email_verified": bool(user.get("is_email_verified")),
        "otp_sent_at": user.get("otp_sent_at", 0),
        "resend_cooldown_seconds": OTP_RESEND_COOLDOWN,
    }
