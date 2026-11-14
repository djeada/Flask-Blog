from blog_engine.models import Post, PostStatus, Role
from blog_engine.schemas import Principal

CAPABILITY_ORDER: tuple[str, ...] = (
    "posts.read_published",
    "posts.read_own_draft",
    "posts.read_any_draft",
    "posts.create_draft",
    "posts.publish",
    "posts.update_own",
    "posts.update_any",
    "posts.assign_author",
    "posts.delete",
    "users.manage",
)

CAPABILITY_DEFINITIONS: dict[str, tuple[str, str]] = {
    "posts.read_published": (
        "Read published posts",
        "Available to everyone, including anonymous visitors.",
    ),
    "posts.read_own_draft": (
        "Read own drafts",
        "Drafts are visible to their author before publishing.",
    ),
    "posts.read_any_draft": (
        "Read any draft",
        "Can open drafts written by other users.",
    ),
    "posts.create_draft": (
        "Create drafts",
        "Can save unpublished work.",
    ),
    "posts.publish": (
        "Create published posts",
        "Can create posts that are immediately public.",
    ),
    "posts.update_own": (
        "Update own posts",
        "Can edit posts they authored.",
    ),
    "posts.update_any": (
        "Update any post",
        "Can edit posts written by anyone.",
    ),
    "posts.assign_author": (
        "Assign post authors",
        "Can create or update posts on behalf of another user.",
    ),
    "posts.delete": (
        "Delete posts",
        "Can permanently remove posts.",
    ),
    "users.manage": (
        "Manage users",
        "Can list users, change roles, and edit role permissions.",
    ),
}

DEFAULT_ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.ADMIN: "Full control over posts, drafts, and user roles.",
    Role.EDITOR: "Full control over all posts and drafts, but cannot manage users.",
    Role.AUTHOR: "Can write and publish posts, and edit only their own posts.",
    Role.CONTRIBUTOR: "Can save drafts, but cannot publish, edit, or delete them.",
    Role.SUBSCRIBER: "Can read published posts and any draft assigned to them as author.",
}

DEFAULT_ROLE_CAPABILITIES: dict[Role, frozenset[str]] = {
    Role.ADMIN: frozenset(CAPABILITY_ORDER),
    Role.EDITOR: frozenset(CAPABILITY_ORDER) - {"users.manage"},
    Role.AUTHOR: frozenset(
        {
            "posts.read_published",
            "posts.read_own_draft",
            "posts.create_draft",
            "posts.publish",
            "posts.update_own",
        }
    ),
    Role.CONTRIBUTOR: frozenset(
        {
            "posts.read_published",
            "posts.read_own_draft",
            "posts.create_draft",
        }
    ),
    Role.SUBSCRIBER: frozenset(
        {
            "posts.read_published",
            "posts.read_own_draft",
        }
    ),
}


def all_capabilities() -> frozenset[str]:
    return frozenset(CAPABILITY_ORDER)


def can_create_post(principal: Principal, status: PostStatus) -> bool:
    capability = "posts.publish" if status == PostStatus.PUBLISHED else "posts.create_draft"
    return capability in principal.capabilities


def can_update_post(principal: Principal, post: Post) -> bool:
    if "posts.update_any" in principal.capabilities:
        return True
    return "posts.update_own" in principal.capabilities and post.author_id == principal.user_id


def can_assign_author(principal: Principal) -> bool:
    return "posts.assign_author" in principal.capabilities


def can_delete_post(principal: Principal, post: Post) -> bool:
    return "posts.delete" in principal.capabilities


def can_read_post(principal: Principal | None, post: Post) -> bool:
    if post.status == PostStatus.PUBLISHED:
        return True
    if principal is None:
        return False
    if "posts.read_any_draft" in principal.capabilities:
        return True
    return (
        "posts.read_own_draft" in principal.capabilities
        and post.author_id == principal.user_id
    )


def can_manage_users(principal: Principal) -> bool:
    return "users.manage" in principal.capabilities
