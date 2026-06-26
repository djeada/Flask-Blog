from sqlalchemy import select
from sqlalchemy.orm import Session

from blog_engine.models import BlogUser, Post, PostStatus
from blog_engine.schemas import PostCreate, PostUpdate


def list_published_posts(db: Session) -> list[Post]:
    return list(
        db.scalars(
            select(Post)
            .where(Post.status == PostStatus.PUBLISHED)
            .order_by(Post.created_at.desc(), Post.id.desc())
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
    update_data = post_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)
    db.commit()
