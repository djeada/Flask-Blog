from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from blog_engine import csrf, policy, repository
from blog_engine.auth import get_web_principal
from blog_engine.database import get_blog_db
from blog_engine.models import PostStatus, Role
from blog_engine.schemas import PostCreate, PostUpdate, Principal
from routers.web import render

router = APIRouter(prefix="/admin", include_in_schema=False)

ADMIN_PER_PAGE = 10
DASHBOARD_RECENT_POSTS = 8


def _capability_flags(principal: Principal) -> dict[str, bool]:
    capabilities = principal.capabilities
    return {
        "can_create_draft": "posts.create_draft" in capabilities,
        "can_publish": "posts.publish" in capabilities,
        "can_update_any": "posts.update_any" in capabilities,
        "can_assign_author": "posts.assign_author" in capabilities,
        "can_delete": "posts.delete" in capabilities,
        "can_manage_users": "users.manage" in capabilities,
    }


def _login_redirect(request: Request) -> RedirectResponse:
    return RedirectResponse(f"/login?next={quote(request.url.path)}", status_code=303)


def _denied(
    request: Request,
    principal: Principal,
    message: str,
    status_code: int = 403,
):
    return render(
        request,
        "denied.html",
        principal,
        status_code=status_code,
        message=message,
    )


def _not_found(request: Request, principal: Principal):
    return render(request, "404.html", principal, status_code=404)


def _validate_post_form(
    title: str,
    body: str,
    status_value: str,
) -> tuple[str, str, PostStatus | None, dict[str, str]]:
    errors: dict[str, str] = {}

    clean_title = title.strip()
    clean_body = body.strip()

    if not clean_title:
        errors["title"] = "Title is required."
    elif len(clean_title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."

    if not clean_body:
        errors["body"] = "Body is required."

    post_status: PostStatus | None = None
    try:
        post_status = PostStatus(status_value)
    except ValueError:
        errors["status"] = "Choose a valid status."

    return clean_title, clean_body, post_status, errors


def _post_form_context(
    principal: Principal,
    *,
    editing: bool,
    action: str,
    post=None,
    title: str = "",
    body: str = "",
    status_value: str = PostStatus.DRAFT.value,
    author_id: str = "",
    authors=None,
    errors: dict[str, str] | None = None,
) -> dict:
    return {
        "editing": editing,
        "action": action,
        "post": post,
        "form_title": title,
        "form_body": body,
        "form_status": status_value,
        "form_author_id": author_id,
        "authors": authors or [],
        "errors": errors or {},
        "statuses": [status.value for status in PostStatus],
    }


def _resolve_author_id(
    principal: Principal,
    author_id_value: str,
    default: int,
    db: Session,
) -> tuple[int | None, str | None]:
    if not policy.can_assign_author(principal) or not author_id_value:
        return default, None

    try:
        author_id = int(author_id_value)
    except ValueError:
        return None, "Choose a valid author."
    if not repository.user_exists(db, author_id):
        return None, "That author does not exist."
    return author_id, None


@router.get("")
def dashboard(
    request: Request,
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    published_count = repository.count_published_posts(db)
    draft_count = repository.count_drafts_visible_to(db, principal)
    recent_posts = repository.list_posts_visible_to(
        db, principal, limit=DASHBOARD_RECENT_POSTS
    )
    return render(
        request,
        "admin/dashboard.html",
        principal,
        published_count=published_count,
        draft_count=draft_count,
        total_count=published_count + draft_count,
        recent_posts=recent_posts,
        flags=_capability_flags(principal),
    )


@router.get("/posts")
def post_list(
    request: Request,
    q: str = Query(""),
    status_filter: str = Query("", alias="status"),
    page: int = Query(1, ge=1),
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    total = repository.count_posts_visible_to(
        db, principal, q=q or None, status_filter=status_filter or None
    )
    total_pages = max((total + ADMIN_PER_PAGE - 1) // ADMIN_PER_PAGE, 1)
    page = min(page, total_pages)
    offset = (page - 1) * ADMIN_PER_PAGE
    posts = repository.list_posts_visible_to(
        db,
        principal,
        q=q or None,
        status_filter=status_filter or None,
        limit=ADMIN_PER_PAGE,
        offset=offset,
    )
    return render(
        request,
        "admin/posts.html",
        principal,
        posts=posts,
        q=q,
        status_filter=status_filter,
        total=total,
        page=page,
        per_page=ADMIN_PER_PAGE,
        total_pages=total_pages,
        flags=_capability_flags(principal),
        statuses=[status.value for status in PostStatus],
    )


@router.get("/posts/new")
def new_post_page(
    request: Request,
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    flags = _capability_flags(principal)
    if not flags["can_create_draft"] and not flags["can_publish"]:
        return _denied(request, principal, "Your role cannot create posts.")

    context = _post_form_context(
        principal,
        editing=False,
        action="/admin/posts",
        authors=repository.list_users(db) if flags["can_assign_author"] else [],
    )
    return render(request, "admin/post_form.html", principal, flags=flags, **context)


@router.post("/posts")
def create_post_submit(
    request: Request,
    title: str = Form(""),
    body: str = Form(""),
    status_value: str = Form(PostStatus.DRAFT.value, alias="status"),
    author_id: str = Form(""),
    csrf_token: str = Form("", alias=csrf.CSRF_FORM_FIELD),
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    flags = _capability_flags(principal)
    if not flags["can_create_draft"] and not flags["can_publish"]:
        return _denied(request, principal, "Your role cannot create posts.")

    form_context = _post_form_context(
        principal,
        editing=False,
        action="/admin/posts",
        title=title,
        body=body,
        status_value=status_value,
        author_id=author_id,
        authors=repository.list_users(db) if flags["can_assign_author"] else [],
    )

    if not csrf.csrf_matches(request, csrf_token):
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=403,
            flags=flags,
            **(form_context | {"errors": {"__all__": "Your session expired. Please try again."}}),
        )

    clean_title, clean_body, post_status, errors = _validate_post_form(
        title, body, status_value
    )

    policy_error: str | None = None
    if post_status is not None and not policy.can_create_post(principal, post_status):
        capability_label = (
            "publish posts" if post_status == PostStatus.PUBLISHED else "save drafts"
        )
        policy_error = f"Your role cannot {capability_label}."

    if errors or policy_error:
        if policy_error:
            errors["status"] = policy_error
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=403 if policy_error else 422,
            flags=flags,
            **(form_context | {"errors": errors}),
        )

    author, author_error = _resolve_author_id(principal, author_id, principal.user_id, db)
    if author_error:
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=422,
            flags=flags,
            **(form_context | {"errors": {"author_id": author_error}}),
        )

    repository.create_post(
        db,
        PostCreate(title=clean_title, body=clean_body, status=post_status),
        author,
    )
    return RedirectResponse("/admin/posts", status_code=303)


@router.get("/posts/{post_id}/edit")
def edit_post_page(
    request: Request,
    post_id: int,
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    post = repository.get_post(db, post_id)
    if post is None or not policy.can_read_post(principal, post):
        return _not_found(request, principal)

    flags = _capability_flags(principal)
    if not policy.can_update_post(principal, post):
        return _denied(request, principal, "Your role cannot edit this post.")

    context = _post_form_context(
        principal,
        editing=True,
        action=f"/admin/posts/{post.id}",
        post=post,
        title=post.title,
        body=post.body,
        status_value=post.status.value,
        author_id=str(post.author_id),
        authors=repository.list_users(db) if flags["can_assign_author"] else [],
    )
    return render(request, "admin/post_form.html", principal, flags=flags, **context)


@router.post("/posts/{post_id}")
def update_post_submit(
    request: Request,
    post_id: int,
    title: str = Form(""),
    body: str = Form(""),
    status_value: str = Form(PostStatus.DRAFT.value, alias="status"),
    author_id: str = Form(""),
    csrf_token: str = Form("", alias=csrf.CSRF_FORM_FIELD),
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    post = repository.get_post(db, post_id)
    if post is None or not policy.can_read_post(principal, post):
        return _not_found(request, principal)

    flags = _capability_flags(principal)
    if not policy.can_update_post(principal, post):
        return _denied(request, principal, "Your role cannot edit this post.")

    form_context = _post_form_context(
        principal,
        editing=True,
        action=f"/admin/posts/{post.id}",
        post=post,
        title=title,
        body=body,
        status_value=status_value,
        author_id=author_id,
        authors=repository.list_users(db) if flags["can_assign_author"] else [],
    )

    if not csrf.csrf_matches(request, csrf_token):
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=403,
            flags=flags,
            **(form_context | {"errors": {"__all__": "Your session expired. Please try again."}}),
        )

    clean_title, clean_body, post_status, errors = _validate_post_form(
        title, body, status_value
    )

    if (
        not policy.can_assign_author(principal)
        and author_id
        and _parse_author_id(author_id) not in (None, post.author_id)
    ):
        errors["author_id"] = "You cannot reassign this post's author."

    if errors:
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=422,
            flags=flags,
            **(form_context | {"errors": errors}),
        )

    author, author_error = _resolve_author_id(principal, author_id, post.author_id, db)
    if author_error:
        return render(
            request,
            "admin/post_form.html",
            principal,
            status_code=422,
            flags=flags,
            **(form_context | {"errors": {"author_id": author_error}}),
        )

    repository.update_post(
        db,
        post,
        PostUpdate(
            title=clean_title,
            body=clean_body,
            status=post_status,
            author_id=author,
        ),
    )
    return RedirectResponse("/admin/posts", status_code=303)


def _parse_author_id(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@router.post("/posts/{post_id}/delete")
def delete_post_submit(
    request: Request,
    post_id: int,
    csrf_token: str = Form("", alias=csrf.CSRF_FORM_FIELD),
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    post = repository.get_post(db, post_id)
    if post is None:
        return _not_found(request, principal)

    if not csrf.csrf_matches(request, csrf_token):
        return RedirectResponse("/admin/posts", status_code=303)

    if not policy.can_delete_post(principal, post):
        return _denied(request, principal, "Your role cannot delete posts.")

    repository.delete_post(db, post)
    return RedirectResponse("/admin/posts", status_code=303)


@router.get("/users")
def user_overview(
    request: Request,
    principal: Principal | None = Depends(get_web_principal),
    db: Session = Depends(get_blog_db),
):
    if principal is None:
        return _login_redirect(request)

    if not policy.can_manage_users(principal):
        return _denied(request, principal, "Only Admins can manage users.")

    users = repository.list_users(db)
    role_capabilities = repository.list_role_capabilities(db)
    role_descriptions = repository.list_role_descriptions(db)
    capability_labels = {
        key: label for key, (label, _) in policy.CAPABILITY_DEFINITIONS.items()
    }
    return render(
        request,
        "admin/users.html",
        principal,
        users=users,
        roles=list(Role),
        role_capabilities=role_capabilities,
        role_descriptions=role_descriptions,
        capability_labels=capability_labels,
        flags=_capability_flags(principal),
    )
