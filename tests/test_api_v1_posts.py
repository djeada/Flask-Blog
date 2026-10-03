import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("BLOG_SEED_DEMO", "False")

from blog_engine.database import Base, get_blog_db
from blog_engine.demo import seed_demo_content
from blog_engine.models import Role
from core.config import settings
from main import app, rate_limit_buckets


@pytest.fixture()
def client(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
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


def token_for(user_id: int, username: str, role: Role) -> str:
    payload = {
        "sub": username,
        "user_id": user_id,
        "role": role.value,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def auth_headers(user_id: int, username: str, role: Role) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user_id, username, role)}"}


def create_payload(status: str = "published") -> dict[str, object]:
    return {
        "title": "Role tested post",
        "body": "Markdown body for the role based API test.",
        "status": status,
    }


def test_get_posts_lists_published_posts_for_anonymous_users(client):
    response = client.get("/api/v1/posts")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=60"
    posts = response.json()
    assert len(posts) == 1
    assert posts[0]["status"] == "published"
    assert "X-RateLimit-Limit" in response.headers


def test_get_post_returns_404_for_missing_or_private_anonymous_post(client):
    assert client.get("/api/v1/posts/999").status_code == 404
    assert client.get("/api/v1/posts/2").status_code == 404


def test_admin_can_create_update_and_delete_any_post(client):
    headers = auth_headers(1, "admin", Role.ADMIN)

    created = client.post("/api/v1/posts", json=create_payload(), headers=headers)
    assert created.status_code == 201
    post_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/posts/{post_id}",
        json={"title": "Admin updated title", "author_id": 2},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Admin updated title"
    assert updated.json()["author_id"] == 2

    deleted = client.delete(f"/api/v1/posts/{post_id}", headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""


def test_editor_has_full_post_crud(client):
    headers = auth_headers(2, "editor", Role.EDITOR)

    created = client.post("/api/v1/posts", json=create_payload(), headers=headers)
    assert created.status_code == 201
    post_id = created.json()["id"]

    assert client.put(
        f"/api/v1/posts/{post_id}",
        json={"status": "draft"},
        headers=headers,
    ).status_code == 200
    assert client.delete(f"/api/v1/posts/{post_id}", headers=headers).status_code == 204


def test_author_can_create_and_update_own_posts_but_cannot_delete(client):
    headers = auth_headers(3, "author", Role.AUTHOR)

    created = client.post("/api/v1/posts", json=create_payload(), headers=headers)
    assert created.status_code == 201
    assert created.json()["author_id"] == 3
    post_id = created.json()["id"]

    own_update = client.put(
        f"/api/v1/posts/{post_id}",
        json={"title": "Author owned update"},
        headers=headers,
    )
    assert own_update.status_code == 200

    other_update = client.put(
        "/api/v1/posts/1",
        json={"title": "Not mine"},
        headers=headers,
    )
    assert other_update.status_code == 403

    delete_response = client.delete(f"/api/v1/posts/{post_id}", headers=headers)
    assert delete_response.status_code == 403


def test_contributor_can_create_drafts_only_and_cannot_update(client):
    headers = auth_headers(4, "contributor", Role.CONTRIBUTOR)

    published = client.post("/api/v1/posts", json=create_payload("published"), headers=headers)
    assert published.status_code == 403

    draft = client.post("/api/v1/posts", json=create_payload("draft"), headers=headers)
    assert draft.status_code == 201

    update_response = client.put(
        f"/api/v1/posts/{draft.json()['id']}",
        json={"title": "No update permission"},
        headers=headers,
    )
    assert update_response.status_code == 403


def test_subscriber_and_anonymous_users_cannot_write(client):
    subscriber_headers = auth_headers(5, "subscriber", Role.SUBSCRIBER)

    assert client.post("/api/v1/posts", json=create_payload(), headers=subscriber_headers).status_code == 403
    assert client.post("/api/v1/posts", json=create_payload()).status_code == 401
    assert client.put("/api/v1/posts/1", json={"title": "Nope"}).status_code == 401
    assert client.delete("/api/v1/posts/1").status_code == 401


def test_validation_errors_return_400(client):
    headers = auth_headers(1, "admin", Role.ADMIN)

    missing = client.post("/api/v1/posts", json={"title": "Missing body"}, headers=headers)
    assert missing.status_code == 400

    invalid = client.post(
        "/api/v1/posts",
        json={"title": "Invalid status", "body": "Body", "status": "archived"},
        headers=headers,
    )
    assert invalid.status_code == 400


def test_openapi_documents_v1_posts(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/posts" in paths
    assert "/api/v1/posts/{post_id}" in paths


def test_delete_missing_post_returns_404(client):
    response = client.delete("/api/v1/posts/999", headers=auth_headers(1, "admin", Role.ADMIN))

    assert response.status_code == 404


def test_list_posts_supports_pagination(client):
    headers = auth_headers(1, "admin", Role.ADMIN)
    for i in range(3):
        client.post("/api/v1/posts", json={**create_payload(), "title": f"Post {i}"}, headers=headers)

    page = client.get("/api/v1/posts", params={"limit": 2})
    assert [p["title"] for p in page.json()] == ["Post 2", "Post 1"]
    rest = client.get("/api/v1/posts", params={"limit": 2, "offset": 2})
    assert [p["title"] for p in rest.json()] == ["Post 0", "Welcome to the API demo"]
    assert client.get("/api/v1/posts", params={"limit": 0}).status_code == 400


def test_update_with_explicit_null_leaves_field_unchanged(client):
    headers = auth_headers(1, "admin", Role.ADMIN)

    response = client.put("/api/v1/posts/1", json={"title": None, "body": "New body"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Welcome to the API demo"
    assert response.json()["body"] == "New body"


def test_token_without_exp_or_with_unknown_role_is_handled(client):
    no_exp = jwt.encode({"sub": "admin", "user_id": 1}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert client.post(
        "/api/v1/posts", json=create_payload(), headers={"Authorization": f"Bearer {no_exp}"}
    ).status_code == 401

    odd_role = jwt.encode(
        {"sub": "subscriber", "user_id": 5, "role": "Superuser", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = client.post("/api/v1/posts", json=create_payload(), headers={"Authorization": f"Bearer {odd_role}"})
    assert response.status_code == 403


def test_token_role_claim_cannot_escalate_privileges(client):
    headers = auth_headers(5, "subscriber", Role.ADMIN)

    assert client.post("/api/v1/posts", json=create_payload(), headers=headers).status_code == 403


def test_access_token_cookie_is_not_accepted(client):
    client.cookies.set("access_token", token_for(1, "admin", Role.ADMIN))

    assert client.post("/api/v1/posts", json=create_payload()).status_code == 401


def test_rate_limit_is_per_client_across_paths(client, monkeypatch):
    monkeypatch.setattr(settings, "API_RATE_LIMIT_PER_MINUTE", 3)

    codes = [client.get(f"/api/v1/posts/{i}").status_code for i in range(5)]

    assert codes[-1] == 429
    assert codes.count(429) == 2


def test_only_admin_can_list_users_and_change_roles(client):
    admin = auth_headers(1, "admin", Role.ADMIN)

    users = client.get("/api/v1/users", headers=admin)
    assert users.status_code == 200
    assert [u["username"] for u in users.json()][:2] == ["admin", "editor"]

    for uid, name, role in [(2, "editor", Role.EDITOR), (3, "author", Role.AUTHOR), (5, "subscriber", Role.SUBSCRIBER)]:
        headers = auth_headers(uid, name, role)
        assert client.get("/api/v1/users", headers=headers).status_code == 403
        assert client.put("/api/v1/users/5/role", json={"role": "Admin"}, headers=headers).status_code == 403
    assert client.get("/api/v1/users").status_code == 401

    changed = client.put("/api/v1/users/5/role", json={"role": "Author"}, headers=admin)
    assert changed.status_code == 200
    assert changed.json()["role"] == "Author"

    # The new role takes effect immediately, even with an old token.
    sub = auth_headers(5, "subscriber", Role.SUBSCRIBER)
    assert client.post("/api/v1/posts", json=create_payload(), headers=sub).status_code == 201


def test_role_change_errors(client):
    admin = auth_headers(1, "admin", Role.ADMIN)

    assert client.put("/api/v1/users/999/role", json={"role": "Editor"}, headers=admin).status_code == 404
    assert client.put("/api/v1/users/5/role", json={"role": "Root"}, headers=admin).status_code == 400
    demote = client.put("/api/v1/users/1/role", json={"role": "Editor"}, headers=admin)
    assert demote.status_code == 409


def test_drafts_visible_only_to_owner_and_privileged_roles(client):
    assert client.get("/api/v1/posts/2", headers=auth_headers(3, "author", Role.AUTHOR)).status_code == 200
    assert client.get("/api/v1/posts/2", headers=auth_headers(1, "admin", Role.ADMIN)).status_code == 200
    assert client.get("/api/v1/posts/2", headers=auth_headers(5, "subscriber", Role.SUBSCRIBER)).status_code == 404
    draft = client.get("/api/v1/posts/2", headers=auth_headers(3, "author", Role.AUTHOR))
    assert draft.headers["Cache-Control"] == "private, no-store"


def test_invalid_expired_and_unknown_user_tokens_return_401(client):
    expired = jwt.encode(
        {"sub": "admin", "user_id": 1, "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    ghost = token_for(99, "ghost", Role.ADMIN)
    for token in (expired, ghost, "garbage"):
        response = client.post(
            "/api/v1/posts", json=create_payload(), headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"


def test_author_cannot_create_for_or_reassign_to_another_author(client):
    headers = auth_headers(3, "author", Role.AUTHOR)

    assert client.post("/api/v1/posts", json={**create_payload(), "author_id": 1}, headers=headers).status_code == 403
    own = client.post("/api/v1/posts", json=create_payload(), headers=headers).json()["id"]
    assert client.put(f"/api/v1/posts/{own}", json={"author_id": 1}, headers=headers).status_code == 403


def test_openapi_has_examples_and_documents_error_responses(client):
    spec = client.get("/openapi.json").json()
    posts = spec["paths"]["/api/v1/posts"]
    item = spec["paths"]["/api/v1/posts/{post_id}"]

    assert "429" in posts["get"]["responses"]
    assert {"401", "403", "429"} <= set(posts["post"]["responses"])
    assert {"401", "403", "404"} <= set(item["put"]["responses"])
    assert {"401", "403", "404"} <= set(item["delete"]["responses"])
    assert spec["components"]["schemas"]["PostResponse"]["examples"]
    assert spec["components"]["schemas"]["PostCreate"]["examples"]
    assert "/api/v1/users/{user_id}/role" in spec["paths"]
