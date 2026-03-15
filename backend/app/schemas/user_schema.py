from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional


RoleType = Literal["student", "moderator", "admin"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)
    dept: str
    year: int
    section: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    dept: str
    year: int
    section: str
    role: RoleType
    verified_seller: bool = False
    
    cluster_id: Optional[str] = None
    verified_by_domain: bool = False
    wallet_points: int = 0


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    dept: str
    year: int
    section: str
    role: RoleType
    is_active: bool
