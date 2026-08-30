"""Add PostGIS location point column to disaster_zones

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-08-30 02:50:00.000000

Additive-only migration:
- Enables PostGIS extension if missing
- Adds nullable location geometry column
- Backfills from existing latitude/longitude (no changes to those columns)
- Adds a GiST spatial index on location
"""
from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.add_column(
        "disaster_zones",
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE disaster_zones
        SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
        """
    )

    op.create_index(
        "ix_disaster_zones_location_gist",
        "disaster_zones",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_disaster_zones_location_gist",
        table_name="disaster_zones",
    )
    op.drop_column("disaster_zones", "location")
