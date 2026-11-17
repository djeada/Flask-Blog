import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine.bootstrap import ensure_initial_admin  # noqa: E402
from blog_engine.database import Base  # noqa: E402
from blog_engine.repository import ensure_role_defaults, get_user_by_username  # noqa: E402


def make_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_initial_admin_is_created_when_no_admin_exists(tmp_path):
    db = make_db(tmp_path)
    ensure_role_defaults(db)

    assert ensure_initial_admin(db, "root", "first-admin-password") is True

    user = get_user_by_username(db, "root")
    assert user is not None
    assert user.role.value == "Admin"


def test_existing_admin_prevents_second_bootstrap(tmp_path):
    db = make_db(tmp_path)
    ensure_role_defaults(db)
    ensure_initial_admin(db, "root", "first-admin-password")

    assert ensure_initial_admin(db, "other", "second-admin-password") is False
    assert get_user_by_username(db, "other") is None


def test_existing_username_is_left_unchanged(tmp_path):
    db = make_db(tmp_path)
    ensure_role_defaults(db)
    ensure_initial_admin(db, "root", "first-admin-password")

    assert ensure_initial_admin(db, "root", "another-password") is False


def test_blank_credentials_do_nothing(tmp_path):
    db = make_db(tmp_path)
    ensure_role_defaults(db)

    assert ensure_initial_admin(db, "", "") is False
    assert ensure_initial_admin(db, "root", "") is False
    assert get_user_by_username(db, "root") is None
