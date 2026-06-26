from blog_engine.models import Post, PostStatus, Role
from blog_engine.schemas import Principal


FULL_CRUD_ROLES = {Role.ADMIN, Role.EDITOR}


def can_create_post(principal: Principal, status: PostStatus) -> bool:
    if principal.role in FULL_CRUD_ROLES | {Role.AUTHOR}:
        return True
    if principal.role == Role.CONTRIBUTOR:
        return status == PostStatus.DRAFT
    return False


def can_update_post(principal: Principal, post: Post) -> bool:
    if principal.role in FULL_CRUD_ROLES:
        return True
    return principal.role == Role.AUTHOR and post.author_id == principal.user_id


def can_delete_post(principal: Principal, post: Post) -> bool:
    return principal.role in FULL_CRUD_ROLES


def can_read_post(principal: Principal | None, post: Post) -> bool:
    if post.status == PostStatus.PUBLISHED:
        return True
    if principal is None:
        return False
    if principal.role in FULL_CRUD_ROLES:
        return True
    return post.author_id == principal.user_id
