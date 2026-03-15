import time
from jose import jwt, JWTError
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.schemas.user_schema import UserCreate, UserResponse, TokenResponse
from app.services.user_service import get_user_by_email, create_user, authenticate_user
from app.services.cluster_resolver import resolve_user_cluster_metadata
from app.utils.domain_validator import validate_college_domain
from app.utils.security import create_access_token, create_refresh_token
from app.utils.dependencies import get_current_user, require_role
from app.database import users_collection, follows_collection, refresh_tokens_collection, revoked_tokens_collection
from app.utils.rate_limiter import login_limiter, signup_limiter
from app.config import settings
from bson import ObjectId

router = APIRouter(prefix="/auth", tags=["Auth"])


class DomainCheckRequest(BaseModel):
    email: str


@router.post("/check-domain")
def check_domain(data: DomainCheckRequest):
    """Pre-signup domain check — called from the signup form to give instant feedback."""
    result = validate_college_domain(data.email)
    return {
        "allowed": result["allowed"],
        "reason": result["reason"],
        "institution_name": result.get("institution_name", ""),
        "source": result.get("source", ""),
    }


@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, _=Depends(signup_limiter)):
    existing = get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ── College domain gate ──────────────────────────────────────────────────
    domain_check = validate_college_domain(user.email)
    if not domain_check["allowed"]:
        raise HTTPException(status_code=400, detail=domain_check["reason"])

    user_data = user.model_dump()
    # Carry institution name from AI check into user record
    if domain_check.get("institution_name"):
        user_data["institution_name"] = domain_check["institution_name"]
    user_data["domain_check_source"] = domain_check.get("source", "unknown")
    try:
        cluster_meta = resolve_user_cluster_metadata(user.email)
    except Exception:
        cluster_meta = {
            "cluster_id": None, "college_id": None, "university_type": None,
            "verified_by_domain": False, "requires_manual_selection": True,
            "cluster_source": "error_fallback", "inference_confidence": 0.0,
        }
    user_data["cluster_id"] = cluster_meta["cluster_id"]
    user_data["verified_by_domain"] = cluster_meta["verified_by_domain"]
    user_data["requires_manual_selection"] = cluster_meta["requires_manual_selection"]
    if cluster_meta.get("cluster_source"):
        user_data["cluster_source"] = cluster_meta["cluster_source"]
    if cluster_meta.get("inference_confidence") is not None:
        user_data["cluster_inference_confidence"] = cluster_meta["inference_confidence"]
    if cluster_meta["college_id"]:
        user_data["college_id"] = cluster_meta["college_id"]
    if cluster_meta["university_type"]:
        user_data["university_type"] = cluster_meta["university_type"]

    new_user = create_user(user_data)
    
    # `create_user` already returns user_helper format
    if new_user.get("cluster_id"):
        new_user["cluster_id"] = str(new_user["cluster_id"])

    return new_user


# Swagger-compatible: OAuth2 form (username=email, password)
@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    _=Depends(login_limiter),
):
    # Swagger sends username; we use it as email
    user = authenticate_user(form_data.username, form_data.password)

    if user == "BANNED":
        raise HTTPException(
            status_code=403, detail="Your account has been disabled"
        )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"], "role": user["role"]})
    refresh_token = create_refresh_token({"sub": user["email"], "role": user["role"]})
    refresh_payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    refresh_tokens_collection.insert_one(
        {
            "user_id": ObjectId(user["id"]),
            "jti": refresh_payload.get("jti"),
            "revoked": False,
            "created_at": int(time.time()),
            "expires_at": int(refresh_payload.get("exp", 0)),
        }
    )

    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(request: Request, response: Response):
    access_token = request.cookies.get(settings.JWT_COOKIE_NAME)
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    for token in (access_token, refresh_token):
        if not token:
            continue
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoked_tokens_collection.update_one(
                    {"jti": jti},
                    {
                        "$setOnInsert": {
                            "created_at": int(time.time()),
                            "expires_at": int(payload.get("exp", 0)),
                        }
                    },
                    upsert=True,
                )
                refresh_tokens_collection.update_one({"jti": jti}, {"$set": {"revoked": True}})
        except JWTError:
            continue

    response.delete_cookie(
        key=settings.JWT_COOKIE_NAME,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    return {"message": "Logged out"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("typ") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token type")
    if revoked_tokens_collection.find_one({"jti": payload.get("jti")}):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    token_doc = refresh_tokens_collection.find_one({"jti": payload.get("jti"), "revoked": False})
    if not token_doc:
        raise HTTPException(status_code=401, detail="Refresh token not active")

    email = payload.get("sub")
    role = payload.get("role", "student")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token subject")

    # Rotate refresh token
    refresh_tokens_collection.update_one({"jti": payload.get("jti")}, {"$set": {"revoked": True}})
    revoked_tokens_collection.update_one(
        {"jti": payload.get("jti")},
        {
            "$setOnInsert": {
                "created_at": int(time.time()),
                "expires_at": int(payload.get("exp", 0)),
            }
        },
        upsert=True,
    )

    new_access = create_access_token({"sub": email, "role": role})
    new_refresh = create_refresh_token({"sub": email, "role": role})
    new_refresh_payload = jwt.decode(new_refresh, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    refresh_tokens_collection.insert_one(
        {
            "user_id": token_doc["user_id"],
            "jti": new_refresh_payload.get("jti"),
            "revoked": False,
            "created_at": int(time.time()),
            "expires_at": int(new_refresh_payload.get("exp", 0)),
        }
    )

    response.set_cookie(
        key=settings.JWT_COOKIE_NAME,
        value=new_access,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )
    return {"access_token": new_access, "token_type": "bearer"}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    # Get followers and following counts
    followers = follows_collection.count_documents({"following_id": ObjectId(current_user["id"])})
    following = follows_collection.count_documents({"follower_id": ObjectId(current_user["id"])})
    
    return {
        "id": str(current_user["id"]),
        "name": current_user["name"],
        "email": current_user["email"],
        "dept": current_user["dept"],
        "year": current_user["year"],
        "section": current_user["section"],
        "role": current_user.get("role", "student"),
        "is_email_verified": current_user.get("is_email_verified", False),
        "profile_pic_url": current_user.get("profile_pic_url", None),
        "wallet_points": int(current_user.get("wallet_points", 0)),
        "upload_violations": int(current_user.get("upload_violations", 0)),
        "can_upload": current_user.get("can_upload", True),
        "verified_seller": current_user.get("verified_seller", False),
        "followers_count": followers,
        "following_count": following
    }


# Example protected route for moderators/admins
@router.get("/moderator-area")
def moderator_area(current_user=Depends(require_role(["moderator", "admin"]))):
    return {"message": "Welcome Moderator/Admin", "user": current_user}
