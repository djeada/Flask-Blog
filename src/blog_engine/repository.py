from sqlalchemy import func, select
from sqlalchemy.orm import Session

from blog_engine.models import BlogUser, Post, PostStatus, Role
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


def count_admins(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(BlogUser).where(BlogUser.role == Role.ADMIN)) or 0


def set_user_role(db: Session, user: BlogUser, role: Role) -> BlogUser:
    user.role = role
    db.commit()
    db.refresh(user)
    return user
