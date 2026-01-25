from pydantic import BaseModel, EmailStr, Field
from typing import Literal


RoleType = Literal["student", "moderator", "admin"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=6)
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
