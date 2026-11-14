from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from blog_engine import repository
from blog_engine.database import get_blog_db
from blog_engine.models import BlogUser
from blog_engine.schemas import Principal
from blog_engine.security import hash_password, verify_password
from core.config import settings

ACCESS_COOKIE_NAME = "access_token"
bearer_scheme = HTTPBearer(auto_error=False)
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def authenticate_user(db: Session, username: str, password: str) -> BlogUser | None:
    user = repository.get_user_by_username(db, username)
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    if not verify_password(password, password_hash) or user is None:
        return None
    return user


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(user: BlogUser) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role.value,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def principal_from_token(token: str, db: Session) -> Principal:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError:
        raise _unauthorized("Invalid authentication credentials") from None

    user = None
    user_id = payload.get("user_id")
    if user_id is not None:
        try:
            user = db.get(BlogUser, int(user_id))
        except (TypeError, ValueError):
            raise _unauthorized("Invalid authentication credentials") from None
    if user is None:
        user = db.scalars(
            select(BlogUser).where(BlogUser.username == payload["sub"])
        ).one_or_none()
    if user is None:
        raise _unauthorized("User not found")

    # The database is the source of truth for the role and its capabilities.
    return Principal(
        user_id=user.id,
        username=user.username,
        role=user.role,
        capabilities=repository.get_role_capabilities(db, user.role),
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_blog_db),
) -> Principal:
    if credentials is None:
        raise _unauthorized("Authentication required")
    return principal_from_token(credentials.credentials, db)


def get_optional_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_blog_db),
) -> Principal | None:
    if credentials is None:
        return None
    try:
        return principal_from_token(credentials.credentials, db)
    except HTTPException:
        return None


def get_web_principal(
    request: Request,
    db: Session = Depends(get_blog_db),
) -> Principal | None:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return None
    try:
        return principal_from_token(token, db)
    except HTTPException:
        return None
