"""add_active_imobilizate_active_circulante_to_financial_data

Revision ID: 574729687650
Revises: 0002
Create Date: 2026-05-11 14:30:13.951007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '574729687650'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('financial_data', sa.Column('active_imobilizate', sa.BigInteger(), nullable=True))
    op.add_column('financial_data', sa.Column('active_circulante', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('financial_data', 'active_circulante')
    op.drop_column('financial_data', 'active_imobilizate')
