"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_VALUES = ("ADMIN", "EDITOR", "AUTHOR", "CONTRIBUTOR", "SUBSCRIBER")
POST_STATUS_VALUES = ("DRAFT", "PUBLISHED")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blog_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", sa.Enum(*ROLE_VALUES, name="role"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_blog_users_id", "blog_users", ["id"])

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*POST_STATUS_VALUES, name="poststatus"),
            nullable=False,
        ),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["blog_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_posts_id", "posts", ["id"])

    op.create_table(
        "role_profiles",
        sa.Column("role", sa.Enum(*ROLE_VALUES, name="role"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("role"),
    )

    op.create_table(
        "role_capabilities",
        sa.Column("role", sa.Enum(*ROLE_VALUES, name="role"), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("role", "capability"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("role_capabilities")
    op.drop_table("role_profiles")
    op.drop_index("ix_posts_id", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_blog_users_id", table_name="blog_users")
    op.drop_table("blog_users")
