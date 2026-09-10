"""Add commanders table for authentication."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i2j3k4l5m6n7"
down_revision: Union[str, Sequence[str], None] = "h1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commanders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_commanders_id"), "commanders", ["id"], unique=False)
    op.create_index(op.f("ix_commanders_username"), "commanders", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_commanders_username"), table_name="commanders")
    op.drop_index(op.f("ix_commanders_id"), table_name="commanders")
    op.drop_table("commanders")
