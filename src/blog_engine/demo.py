from sqlalchemy.orm import Session

from blog_engine.models import BlogUser, Post, PostStatus, Role


DEMO_USERS = [
    (1, "admin", Role.ADMIN),
    (2, "editor", Role.EDITOR),
    (3, "author", Role.AUTHOR),
    (4, "contributor", Role.CONTRIBUTOR),
    (5, "subscriber", Role.SUBSCRIBER),
]

DEMO_POSTS = [
    {
        "title": "Welcome to the API demo",
        "body": "This published article is seeded as demo content.",
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
    },
    {
        "title": "Draft workflow notes",
        "body": "This draft demonstrates private post behavior.",
        "status": PostStatus.DRAFT,
        "author_id": 3,
    },
]


def seed_demo_content(db: Session) -> None:
    for user_id, username, role in DEMO_USERS:
        if db.get(BlogUser, user_id) is None:
            db.add(BlogUser(id=user_id, username=username, role=role))
    db.commit()

    has_posts = db.query(Post).first() is not None
    if has_posts:
        return

    for post_data in DEMO_POSTS:
        db.add(Post(**post_data))
    db.commit()
