"""Add index on generated_reviews.user_id

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-05
"""
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_generated_reviews_user_id", "generated_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_generated_reviews_user_id", table_name="generated_reviews")
