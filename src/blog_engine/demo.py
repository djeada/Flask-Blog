from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from blog_engine.models import BlogUser, Post, PostStatus, Role
from blog_engine.security import hash_password

DEMO_PASSWORD_SUFFIX = "123"
_demo_password_hashes: dict[str, str] = {}

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
        "created_at": datetime(2026, 10, 3, 9, 0),
        "updated_at": datetime(2026, 10, 3, 9, 0),
    },
    {
        "title": "Draft workflow notes",
        "body": "This draft demonstrates private post behavior.",
        "status": PostStatus.DRAFT,
        "author_id": 3,
        "created_at": datetime(2026, 10, 5, 14, 30),
        "updated_at": datetime(2026, 10, 5, 14, 30),
    },
    {
        "title": "Designing role-based access for a small API",
        "body": (
            "Permissions are easiest to reason about when every rule answers one question: "
            "who can perform this action on this resource?\n\n"
            "We keep that decision in a single policy module, so route handlers stay small and "
            "the rules can be tested without spinning up the whole application."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
        "created_at": datetime(2026, 10, 20, 10, 15),
        "updated_at": datetime(2026, 10, 20, 10, 15),
    },
    {
        "title": "Pagination patterns that scale",
        "body": (
            "Offset pagination is perfectly fine for a blog. It is simple to explain, easy to "
            "link to, and fast enough on the datasets most small sites actually have.\n\n"
            "When the table grows into the millions, cursor pagination becomes attractive, but "
            "that is a problem to solve later rather than early."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 2,
        "created_at": datetime(2026, 10, 26, 8, 45),
        "updated_at": datetime(2026, 10, 26, 8, 45),
    },
    {
        "title": "A practical guide to JWT expiration",
        "body": (
            "Short-lived access tokens limit the damage from a leaked credential. A one-hour "
            "lifetime is a comfortable default for a small application.\n\n"
            "Expiration is not optional: reject tokens without an exp claim, and read the role "
            "from the database instead of trusting whatever the token says."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
        "created_at": datetime(2026, 11, 1, 12, 0),
        "updated_at": datetime(2026, 11, 1, 12, 0),
    },
    {
        "title": "Writing drafts without breaking production",
        "body": (
            "A status field turns a post into a small state machine. Drafts are private by "
            "default, published posts are public, and everyone else sees a 404.\n\n"
            "That one rule keeps unfinished writing out of search results and off the homepage "
            "without requiring a separate staging system."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 3,
        "created_at": datetime(2026, 11, 3, 16, 20),
        "updated_at": datetime(2026, 11, 3, 16, 20),
    },
    {
        "title": "SQLite is enough for your first thousand readers",
        "body": (
            "A single-file database removes an entire category of deployment work. Backups are "
            "a file copy, local development matches production, and there is no server to tune.\n\n"
            "Move on to Postgres when you have a reason, not because a checklist told you to."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 2,
        "created_at": datetime(2026, 11, 5, 9, 10),
        "updated_at": datetime(2026, 11, 5, 9, 10),
    },
    {
        "title": "Rate limiting without a Redis cluster",
        "body": (
            "A per-client sliding window kept in memory is surprisingly effective for a demo "
            "and a single-process deployment.\n\n"
            "The important part is the contract: return clear headers, a Retry-After value, and "
            "document the limit so clients can back off politely."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
        "created_at": datetime(2026, 11, 6, 11, 25),
        "updated_at": datetime(2026, 11, 6, 11, 25),
    },
    {
        "title": "Planning content with status fields",
        "body": (
            "Editorial workflows get complicated quickly. Start with two states, draft and "
            "published, and add scheduled or archived later if there is real demand.\n\n"
            "Every extra state is a branch in the UI, the API, and the tests, so earn it."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 3,
        "created_at": datetime(2026, 11, 7, 15, 40),
        "updated_at": datetime(2026, 11, 7, 15, 40),
    },
    {
        "title": "OpenAPI docs as a product surface",
        "body": (
            "Generated documentation is only useful when it includes examples and error "
            "responses. A schema without a sample payload leaves the reader guessing.\n\n"
            "We document the 401, 403, 404, and 429 cases next to the happy path, because those "
            "are the responses integrations actually have to handle."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 2,
        "created_at": datetime(2026, 11, 8, 10, 5),
        "updated_at": datetime(2026, 11, 8, 10, 5),
    },
    {
        "title": "Testing permissions is testing behavior",
        "body": (
            "The useful test does not assert that a decorator exists. It asserts that a "
            "Contributor receives a 403 when publishing, and a 201 when saving a draft.\n\n"
            "Writing the test from the outside makes it resilient to refactoring and documents "
            "the policy for the next person."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 3,
        "created_at": datetime(2026, 11, 9, 13, 50),
        "updated_at": datetime(2026, 11, 9, 13, 50),
    },
    {
        "title": "The case for server-rendered admin pages",
        "body": (
            "Most admin screens are forms over a database. Server-rendered HTML handles that "
            "well, ships less JavaScript, and keeps authentication in an HttpOnly cookie.\n\n"
            "A sprinkling of progressive enhancement is enough for the interactions that "
            "actually need to happen without a full page load."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
        "created_at": datetime(2026, 11, 10, 9, 30),
        "updated_at": datetime(2026, 11, 10, 9, 30),
    },
    {
        "title": "Small deployments, boring infrastructure",
        "body": (
            "One container, one volume, one health check. That setup has fewer moving parts than "
            "a local development stack and is easy to reason about at 2 a.m.\n\n"
            "Boring infrastructure is a feature: it lets the team spend its attention on the "
            "product instead of the platform."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 2,
        "created_at": datetime(2026, 11, 11, 17, 15),
        "updated_at": datetime(2026, 11, 11, 17, 15),
    },
    {
        "title": "What we learned shipping v1",
        "body": (
            "The first release was mostly about removing things: fewer endpoints, fewer states, "
            "fewer dependencies. What remained was easier to test and explain.\n\n"
            "The next version can add features. The first one needed to be trustworthy."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 3,
        "created_at": datetime(2026, 11, 12, 11, 0),
        "updated_at": datetime(2026, 11, 12, 11, 0),
    },
    {
        "title": "A release checklist for small teams",
        "body": (
            "Run the tests, check the migrations against a copy of the real database, and verify "
            "the health endpoint after deployment.\n\n"
            "A short checklist that people actually follow beats a long one that lives in a wiki "
            "nobody opens."
        ),
        "status": PostStatus.PUBLISHED,
        "author_id": 1,
        "created_at": datetime(2026, 11, 13, 8, 20),
        "updated_at": datetime(2026, 11, 13, 8, 20),
    },
    {
        "title": "Notes from the editor rewrite",
        "body": (
            "We are experimenting with a simpler editor and better previews for contributors. "
            "This draft collects the open questions before we commit to a direction."
        ),
        "status": PostStatus.DRAFT,
        "author_id": 4,
        "created_at": datetime(2026, 11, 13, 14, 40),
        "updated_at": datetime(2026, 11, 13, 14, 40),
    },
]


def demo_password(username: str) -> str:
    return f"{username}{DEMO_PASSWORD_SUFFIX}"


def demo_password_hash(username: str) -> str:
    if username not in _demo_password_hashes:
        _demo_password_hashes[username] = hash_password(demo_password(username))
    return _demo_password_hashes[username]


def seed_demo_content(db: Session) -> None:
    for user_id, username, role in DEMO_USERS:
        user = db.get(BlogUser, user_id)
        if user is None:
            db.add(
                BlogUser(
                    id=user_id,
                    username=username,
                    role=role,
                    password_hash=demo_password_hash(username),
                )
            )
        elif not user.password_hash:
            user.password_hash = demo_password_hash(username)
    db.commit()

    existing_titles = set(db.scalars(select(Post.title)))
    for post_data in DEMO_POSTS:
        if post_data["title"] not in existing_titles:
            db.add(Post(**post_data))
    db.commit()
