import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine import policy
from blog_engine.database import Base, get_blog_db
from blog_engine.demo import DEMO_POSTS, seed_demo_content
from blog_engine.models import Post, PostStatus, Role
from blog_engine.repository import ensure_role_defaults
from blog_engine.schemas import Principal
from core.config import DEFAULT_DATABASE_PATH, settings
from main import app, rate_limit_buckets

PUBLISHED_SEED_COUNT = sum(
    1 for post in DEMO_POSTS if post["status"] == PostStatus.PUBLISHED
)


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
    assert len(posts) == PUBLISHED_SEED_COUNT
    assert all(post["status"] == "published" for post in posts)
    assert "Welcome to the API demo" in [post["title"] for post in posts]
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
    rest_titles = [p["title"] for p in rest.json()]
    assert rest_titles[0] == "Post 0"
    assert len(rest_titles) == 2
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


def test_roles_endpoint_lists_descriptions_and_capabilities(client):
    response = client.get("/api/v1/roles")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=300"
    roles = {item["role"]: item for item in response.json()}
    assert list(roles) == ["Admin", "Editor", "Author", "Contributor", "Subscriber"]
    assert all(item["description"] for item in roles.values())
    assert roles["Admin"]["capabilities"] == list(policy.CAPABILITY_ORDER)
    assert "users.manage" not in roles["Editor"]["capabilities"]
    assert "posts.publish" in roles["Author"]["capabilities"]
    assert "posts.publish" not in roles["Contributor"]["capabilities"]
    assert "posts.create_draft" in roles["Contributor"]["capabilities"]
    assert roles["Subscriber"]["capabilities"] == [
        "posts.read_published",
        "posts.read_own_draft",
    ]

    single = client.get("/api/v1/roles/Author")
    assert single.status_code == 200
    assert single.json() == roles["Author"]
    assert client.get("/api/v1/roles/Wizard").status_code == 400


def test_capabilities_endpoint_is_separate_from_roles(client):
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=300"
    capabilities = response.json()
    assert [item["key"] for item in capabilities] == list(policy.CAPABILITY_ORDER)
    assert all(item["label"] and item["description"] for item in capabilities)
    assert all("roles" not in item and "exclusive" not in item for item in capabilities)

    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/roles" in paths
    assert "/api/v1/roles/{role}" in paths
    assert "put" in paths["/api/v1/roles/{role}"]
    assert "/api/v1/capabilities" in paths


def test_policy_behavior_matches_role_capability_assignments(client):
    roles = {item["role"]: item for item in client.get("/api/v1/roles").json()}

    for role in Role:
        assigned = set(roles[role.value]["capabilities"])
        principal = Principal(
            user_id=1,
            username=role.value,
            role=role,
            capabilities=frozenset(assigned),
        )
        own_draft = Post(
            title="Own", body="Body", status=PostStatus.DRAFT, author_id=1
        )
        other_draft = Post(
            title="Other", body="Body", status=PostStatus.DRAFT, author_id=2
        )
        other_published = Post(
            title="Public", body="Body", status=PostStatus.PUBLISHED, author_id=2
        )
        allowed = {
            "posts.read_published": policy.can_read_post(principal, other_published),
            "posts.read_own_draft": policy.can_read_post(principal, own_draft),
            "posts.read_any_draft": policy.can_read_post(principal, other_draft),
            "posts.create_draft": policy.can_create_post(principal, PostStatus.DRAFT),
            "posts.publish": policy.can_create_post(principal, PostStatus.PUBLISHED),
            "posts.update_own": policy.can_update_post(principal, own_draft),
            "posts.update_any": policy.can_update_post(principal, other_draft),
            "posts.assign_author": policy.can_assign_author(principal),
            "posts.delete": policy.can_delete_post(principal, other_draft),
            "users.manage": policy.can_manage_users(principal),
        }
        enforced = {key for key, is_allowed in allowed.items() if is_allowed}
        assert assigned == enforced


def test_admin_can_update_role_and_authorization_changes_immediately(client):
    contributor_headers = auth_headers(4, "contributor", Role.CONTRIBUTOR)
    admin_headers = auth_headers(1, "admin", Role.ADMIN)

    denied = client.post(
        "/api/v1/posts", json=create_payload("published"), headers=contributor_headers
    )
    assert denied.status_code == 403

    updated = client.put(
        "/api/v1/roles/Contributor",
        json={
            "description": "Can publish after an editorial promotion.",
            "capabilities": [
                "posts.read_published",
                "posts.read_own_draft",
                "posts.create_draft",
                "posts.publish",
            ],
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Can publish after an editorial promotion."
    assert "posts.publish" in updated.json()["capabilities"]

    published = client.post(
        "/api/v1/posts", json=create_payload("published"), headers=contributor_headers
    )
    assert published.status_code == 201

    fetched = client.get("/api/v1/roles/Contributor")
    assert fetched.json() == updated.json()


def test_role_update_permissions_validation_and_admin_immutability(client):
    admin_headers = auth_headers(1, "admin", Role.ADMIN)
    payload = {"description": "Nope", "capabilities": ["posts.publish"]}

    assert (
        client.put(
            "/api/v1/roles/Contributor",
            json=payload,
            headers=auth_headers(2, "editor", Role.EDITOR),
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/roles/Contributor",
            json=payload,
            headers=auth_headers(3, "author", Role.AUTHOR),
        ).status_code
        == 403
    )
    assert client.put("/api/v1/roles/Contributor", json=payload).status_code == 401
    assert (
        client.put("/api/v1/roles/Admin", json=payload, headers=admin_headers).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/roles/Contributor",
            json={"capabilities": ["posts.fly"]},
            headers=admin_headers,
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/v1/roles/Contributor",
            json={"description": "   "},
            headers=admin_headers,
        ).status_code
        == 400
    )


def test_description_only_update_preserves_capabilities(client):
    before = client.get("/api/v1/roles/Author").json()

    updated = client.put(
        "/api/v1/roles/Author",
        json={"description": "Writes and manages their own articles."},
        headers=auth_headers(1, "admin", Role.ADMIN),
    )

    assert updated.status_code == 200
    assert updated.json()["description"] == "Writes and manages their own articles."
    assert updated.json()["capabilities"] == before["capabilities"]


def test_default_database_path_is_absolute_and_tests_are_isolated():
    assert DEFAULT_DATABASE_PATH.is_absolute()
    assert DEFAULT_DATABASE_PATH.name == "blog_engine.db"
    assert settings.BLOG_DATABASE_URL == "sqlite://"
