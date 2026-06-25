from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    recruiter = "recruiter"
    candidate = "candidate"


class UserRolePublic(str, Enum):
    """Roles available for public self-registration — admin is excluded."""
    recruiter = "recruiter"
    candidate = "candidate"


class UserCreate(BaseModel):
    """Schema for user registration — admin role is not allowed."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: UserRolePublic = UserRolePublic.recruiter


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str


class TokenData(BaseModel):
    """JWT token payload data"""
    sub: str  # user email
    user_id: int


class Token(BaseModel):
    """Response for login/register endpoints"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """User info response"""
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: str

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class MessageResponse(BaseModel):
    message: str
