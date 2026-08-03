"""Add QR scan reminder tracking columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_business",
        sa.Column(
            "qr_tracking_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "user_business",
        sa.Column("last_qr_scan_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_business",
        sa.Column("last_qr_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Existing businesses begin the 7-day reminder clock from the migration time.
    op.execute(
        "UPDATE user_business "
        "SET qr_tracking_started_at = now() "
        "WHERE qr_tracking_started_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("user_business", "last_qr_reminder_sent_at")
    op.drop_column("user_business", "last_qr_scan_at")
    op.drop_column("user_business", "qr_tracking_started_at")
