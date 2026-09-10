"""SACHET CAP early-warning alerts.

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-09-04 14:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ndma_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("cap_identifier", sa.String(), nullable=True),
        sa.Column("etag", sa.String(), nullable=True),
        sa.Column("sender", sa.String(), nullable=True),
        sa.Column("sent", sa.DateTime(), nullable=True),
        sa.Column("msg_status", sa.String(), nullable=True),
        sa.Column("msg_type", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("urgency", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("certainty", sa.String(), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("area_description", sa.Text(), nullable=True),
        sa.Column("area_polygon", sa.Text(), nullable=True),
        sa.Column("area_circle", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("effective", sa.DateTime(), nullable=True),
        sa.Column("onset", sa.DateTime(), nullable=True),
        sa.Column("expires", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="Active"),
        sa.Column("source", sa.String(), nullable=False, server_default="NDMA SACHET"),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_index(op.f("ix_ndma_alerts_id"), "ndma_alerts", ["id"], unique=False)
    op.create_index(
        op.f("ix_ndma_alerts_cap_identifier"),
        "ndma_alerts",
        ["cap_identifier"],
        unique=False,
    )
    op.create_index(op.f("ix_ndma_alerts_status"), "ndma_alerts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ndma_alerts_status"), table_name="ndma_alerts")
    op.drop_index(op.f("ix_ndma_alerts_cap_identifier"), table_name="ndma_alerts")
    op.drop_index(op.f("ix_ndma_alerts_id"), table_name="ndma_alerts")
    op.drop_table("ndma_alerts")
