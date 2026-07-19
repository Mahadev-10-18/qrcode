"""initial_schema

Revision ID: 6f1a2bfc45ae
Revises:
Create Date: 2026-07-18 20:13:25.872712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '6f1a2bfc45ae'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Only create tables that don't already exist (supports both fresh and existing DBs)
    existing_tables = inspector.get_table_names()

    if "user" not in existing_tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("phone_number", sa.String(), nullable=True),
            sa.Column("hashed_password", sa.String(), nullable=True),
            sa.Column("plan", sa.String(), nullable=False, server_default="free"),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("verification_token", sa.String(), nullable=True),
            sa.Column("reset_token", sa.String(), nullable=True),
            sa.Column("reset_token_expires", sa.DateTime(timezone=False), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_user_email", "user", ["email"], unique=True)
        op.create_index("ix_user_reset_token", "user", ["reset_token"])

    if "tag" not in existing_tables:
        op.create_table(
            "tag",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        )
        op.create_index("ix_tag_owner_id", "tag", ["owner_id"])

    if "contactevent" not in existing_tables:
        op.create_table(
            "contactevent",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("tag_id", sa.Uuid(), nullable=False),
            sa.Column("finder_contact_method", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("relay_session_id", sa.String(), nullable=True),
            sa.Column("message", sa.String(), nullable=True),
            sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("finder_phone", sa.String(), nullable=True),
            sa.Column("owner_phone", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["tag_id"], ["tag.id"]),
        )
        op.create_index("ix_contactevent_finder_contact_method", "contactevent", ["finder_contact_method"])

    if "ratelimitevent" not in existing_tables:
        op.create_table(
            "ratelimitevent",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ratelimitevent_key", "ratelimitevent", ["key"])

    if "auditlog" not in existing_tables:
        op.create_table(
            "auditlog",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("resource_type", sa.String(), nullable=True),
            sa.Column("resource_id", sa.String(), nullable=True),
            sa.Column("detail", sa.String(), nullable=True),
            sa.Column("ip_address", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_auditlog_user_id", "auditlog", ["user_id"])
        op.create_index("ix_auditlog_action", "auditlog", ["action"])

    if "job" not in existing_tables:
        op.create_table(
            "job",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("result", sa.LargeBinary(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("job")
    op.drop_table("auditlog")
    op.drop_table("ratelimitevent")
    op.drop_table("contactevent")
    op.drop_table("tag")
    op.drop_table("user")
