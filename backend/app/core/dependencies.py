from typing import Generator, Optional
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .security import decode_token
from app.schemas.user import TokenData
from app.models.models import User


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to provide database sessions.
    
    Usage in routes:
        from fastapi import Depends
        from app.core.database import get_db
        
        @router.get("/items")
        def read_items(db: Session = Depends(get_db)):
            # Use db session here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency function to get the current authenticated user.
    Extracts and validates JWT token from Authorization header.
    
    Usage in protected routes:
        from fastapi import Depends
        from app.core.dependencies import get_current_user
        from app.models.models import User
        
        @router.get("/protected")
        def protected_endpoint(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    
    Args:
        authorization: Bearer token from Authorization header
        db: Database session
        
    Returns:
        User object of the authenticated user
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    # 1. Extract and validate token
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    # 2. Decode token
    try:
        token_data: TokenData = decode_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
