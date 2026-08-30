"""Add inventory tracking quantity constraint

Revision ID: c8d9e0f1a2b3
Revises: b2c3d4e5f6a7
Create Date: 2026-08-29 16:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    violations = conn.execute(
        sa.text(
            "SELECT id, quantity, reserved_quantity, in_transit_quantity "
            "FROM resource_inventory "
            "WHERE reserved_quantity + in_transit_quantity > quantity"
        )
    ).fetchall()
    if violations:
        details = [
            {
                "id": row[0],
                "quantity": row[1],
                "reserved_quantity": row[2],
                "in_transit_quantity": row[3],
            }
            for row in violations
        ]
        raise RuntimeError(
            "Cannot add ck_resource_inventory_tracking_lte_quantity: "
            f"{len(violations)} row(s) violate reserved_quantity + in_transit_quantity <= quantity. "
            f"Violations: {details}"
        )

    op.create_check_constraint(
        "ck_resource_inventory_tracking_lte_quantity",
        "resource_inventory",
        "reserved_quantity + in_transit_quantity <= quantity",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_resource_inventory_tracking_lte_quantity",
        "resource_inventory",
        type_="check",
    )
