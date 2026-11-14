import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from blog_engine.database import Base
from blog_engine.database import engine as app_engine
from blog_engine.models import Role, RoleCapability, RoleProfile
from blog_engine.repository import ensure_role_defaults, update_role_settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(db_path):
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def sqlite_engine(path):
    test_engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(test_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return test_engine


def test_migrations_match_models(tmp_path):
    db_path = tmp_path / "migrated.db"
    command.upgrade(alembic_config(db_path), "head")

    test_engine = sqlite_engine(db_path)
    with test_engine.connect() as connection:
        context = MigrationContext.configure(
            connection, opts={"compare_type": True}
        )
        assert compare_metadata(context, Base.metadata) == []


def test_migrations_add_role_foreign_keys(tmp_path):
    db_path = tmp_path / "migrated.db"
    config = alembic_config(db_path)
    command.upgrade(config, "head")

    connection = sqlite_engine(db_path)
    with connection.connect() as db_connection:
        user_keys = db_connection.exec_driver_sql(
            "PRAGMA foreign_key_list(blog_users)"
        ).fetchall()
        assert any(
            key[2] == "role_profiles" and key[3] == "role" and key[4] == "role"
            for key in user_keys
        )
        capability_keys = db_connection.exec_driver_sql(
            "PRAGMA foreign_key_list(role_capabilities)"
        ).fetchall()
        assert any(
            key[2] == "role_profiles" and key[3] == "role" and key[4] == "role"
            for key in capability_keys
        )
        assert db_connection.exec_driver_sql(
            "PRAGMA foreign_key_check"
        ).fetchall() == []

    with pytest.raises(IntegrityError):
        with connection.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO blog_users (username, role, password_hash) "
                    "VALUES ('ghost', 'ADMIN', NULL)"
                )
            )


def test_upgrade_preserves_existing_data(tmp_path):
    db_path = tmp_path / "legacy.db"
    config = alembic_config(db_path)
    command.upgrade(config, "0001")

    with sqlite_engine(db_path).begin() as connection:
        connection.execute(
            text(
                "INSERT INTO role_profiles (role, description) "
                "VALUES ('ADMIN', 'Administrator')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO role_capabilities (role, capability) "
                "VALUES ('ADMIN', 'users.manage')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO blog_users (id, username, role, password_hash) "
                "VALUES (1, 'ada', 'ADMIN', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO posts (id, title, body, status, author_id) "
                "VALUES (1, 'Hello', 'Body', 'PUBLISHED', 1)"
            )
        )

    command.upgrade(config, "head")

    with sqlite_engine(db_path).connect() as connection:
        assert connection.exec_driver_sql(
            "SELECT username FROM blog_users"
        ).fetchall() == [("ada",)]
        assert connection.exec_driver_sql(
            "SELECT author_id FROM posts"
        ).fetchall() == [(1,)]
        assert connection.exec_driver_sql(
            "SELECT capability FROM role_capabilities"
        ).fetchall() == [("users.manage",)]
        indexes = {
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA index_list(blog_users)"
            ).fetchall()
        }
        assert "ix_blog_users_id" in indexes
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


def test_migrations_can_be_downgraded_and_reapplied(tmp_path):
    db_path = tmp_path / "reversible.db"
    config = alembic_config(db_path)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    with sqlite_engine(db_path).connect() as connection:
        tables = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "blog_users" not in tables
        assert "posts" not in tables
        assert "role_profiles" not in tables
        assert "role_capabilities" not in tables

    command.upgrade(config, "head")


def test_role_defaults_seed_with_foreign_keys_enforced(tmp_path):
    test_engine = sqlite_engine(tmp_path / "seed.db")
    Base.metadata.create_all(test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    with TestingSessionLocal() as db:
        ensure_role_defaults(db)
        assert len(list(db.query(RoleProfile))) == len(Role)
        assert db.query(RoleCapability).count() > 0

        update_role_settings(
            db,
            Role.CONTRIBUTOR,
            "Writes and edits their own drafts.",
            ["posts.read_published", "posts.create_draft"],
        )
        capabilities = {
            row.capability
            for row in db.query(RoleCapability).filter(RoleCapability.role == Role.CONTRIBUTOR)
        }
        assert capabilities == {"posts.read_published", "posts.create_draft"}


def test_app_engine_enables_sqlite_foreign_keys():
    with app_engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
