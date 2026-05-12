"""Initial schema: user_business and generated_reviews tables

Revision ID: 0001
Revises:
Create Date: 2026-04-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_business",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=False),
        sa.Column("business_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("seo_keyword", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("mobile_no", sa.String(), nullable=False, server_default=""),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("review_link", sa.String(), nullable=False, server_default=""),
        sa.Column("business_desc", sa.Text(), nullable=False, server_default=""),
        sa.Column("qr_code_url", sa.String(), nullable=True),
        sa.Column("google_id", sa.String(), nullable=True),
        sa.Column("google_place_id", sa.String(), nullable=True),
        sa.Column("auth_provider", sa.String(), nullable=False, server_default="local"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_name"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
    )

    op.create_table(
        "generated_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_business.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("generated_reviews")
    op.drop_table("user_business")
