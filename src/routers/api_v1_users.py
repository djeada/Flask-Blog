from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from blog_engine import policy, repository
from blog_engine.auth import get_current_principal
from blog_engine.database import get_blog_db
from blog_engine.models import Role
from blog_engine.schemas import ErrorResponse, Principal, RoleUpdate, UserResponse

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)


def _require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if not policy.can_manage_users(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return principal


@router.get("", response_model=list[UserResponse], summary="List users (Admin)")
def list_users(
    _: Principal = Depends(_require_admin), db: Session = Depends(get_blog_db)
) -> list[UserResponse]:
    return repository.list_users(db)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    summary="Change a user's role (Admin)",
)
def update_user_role(
    user_id: int,
    payload: RoleUpdate,
    _: Principal = Depends(_require_admin),
    db: Session = Depends(get_blog_db),
) -> UserResponse:
    user = repository.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if (
        user.role == Role.ADMIN
        and payload.role != Role.ADMIN
        and repository.count_admins(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cannot demote the last Admin"
        )
    return repository.set_user_role(db, user, payload.role)
