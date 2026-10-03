from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from blog_engine.database import get_blog_db
from blog_engine.models import BlogUser
from blog_engine.schemas import Principal
from core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_blog_db),
) -> Principal:
    if credentials is None:
        raise _unauthorized("Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
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

    # The database is the source of truth for the role; token claims are ignored.
    return Principal(user_id=user.id, username=user.username, role=user.role)


def get_optional_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_blog_db),
) -> Principal | None:
    try:
        return get_current_principal(credentials, db)
    except HTTPException:
        return None
