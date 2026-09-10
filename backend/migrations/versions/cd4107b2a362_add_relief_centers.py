"""Empty revision (no schema change)

Superseded duplicate of ``629232e69636`` "Add relief centers": an autogenerate
run that produced no operations because ``relief_centers`` already existed. Kept
as a no-op so databases already stamped at this revision keep a valid chain.

Revision ID: cd4107b2a362
Revises: 629232e69636
Create Date: 2026-07-30 19:00:04.316222

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'cd4107b2a362'
down_revision: Union[str, Sequence[str], None] = '629232e69636'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op."""
    pass


def downgrade() -> None:
    """No-op."""
    pass
