"""Initial schema

Baseline table that predates the rest of the migration chain.

``disaster_events`` was originally created outside Alembic (via
``Base.metadata.create_all``), so autogenerate produced an empty initial
revision and later revision ``9aa4a3422f50`` emitted ALTER statements against a
table the chain never created. That made ``alembic upgrade head`` fail on any
empty database. The baseline is declared here, in its pre-``9aa4a3422f50``
shape, so ``9aa4a3422f50`` still applies its own column additions and NOT NULL
tightening on top.

Revision ID: 69563a885d0a
Revises:
Create Date: 2026-07-30 11:13:30.024575

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '69563a885d0a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'disaster_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('disaster_type', sa.String(), nullable=True),
        sa.Column('magnitude', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('event_time', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index(
        op.f('ix_disaster_events_id'), 'disaster_events', ['id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_disaster_events_id'), table_name='disaster_events')
    op.drop_table('disaster_events')
