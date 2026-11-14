from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from blog_engine.auth import authenticate_user, create_access_token
from blog_engine.database import get_blog_db
from blog_engine.schemas import ErrorResponse, LoginRequest, TokenResponse
from core.config import settings

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
    description=(
        "Returns a JWT for use in the Authorization header. "
        "The browser UI uses the same token in an HttpOnly cookie."
    ),
)
def login(payload: LoginRequest, db: Session = Depends(get_blog_db)) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
