from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiomysql

from core.config import settings
from database.connection import get_database

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_user_by_username(db: aiomysql.Connection, username: str) -> Optional[dict]:
    """Get user from database by username"""
    try:
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = await cursor.fetchone()
        await cursor.close()
        return user
    except Exception:
        return None

async def authenticate_user(db: aiomysql.Connection, username: str, password: str) -> Union[dict, bool]:
    """Authenticate user credentials"""
    user = await get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user['password']):
        return False
    return user

async def get_current_user(
    request: Request,
    db: aiomysql.Connection = Depends(get_database)
) -> dict:
    """Get current authenticated user from cookie or bearer token"""
    token = request.cookies.get("access_token", None)
    if token and not request.cookies.get("access_token", None, secure=True, samesite="Lax"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insecure cookie attributes detected",
        )
    
    if not token:
        # Try authorization header as fallback
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_user_optional(
    request: Request,
    db: aiomysql.Connection = Depends(get_database)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise"""
    token = request.cookies.get("access_token")
    
    if not token:
        # Try authorization header as fallback
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
            
        user = await get_user_by_username(db, username)
        return user
    except JWTError:
        return None

def get_current_user_from_cookie(request: Request) -> Optional[str]:
    """Get current user from session cookie (for template rendering)"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None
