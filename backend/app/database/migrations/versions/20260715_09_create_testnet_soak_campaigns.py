"""Create continuous Testnet soak campaigns."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260715_09"
down_revision = "20260715_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "testnet_soak_campaigns",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("budget_brl", sa.Float(), nullable=False),
        sa.Column("reference_brl_per_usdt", sa.Float(), nullable=False),
        sa.Column("budget_quote", sa.Float(), nullable=False),
        sa.Column("max_quote_per_trade", sa.Float(), nullable=False),
        sa.Column("max_loss_quote", sa.Float(), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("symbols", postgresql.JSONB(), nullable=False),
        sa.Column("baseline_candle_counts", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'CANCELED', 'FAILED')",
            name="ck_testnet_soak_campaigns_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_testnet_soak_campaigns"),
    )
    op.create_index(
        "uq_testnet_soak_campaigns_one_running",
        "testnet_soak_campaigns",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
    )
    op.create_index("ix_testnet_soak_campaigns_started_at", "testnet_soak_campaigns", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_testnet_soak_campaigns_started_at", table_name="testnet_soak_campaigns")
    op.drop_index("uq_testnet_soak_campaigns_one_running", table_name="testnet_soak_campaigns")
    op.drop_table("testnet_soak_campaigns")

