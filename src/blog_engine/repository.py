from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from blog_engine import policy
from blog_engine.models import BlogUser, Post, PostStatus, Role, RoleCapability, RoleProfile
from blog_engine.schemas import PostCreate, PostUpdate


def list_published_posts(db: Session, limit: int = 20, offset: int = 0) -> list[Post]:
    return list(
        db.scalars(
            select(Post)
            .where(Post.status == PostStatus.PUBLISHED)
            .order_by(Post.created_at.desc(), Post.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


def get_post(db: Session, post_id: int) -> Post | None:
    return db.get(Post, post_id)


def count_published_posts(db: Session) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Post).where(Post.status == PostStatus.PUBLISHED)
        )
        or 0
    )


def user_exists(db: Session, user_id: int) -> bool:
    return db.get(BlogUser, user_id) is not None


def create_post(db: Session, post_in: PostCreate, author_id: int) -> Post:
    post = Post(
        title=post_in.title,
        body=post_in.body,
        status=post_in.status,
        author_id=author_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, post: Post, post_in: PostUpdate) -> Post:
    # Every PostUpdate field is non-nullable on the model, so an explicit null means "unchanged".
    update_data = post_in.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)
    db.commit()


def list_users(db: Session) -> list[BlogUser]:
    return list(db.scalars(select(BlogUser).order_by(BlogUser.id)))


def get_user(db: Session, user_id: int) -> BlogUser | None:
    return db.get(BlogUser, user_id)


def get_user_by_username(db: Session, username: str) -> BlogUser | None:
    return db.scalars(select(BlogUser).where(BlogUser.username == username)).one_or_none()


def count_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(BlogUser).where(BlogUser.role == Role.ADMIN)) or 0


def set_user_role(db: Session, user: BlogUser, role: Role) -> BlogUser:
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def ensure_role_defaults(db: Session) -> None:
    for role in Role:
        if db.get(RoleProfile, role) is not None:
            continue
        db.add(
            RoleProfile(
                role=role,
                description=policy.DEFAULT_ROLE_DESCRIPTIONS[role],
            )
        )
        for capability in policy.CAPABILITY_ORDER:
            if capability in policy.DEFAULT_ROLE_CAPABILITIES[role]:
                db.add(RoleCapability(role=role, capability=capability))
    db.commit()


def get_role_capabilities(db: Session, role: Role) -> frozenset[str]:
    if role == Role.ADMIN:
        return policy.all_capabilities()
    return frozenset(
        db.scalars(
            select(RoleCapability.capability).where(RoleCapability.role == role)
        )
    )


def list_role_capabilities(db: Session) -> dict[Role, frozenset[str]]:
    capabilities: dict[Role, set[str]] = {role: set() for role in Role}
    for role, capability in db.execute(
        select(RoleCapability.role, RoleCapability.capability)
    ):
        capabilities[role].add(capability)
    capabilities[Role.ADMIN] = set(policy.all_capabilities())
    return {role: frozenset(values) for role, values in capabilities.items()}


def list_role_descriptions(db: Session) -> dict[Role, str]:
    return {
        profile.role: profile.description
        for profile in db.scalars(select(RoleProfile))
    }


def update_role_settings(
    db: Session,
    role: Role,
    description: str | None,
    capabilities: list[str] | None,
) -> None:
    profile = db.get(RoleProfile, role)
    if profile is None:
        db.add(
            RoleProfile(
                role=role,
                description=description or policy.DEFAULT_ROLE_DESCRIPTIONS[role],
            )
        )
    elif description is not None:
        profile.description = description

    if capabilities is not None:
        db.execute(delete(RoleCapability).where(RoleCapability.role == role))
        for capability in capabilities:
            db.add(RoleCapability(role=role, capability=capability))
    db.commit()
