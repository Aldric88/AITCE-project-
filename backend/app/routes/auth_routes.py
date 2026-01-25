from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user_schema import UserCreate, UserResponse, TokenResponse
from app.services.user_service import get_user_by_email, create_user, authenticate_user
from app.utils.security import create_access_token
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate):
    existing = get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = create_user(user.model_dump())
    return new_user


# Swagger-compatible: OAuth2 form (username=email, password)
@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Swagger sends username; we use it as email
    user = authenticate_user(form_data.username, form_data.password)

    if user == "BANNED":
        raise HTTPException(
            status_code=403, detail="Your account has been disabled"
        )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(current_user=Depends(get_current_user)):
    return current_user


# Example protected route for moderators/admins
@router.get("/moderator-area")
def moderator_area(current_user=Depends(require_role(["moderator", "admin"]))):
    return {"message": "Welcome Moderator/Admin", "user": current_user}
