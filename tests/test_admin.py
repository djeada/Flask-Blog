import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine.database import Base, get_blog_db
from blog_engine.demo import seed_demo_content
from blog_engine.repository import ensure_role_defaults
from main import app, rate_limit_buckets


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


def login(client, username="admin", password="admin123"):
    client.get("/login")
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/admin",
            "csrf_token": client.cookies["csrf_token"],
        },
        follow_redirects=False,
    )


def csrf(client) -> str:
    return client.cookies["csrf_token"]


def form(client, **overrides) -> dict:
    data = {"csrf_token": csrf(client)}
    data.update(overrides)
    return data


def post_id_of(client, title: str) -> int:
    listing = client.get("/admin/posts", params={"q": title})
    match = re.search(rf"/admin/posts/(\d+)/edit[^>]*>{re.escape(title)}", listing.text)
    if not match:
        match = re.search(rf'/posts/(\d+)">{re.escape(title)}', listing.text)
    if not match:
        match = re.search(r"/admin/posts/(\d+)/edit", listing.text)
    assert match, f"Post {title!r} not found in admin listing"
    return int(match.group(1))


def test_anonymous_admin_routes_redirect_to_login(client):
    for path in ["/admin", "/admin/posts", "/admin/posts/new", "/admin/posts/1/edit", "/admin/users"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 303, path
        assert response.headers["location"].startswith("/login"), path

    response = client.post(
        "/admin/posts",
        data={"title": "Bypass", "body": "Body"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_admin_dashboard_shows_published_and_drafts(client):
    login(client)

    response = client.get("/admin")

    assert response.status_code == 200
    assert "A release checklist for small teams" in response.text
    assert "Notes from the editor rewrite" in response.text
    assert "New post" in response.text


def test_full_publishing_journey(client):
    login(client)

    created = client.post(
        "/admin/posts",
        data=form(client, title="Journey post", body="First draft body", status="draft"),
        follow_redirects=False,
    )
    assert created.status_code == 303

    homepage = client.get("/")
    assert "Journey post" not in homepage.text

    post_id = post_id_of(client, "Journey post")

    published = client.post(
        f"/admin/posts/{post_id}",
        data=form(client, title="Journey post", body="First draft body", status="published"),
        follow_redirects=False,
    )
    assert published.status_code == 303

    homepage = client.get("/")
    assert "Journey post" in homepage.text
    assert client.get(f"/posts/{post_id}").status_code == 200

    deleted = client.post(
        f"/admin/posts/{post_id}/delete",
        data=form(client),
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert client.get(f"/posts/{post_id}").status_code == 404


def test_admin_post_list_search_and_status_filter(client):
    login(client)

    search = client.get("/admin/posts", params={"q": "Pagination"})
    assert search.status_code == 200
    assert "Pagination patterns that scale" in search.text
    assert "Welcome to the API demo" not in search.text

    drafts = client.get("/admin/posts", params={"status": "draft"})
    assert drafts.status_code == 200
    assert "Draft workflow notes" in drafts.text
    assert "Welcome to the API demo" not in drafts.text


def test_admin_mutations_require_csrf(client):
    login(client)

    response = client.post(
        "/admin/posts",
        data={"title": "No csrf post", "body": "Body"},
        follow_redirects=False,
    )

    assert response.status_code == 403
    listing = client.get("/admin/posts", params={"q": "No csrf post"})
    assert ">No csrf post</a>" not in listing.text


def test_contributor_can_draft_but_not_publish(client):
    login(client, username="contributor", password="contributor123")

    new_form = client.get("/admin/posts/new")
    assert new_form.status_code == 200
    assert '<option value="published"' not in new_form.text

    created = client.post(
        "/admin/posts",
        data=form(client, title="Contributor draft", body="Draft body", status="draft"),
        follow_redirects=False,
    )
    assert created.status_code == 303

    post_id = post_id_of(client, "Contributor draft")
    assert client.get(f"/api/v1/posts/{post_id}").status_code == 404

    denied = client.post(
        "/admin/posts",
        data=form(client, title="Contributor sneak", body="Body", status="published"),
        follow_redirects=False,
    )
    assert denied.status_code == 403
    assert "cannot publish" in denied.text


def test_author_edits_own_post_but_not_others(client):
    login(client, username="author", password="author123")

    own = client.get("/admin/posts/2/edit")
    assert own.status_code == 200
    assert "Draft workflow notes" in own.text

    others = client.get("/admin/posts/1/edit")
    assert others.status_code == 403
    assert "cannot edit" in others.text

    bypass = client.post(
        "/admin/posts/1",
        data=form(client, title="Hijacked", body="Body", status="published"),
        follow_redirects=False,
    )
    assert bypass.status_code == 403
    assert client.get("/posts/1").status_code == 200
    assert "Hijacked" not in client.get("/posts/1").text


def test_author_can_publish_own_draft(client):
    login(client, username="author", password="author123")

    published = client.post(
        "/admin/posts/2",
        data=form(client, title="Draft workflow notes", body="Now public", status="published"),
        follow_redirects=False,
    )
    assert published.status_code == 303

    detail = client.get("/posts/2")
    assert detail.status_code == 200
    assert 'class="status-badge draft"' not in detail.text
    assert "Now public" in detail.text


def test_subscriber_cannot_write(client):
    login(client, username="subscriber", password="subscriber123")

    new_form = client.get("/admin/posts/new")
    assert new_form.status_code == 403

    denied = client.post(
        "/admin/posts",
        data=form(client, title="Subscriber post", body="Body", status="draft"),
        follow_redirects=False,
    )
    assert denied.status_code == 403


def test_subscriber_sees_only_published_in_admin(client):
    login(client, username="subscriber", password="subscriber123")

    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    assert "A release checklist for small teams" in dashboard.text
    assert "Notes from the editor rewrite" not in dashboard.text

    listing = client.get("/admin/posts")
    assert listing.status_code == 200
    assert "Draft workflow notes" not in listing.text


def test_users_overview_is_admin_only(client):
    login(client)
    overview = client.get("/admin/users")
    assert overview.status_code == 200
    assert "admin" in overview.text
    assert "Admin" in overview.text

    login(client, username="editor", password="editor123")
    denied = client.get("/admin/users")
    assert denied.status_code == 403
    assert "Only Admins" in denied.text


def test_create_validates_input(client):
    login(client)

    response = client.post(
        "/admin/posts",
        data=form(client, title="   ", body="", status="draft"),
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert "Title is required." in response.text
    assert "Body is required." in response.text


def test_editor_can_edit_any_post(client):
    login(client, username="editor", password="editor123")

    edit = client.get("/admin/posts/2/edit")
    assert edit.status_code == 200

    response = client.post(
        "/admin/posts/2",
        data=form(client, title="Editor rewrite", body="Updated", status="draft"),
        follow_redirects=False,
    )
    assert response.status_code == 303

    draft = client.get("/posts/2")
    assert draft.status_code == 200
    assert "Editor rewrite" in draft.text
