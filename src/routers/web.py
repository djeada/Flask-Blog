from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from blog_engine import csrf, policy, repository
from blog_engine.auth import (
    ACCESS_COOKIE_NAME,
    authenticate_user,
    create_access_token,
    get_web_principal,
)
from blog_engine.database import get_blog_db
from blog_engine.demo import DEMO_USERS, demo_password
from blog_engine.schemas import Principal
from core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(include_in_schema=False)


def _safe_next(next_url: str | None) -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def render(
    request: Request,
    name: str,
    principal: Principal | None,
    status_code: int = 200,
    **context,
):
    token = request.cookies.get(csrf.CSRF_COOKIE_NAME)
    issued_new_token = token is None
    if issued_new_token:
        token = csrf.generate_csrf_token()

    response = templates.TemplateResponse(
        name,
        {
            "request": request,
            "principal": principal,
            "app_name": settings.APP_NAME,
            "csrf_token": token,
        }
        | context,
        status_code=status_code,
    )
    if issued_new_token:
        response.set_cookie(
            csrf.CSRF_COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            secure=settings.SESSION_COOKIE_SECURE,
            path="/",
        )
    return response


def _demo_accounts() -> list[dict[str, str]]:
    if not settings.BLOG_SEED_DEMO:
        return []
    return [
        {"username": username, "password": demo_password(username)}
        for _, username, _ in DEMO_USERS
    ]


@router.get("/")
def index(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    total = repository.count_published_posts(db)
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    posts = repository.list_published_posts(db, limit=per_page, offset=offset)
    return render(
        request,
        "index.html",
        principal,
        posts=posts,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        first_item=offset + 1 if total else 0,
        last_item=min(offset + len(posts), total),
    )


@router.get("/posts/{post_id}")
def post_detail(
    request: Request,
    post_id: int,
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    post = repository.get_post(db, post_id)
    if post is None or not policy.can_read_post(principal, post):
        return render(request, "404.html", principal, status_code=404)
    return render(request, "post_detail.html", principal, post=post)


@router.get("/login")
def login_page(
    request: Request,
    next: str = "/",
    principal: Principal | None = Depends(get_web_principal),
):
    if principal is not None:
        return RedirectResponse(_safe_next(next), status_code=303)
    return render(
        request,
        "login.html",
        None,
        next_url=_safe_next(next),
        demo_accounts=_demo_accounts(),
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    next_url: str = Form("/", alias="next"),
    csrf_token: str = Form("", alias=csrf.CSRF_FORM_FIELD),
    db: Session = Depends(get_blog_db),
):
    if not csrf.csrf_matches(request, csrf_token):
        return render(
            request,
            "login.html",
            None,
            next_url=_safe_next(next_url),
            error="Your session expired. Please try again.",
            username=username,
            demo_accounts=_demo_accounts(),
            status_code=403,
        )

    if not username.strip() or not password:
        return render(
            request,
            "login.html",
            None,
            next_url=_safe_next(next_url),
            error="Username and password are required.",
            username=username,
            demo_accounts=_demo_accounts(),
            status_code=401,
        )

    user = authenticate_user(db, username.strip(), password)
    if user is None:
        return render(
            request,
            "login.html",
            None,
            next_url=_safe_next(next_url),
            error="Invalid username or password.",
            username=username,
            demo_accounts=_demo_accounts(),
            status_code=401,
        )

    response = RedirectResponse(_safe_next(next_url), status_code=303)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        create_access_token(user),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=settings.SESSION_COOKIE_SECURE,
        path="/",
    )
    return response


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form("", alias=csrf.CSRF_FORM_FIELD),
) -> RedirectResponse:
    if not csrf.csrf_matches(request, csrf_token):
        return RedirectResponse("/", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    return response
