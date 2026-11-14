import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine.database import Base, get_blog_db
from blog_engine.demo import DEMO_POSTS, seed_demo_content
from blog_engine.models import PostStatus, Role
from blog_engine.repository import ensure_role_defaults
from core.config import settings
from main import app, rate_limit_buckets

PUBLISHED_SEED_COUNT = sum(
    1 for post in DEMO_POSTS if post["status"] == PostStatus.PUBLISHED
)
SEED_TOTAL_PAGES = (PUBLISHED_SEED_COUNT + 9) // 10


@pytest.fixture()
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        ensure_role_defaults(db)
        seed_demo_content(db)

    def override_get_blog_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_blog_db] = override_get_blog_db
    rate_limit_buckets.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    rate_limit_buckets.clear()


def admin_headers() -> dict[str, str]:
    payload = {
        "sub": "admin",
        "user_id": 1,
        "role": Role.ADMIN.value,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def login(client, username="admin", password="admin123", next_url="/"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": next_url},
        follow_redirects=False,
    )


def test_homepage_lists_published_posts_and_hides_drafts(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Latest posts" in response.text
    assert "A release checklist for small teams" in response.text
    assert f"of {PUBLISHED_SEED_COUNT} published posts" in response.text
    assert f"Page 1 of {SEED_TOTAL_PAGES}" in response.text
    assert "Draft workflow notes" not in response.text


def test_post_detail_renders_published_post_and_hides_anonymous_draft(client):
    published = client.get("/posts/1")
    assert published.status_code == 200
    assert "Welcome to the API demo" in published.text
    assert "This published article is seeded as demo content." in published.text

    draft = client.get("/posts/2")
    assert draft.status_code == 404
    assert "Page not found" in draft.text


def test_login_page_renders_demo_accounts(client, monkeypatch):
    monkeypatch.setattr(settings, "BLOG_SEED_DEMO", True)

    response = client.get("/login")

    assert response.status_code == 200
    assert "Demo accounts" in response.text
    assert "admin123" in response.text


def test_login_sets_httponly_cookie_and_unlocks_drafts(client):
    response = login(client)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    cookie = response.headers["set-cookie"]
    assert "access_token=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie

    homepage = client.get("/")
    assert "admin" in homepage.text
    assert "Log out" in homepage.text

    draft = client.get("/posts/2")
    assert draft.status_code == 200
    assert "Draft workflow notes" in draft.text
    assert "This draft is only visible" in draft.text


def test_login_rejects_bad_credentials(client):
    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert "Invalid username or password." in response.text
    assert "set-cookie" not in response.headers

    unknown = login(client, username="ghost")
    assert unknown.status_code == 401


def test_login_ignores_unsafe_next_urls(client):
    unsafe = login(client, next_url="//evil.example/phish")
    assert unsafe.headers["location"] == "/"

    external = login(client, next_url="https://evil.example/phish")
    assert external.headers["location"] == "/"

    safe = login(client, next_url="/posts/1")
    assert safe.headers["location"] == "/posts/1"


def test_logout_clears_cookie_and_restores_anonymous_view(client):
    login(client)
    assert client.get("/posts/2").status_code == 200

    response = client.post("/logout", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert client.cookies.get("access_token") is None
    assert client.get("/posts/2").status_code == 404


def test_invalid_cookie_is_treated_as_anonymous(client):
    client.cookies.set("access_token", "garbage")

    homepage = client.get("/")
    assert homepage.status_code == 200
    assert "Log in" in homepage.text
    assert client.get("/posts/2").status_code == 404


def test_pagination_splits_published_posts(client):
    for index in range(11):
        response = client.post(
            "/api/v1/posts",
            json={
                "title": f"Bulk post {index}",
                "body": "Bulk body",
                "status": "published",
            },
            headers=admin_headers(),
        )
        assert response.status_code == 201

    total = PUBLISHED_SEED_COUNT + 11
    total_pages = (total + 9) // 10

    first = client.get("/", params={"per_page": 10})
    assert first.status_code == 200
    assert "Bulk post 10" in first.text
    assert "Bulk post 0" not in first.text
    assert f"Page 1 of {total_pages}" in first.text
    assert "Next" in first.text

    last = client.get("/", params={"per_page": 10, "page": total_pages})
    assert last.status_code == 200
    assert "Welcome to the API demo" in last.text
    assert f"Page {total_pages} of {total_pages}" in last.text


def test_login_api_returns_usable_token(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    created = client.post(
        "/api/v1/posts",
        json={"title": "From login token", "body": "Body", "status": "draft"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert created.status_code == 201

    bad = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "nope"},
    )
    assert bad.status_code == 401

    invalid = client.post("/api/v1/auth/login", json={"username": "admin"})
    assert invalid.status_code == 400


def test_unknown_page_returns_html_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Page not found" in response.text


def test_static_css_is_served(client):
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
