"""Add user preferences columns, timestamps, convert seo_keyword ARRAY→JSONB

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    # ── 1. Convert seo_keyword from ARRAY(VARCHAR) → JSONB ───────────────────
    op.execute(
        "ALTER TABLE user_business "
        "ALTER COLUMN seo_keyword TYPE JSONB "
        "USING to_jsonb(seo_keyword)"
    )
    op.execute(
        "ALTER TABLE user_business "
        "ALTER COLUMN seo_keyword SET DEFAULT '[]'::jsonb"
    )

    # ── 2. New preference columns on user_business ────────────────────────────
    op.add_column("user_business", sa.Column(
        "language", sa.String(), nullable=False, server_default="English",
    ))
    op.add_column("user_business", sa.Column(
        "tone", sa.String(), nullable=False, server_default="Professional",
    ))
    op.add_column("user_business", sa.Column(
        "bill_items", sa.Text(), nullable=False, server_default="",
    ))

    # ── 3. Timestamps ──────────────────────────────────────────────────────────
    op.add_column("user_business", sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    ))
    op.add_column("user_business", sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=True,
    ))
    op.add_column("generated_reviews", sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=True,
    ))

    # ── 4. Rating check constraint ─────────────────────────────────────────────
    op.create_check_constraint(
        "ck_generated_reviews_rating",
        "generated_reviews",
        "rating BETWEEN 1 AND 5",
    )

    # ── 5. Additional indexes ─────────────────────────────────────────────────
    op.create_index("ix_user_business_email", "user_business", ["email"])
    op.create_index("ix_user_business_google_place_id", "user_business", ["google_place_id"])


def downgrade() -> None:
    op.drop_index("ix_user_business_google_place_id", table_name="user_business")
    op.drop_index("ix_user_business_email", table_name="user_business")

    op.drop_constraint("ck_generated_reviews_rating", "generated_reviews", type_="check")

    op.drop_column("generated_reviews", "updated_at")
    op.drop_column("user_business", "updated_at")
    op.drop_column("user_business", "created_at")
    op.drop_column("user_business", "bill_items")
    op.drop_column("user_business", "tone")
    op.drop_column("user_business", "language")

    # Revert JSONB → ARRAY(VARCHAR) — data safe as long as values were strings
    op.execute(
        "ALTER TABLE user_business "
        "ALTER COLUMN seo_keyword TYPE VARCHAR[] "
        "USING ARRAY(SELECT jsonb_array_elements_text(seo_keyword))"
    )
