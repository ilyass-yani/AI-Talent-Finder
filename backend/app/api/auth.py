"""
Authentication API endpoints - ÉTAPE 3 COMPLÈTE
This module handles user registration, login, and token generation.
"""

from fastapi import APIRouter, Depends, status, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from jose import JWTError
from pydantic import BaseModel

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.core.dependencies import get_db, get_current_user
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, TokenData
from app.models.models import User, UserRole as DBUserRole


router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: Session = Depends(get_db)) -> Token:
    """
    Register a new user (ÉTAPE 3)
    
    - **email**: User email address (must be unique)
    - **password**: User password (min 6 characters)
    - **full_name**: User full name
    - **role**: User role (admin, recruiter, candidate) - defaults to recruiter
    
    Returns: Token with access_token, token_type, and user info
    """
    try:
        # 1. Check if user already exists
        existing_user = db.query(User).filter(User.email == user_create.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # 2. Hash password
        hashed_password = get_password_hash(user_create.password)
        
        # 3. Create user in database
        db_user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            role=DBUserRole(user_create.role.value),
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )
    
    # 4. Generate access + refresh tokens
    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )

    # 5. Return tokens + user
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at.isoformat()
        )
    )


@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    User login endpoint (ÉTAPE 3)
    
    - **email**: User email address
    - **password**: User password
    
    Returns: Token with access_token, token_type, and user info
    """
    # 1. Find user by email
    db_user = db.query(User).filter(User.email == user_login.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 2. Verify password
    if not verify_password(user_login.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # 3. Generate access + refresh tokens
    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )

    # 4. Return tokens + user
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at.isoformat()
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user information (ÉTAPE 3)

    Requires: Valid JWT token in Authorization header
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        created_at=current_user.created_at.isoformat()
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=Token)
async def refresh_access_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    """Exchange a valid refresh token for a fresh access + refresh token pair."""
    try:
        token_data = decode_token(payload.refresh_token, expected_type="refresh")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at.isoformat(),
        ),
    )
