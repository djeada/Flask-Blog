from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from blog_engine import policy, repository
from blog_engine.auth import get_current_principal, get_optional_principal
from blog_engine.database import get_blog_db
from blog_engine.models import PostStatus, Role
from blog_engine.schemas import ErrorResponse, PostCreate, PostResponse, PostUpdate, Principal

ERR_401 = {"model": ErrorResponse, "description": "Missing, invalid or expired token"}
ERR_429 = {"model": ErrorResponse, "description": "Rate limit exceeded"}

router = APIRouter(prefix="/api/v1/posts", tags=["posts"], responses={429: ERR_429})


def _author_id_for_create(
    payload: PostCreate, principal: Principal, db: Session
) -> int:
    if principal.role in {Role.ADMIN, Role.EDITOR}:
        author_id = payload.author_id or principal.user_id
    else:
        if payload.author_id is not None and payload.author_id != principal.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create for another author")
        author_id = principal.user_id

    if not repository.user_exists(db, author_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="author_id does not exist")
    return author_id


@router.get(
    "",
    response_model=list[PostResponse],
    summary="List published posts",
    description="Public. Returns published posts, newest first.",
)
def list_posts(
    response: Response,
    limit: int = Query(20, ge=1, le=100, description="Maximum posts to return."),
    offset: int = Query(0, ge=0, description="Posts to skip."),
    db: Session = Depends(get_blog_db),
) -> list[PostResponse]:
    response.headers["Cache-Control"] = "public, max-age=60"
    return repository.list_published_posts(db, limit=limit, offset=offset)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Retrieve a post by ID",
)
def retrieve_post(
    post_id: int,
    response: Response,
    principal: Principal | None = Depends(get_optional_principal),
    db: Session = Depends(get_blog_db),
) -> PostResponse:
    post = repository.get_post(db, post_id)
    if post is None or not policy.can_read_post(principal, post):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.status == PostStatus.PUBLISHED:
        response.headers["Cache-Control"] = "public, max-age=60"
    else:
        response.headers["Cache-Control"] = "private, no-store"
    return post


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 401: ERR_401, 403: {"model": ErrorResponse}},
    summary="Create a post",
)
def create_post(
    payload: PostCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_blog_db),
) -> PostResponse:
    if not policy.can_create_post(principal, payload.status):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create this post")

    author_id = _author_id_for_create(payload, principal, db)
    return repository.create_post(db, payload, author_id)


@router.put(
    "/{post_id}",
    response_model=PostResponse,
    responses={
        400: {"model": ErrorResponse},
        401: ERR_401,
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
    summary="Update a post",
)
def update_post(
    post_id: int,
    payload: PostUpdate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_blog_db),
) -> PostResponse:
    post = repository.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not policy.can_update_post(principal, post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update this post")
    if principal.role not in {Role.ADMIN, Role.EDITOR} and payload.author_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reassign post author")
    if payload.author_id is not None and not repository.user_exists(db, payload.author_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="author_id does not exist")

    return repository.update_post(db, post, payload)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: ERR_401, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Delete a post",
)
def delete_post(
    post_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_blog_db),
) -> Response:
    post = repository.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not policy.can_delete_post(principal, post):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete posts")

    repository.delete_post(db, post)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
