"""Add company_balance_sheets table for MF/ANAF bulk financial data

Revision ID: 0002
Revises:
Create Date: 2026-04-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_balance_sheets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cui", sa.Integer(), nullable=False),
        sa.Column("an_fiscal", sa.SmallInteger(), nullable=False),
        # P&L
        sa.Column("cifra_afaceri", sa.BigInteger(), nullable=True),
        sa.Column("venituri_totale", sa.BigInteger(), nullable=True),
        sa.Column("cheltuieli_totale", sa.BigInteger(), nullable=True),
        sa.Column("profit_brut", sa.BigInteger(), nullable=True),
        sa.Column("pierdere_bruta", sa.BigInteger(), nullable=True),
        sa.Column("profit_net", sa.BigInteger(), nullable=True),
        sa.Column("pierdere_neta", sa.BigInteger(), nullable=True),
        # Balance sheet
        sa.Column("total_active", sa.BigInteger(), nullable=True),
        sa.Column("active_imobilizate", sa.BigInteger(), nullable=True),
        sa.Column("active_circulante", sa.BigInteger(), nullable=True),
        sa.Column("capitaluri_proprii", sa.BigInteger(), nullable=True),
        sa.Column("datorii_totale", sa.BigInteger(), nullable=True),
        sa.Column("datorii_termen_lung", sa.BigInteger(), nullable=True),
        # Headcount
        sa.Column("nr_salariati", sa.Integer(), nullable=True),
        # Metadata
        sa.Column("sursa", sa.String(length=20), nullable=False, server_default="MF_BULK"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cui", "an_fiscal", name="uq_balance_sheet_cui_year"),
    )
    op.create_index("idx_balance_sheets_cui", "company_balance_sheets", ["cui"])
    op.create_index("idx_balance_sheets_year", "company_balance_sheets", ["an_fiscal"])


def downgrade() -> None:
    op.drop_index("idx_balance_sheets_year", table_name="company_balance_sheets")
    op.drop_index("idx_balance_sheets_cui", table_name="company_balance_sheets")
    op.drop_table("company_balance_sheets")
