"""Use exact numeric types for soak campaign financial values."""

from alembic import op
import sqlalchemy as sa


revision = "20260715_10"
down_revision = "20260715_09"
branch_labels = None
depends_on = None


FINANCIAL_COLUMNS = (
    "budget_brl",
    "reference_brl_per_usdt",
    "budget_quote",
    "max_quote_per_trade",
    "max_loss_quote",
)


def upgrade() -> None:
    for column in FINANCIAL_COLUMNS:
        op.alter_column(
            "testnet_soak_campaigns",
            column,
            existing_type=sa.Float(),
            type_=sa.Numeric(20, 8),
            existing_nullable=False,
            postgresql_using=f"{column}::numeric(20, 8)",
        )


def downgrade() -> None:
    for column in reversed(FINANCIAL_COLUMNS):
        op.alter_column(
            "testnet_soak_campaigns",
            column,
            existing_type=sa.Numeric(20, 8),
            type_=sa.Float(),
            existing_nullable=False,
            postgresql_using=f"{column}::double precision",
        )

