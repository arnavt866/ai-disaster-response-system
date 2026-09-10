"""Copernicus EMS satellite assessment polygons.

Revision ID: g9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-09-04 14:20:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

revision: str = "a7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "satellite_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activation_code", sa.String(), nullable=False),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("product_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("classification", sa.String(), nullable=True),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("source_license", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_satellite_assessments_id"),
        "satellite_assessments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satellite_assessments_activation_code"),
        "satellite_assessments",
        ["activation_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satellite_assessments_product_type"),
        "satellite_assessments",
        ["product_type"],
        unique=False,
    )
    op.create_index(
        "ix_satellite_assessments_geometry_gist",
        "satellite_assessments",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_satellite_assessments_geometry_gist",
        table_name="satellite_assessments",
    )
    op.drop_index(
        op.f("ix_satellite_assessments_product_type"),
        table_name="satellite_assessments",
    )
    op.drop_index(
        op.f("ix_satellite_assessments_activation_code"),
        table_name="satellite_assessments",
    )
    op.drop_index(op.f("ix_satellite_assessments_id"), table_name="satellite_assessments")
    op.drop_table("satellite_assessments")
