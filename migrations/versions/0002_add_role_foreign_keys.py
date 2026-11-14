"""add role foreign keys

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("role_capabilities") as batch_op:
        batch_op.create_foreign_key(
            "fk_role_capabilities_role_role_profiles",
            "role_profiles",
            ["role"],
            ["role"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("blog_users") as batch_op:
        batch_op.create_foreign_key(
            "fk_blog_users_role_role_profiles",
            "role_profiles",
            ["role"],
            ["role"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("blog_users") as batch_op:
        batch_op.drop_constraint(
            "fk_blog_users_role_role_profiles",
            type_="foreignkey",
        )

    with op.batch_alter_table("role_capabilities") as batch_op:
        batch_op.drop_constraint(
            "fk_role_capabilities_role_role_profiles",
            type_="foreignkey",
        )
