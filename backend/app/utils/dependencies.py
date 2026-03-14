from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import Optional
from app.config import settings
from app.database import users_collection, revoked_tokens_collection
from app.models.user_model import user_helper

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _extract_token(request: Request, bearer_token: Optional[str]) -> Optional[str]:
    if bearer_token:
        return bearer_token
    return request.cookies.get(settings.JWT_COOKIE_NAME)


def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme_optional),
):
    token = _extract_token(request, bearer_token)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("typ") not in (None, "access"):
            raise HTTPException(status_code=401, detail="Invalid token type")
        email: str = payload.get("sub")
        jti: str = payload.get("jti")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if jti and revoked_tokens_collection.find_one({"jti": jti}):
            raise HTTPException(status_code=401, detail="Token revoked")

        user = users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user_helper(user)

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(allowed_roles: list):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized for this action",
            )
        return current_user

    return role_checker


def require_email_verified(current_user=Depends(get_current_user)):
    """Gate: user must have verified their college email."""
    if not current_user.get("is_email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your college email before performing this action.",
        )
    return current_user

def get_optional_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme_optional),
):
    token = _extract_token(request, bearer_token)
    if not token:
        return None
        
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("typ") not in (None, "access"):
            return None
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        if email is None:
            return None
        if jti and revoked_tokens_collection.find_one({"jti": jti}):
            return None

        user = users_collection.find_one({"email": email})
        if not user:
            return None

        return user_helper(user)
    except JWTError:
        return None
