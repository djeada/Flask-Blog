from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from blog_engine.database import get_blog_db
from blog_engine.models import BlogUser, Role
from blog_engine.schemas import Principal
from core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def _bearer_token(
    request: Request, credentials: HTTPAuthorizationCredentials | None
) -> str | None:
    if credentials is not None:
        return credentials.credentials
    authorization = request.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return request.cookies.get("access_token")


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_blog_db),
) -> Principal:
    token = _bearer_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    user_id = payload.get("user_id")
    role_value = payload.get("role")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = None
    if user_id is not None:
        user = db.get(BlogUser, int(user_id))
    if user is None:
        user = db.query(BlogUser).filter(BlogUser.username == username).one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = Role(role_value) if role_value else user.role
    if role != user.role:
        role = user.role

    return Principal(user_id=user.id, username=user.username, role=role)


def get_optional_principal(
    request: Request,
    db: Session = Depends(get_blog_db),
) -> Principal | None:
    try:
        return get_current_principal(request, None, db)
    except HTTPException:
        return None
