"""
Authentication API endpoints - ÉTAPE 3 COMPLÈTE
This module handles user registration, login, and token generation.
"""

from fastapi import APIRouter, Depends, status, HTTPException, Header, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import secrets

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.core.dependencies import get_db, get_current_user, log_activity
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token, TokenData,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.models.models import User, UserRole as DBUserRole
from app.services.email import send_password_reset_email

PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 2


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
            role=DBUserRole(user_create.role.value),  # recruiter or candidate only
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
    
    # 4. Generate access token
    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )
    
    # 5. Return token + user
    return Token(
        access_token=access_token,
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
    
    # 3. Generate access token
    access_token = create_access_token(
        data={"sub": db_user.email, "user_id": db_user.id}
    )

    log_activity(db, "auth.login", user_id=db_user.id, detail=f"Connexion de {db_user.email}")

    # 4. Return token + user
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            created_at=db_user.created_at.isoformat()
        )
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Request a password reset link.
    Always returns the same message to avoid email enumeration.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_password_token = token
        user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        db.commit()
        background_tasks.add_task(send_password_reset_email, user.email, token)
    return MessageResponse(
        message="Si un compte existe avec cet email, un lien de réinitialisation a été envoyé."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Reset password using a valid reset token.
    """
    user = db.query(User).filter(User.reset_password_token == request.token).first()
    if not user or not user.reset_password_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation invalide ou expiré."
        )
    if datetime.utcnow() > user.reset_password_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation invalide ou expiré."
        )
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_password_token = None
    user.reset_password_token_expires = None
    db.commit()
    log_activity(db, "auth.reset_password", user_id=user.id, detail=f"Mot de passe réinitialisé pour {user.email}")
    return MessageResponse(message="Mot de passe réinitialisé avec succès.")


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
