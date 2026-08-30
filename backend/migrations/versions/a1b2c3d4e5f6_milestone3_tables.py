"""Milestone 3 tables and zone priority column

Revision ID: a1b2c3d4e5f6
Revises: 34f54a4b285c
Create Date: 2026-08-21 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "34f54a4b285c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "disaster_zones",
        sa.Column(
            "operational_priority",
            sa.String(),
            nullable=False,
            server_default="Moderate",
        ),
    )

    op.create_table(
        "field_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("vehicle_type", sa.String(), nullable=True),
        sa.Column("vehicle_capacity", sa.Integer(), nullable=False),
        sa.Column("contact_number", sa.String(), nullable=True),
        sa.Column("base_latitude", sa.Float(), nullable=True),
        sa.Column("base_longitude", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_field_teams_id"), "field_teams", ["id"], unique=False)

    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_code", sa.String(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("field_team_id", sa.Integer(), nullable=True),
        sa.Column("relief_center_id", sa.Integer(), nullable=True),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("route_distance_km", sa.Float(), nullable=True),
        sa.Column("route_eta_hours", sa.Float(), nullable=True),
        sa.Column("route_status", sa.String(), nullable=False),
        sa.Column("resources_payload", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["field_team_id"], ["field_teams.id"]),
        sa.ForeignKeyConstraint(["relief_center_id"], ["relief_centers.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["disaster_zones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_code"),
    )
    op.create_index(op.f("ix_missions_id"), "missions", ["id"], unique=False)
    op.create_index(op.f("ix_missions_mission_code"), "missions", ["mission_code"], unique=True)
    op.create_index(op.f("ix_missions_zone_id"), "missions", ["zone_id"], unique=False)

    op.create_table(
        "allocation_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.Column("relief_center_id", sa.Integer(), nullable=False),
        sa.Column("resource_category", sa.String(), nullable=False),
        sa.Column("demanded", sa.Float(), nullable=False),
        sa.Column("allocated", sa.Float(), nullable=False),
        sa.Column("unmet", sa.Float(), nullable=False),
        sa.Column("priority_weight", sa.Float(), nullable=False),
        sa.Column("optimization_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["relief_center_id"], ["relief_centers.id"]),
        sa.ForeignKeyConstraint(["zone_id"], ["disaster_zones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_allocation_records_id"), "allocation_records", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_allocation_records_run_id"),
        "allocation_records",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_allocation_records_zone_id"),
        "allocation_records",
        ["zone_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_allocation_records_zone_id"), table_name="allocation_records")
    op.drop_index(op.f("ix_allocation_records_run_id"), table_name="allocation_records")
    op.drop_index(op.f("ix_allocation_records_id"), table_name="allocation_records")
    op.drop_table("allocation_records")
    op.drop_index(op.f("ix_missions_zone_id"), table_name="missions")
    op.drop_index(op.f("ix_missions_mission_code"), table_name="missions")
    op.drop_index(op.f("ix_missions_id"), table_name="missions")
    op.drop_table("missions")
    op.drop_index(op.f("ix_field_teams_id"), table_name="field_teams")
    op.drop_table("field_teams")
    op.drop_column("disaster_zones", "operational_priority")
