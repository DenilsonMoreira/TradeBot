"""Create candles table.

Revision ID: 20260710_01
Revises:
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(30, 12), nullable=False),
        sa.Column("high", sa.Numeric(30, 12), nullable=False),
        sa.Column("low", sa.Numeric(30, 12), nullable=False),
        sa.Column("close", sa.Numeric(30, 12), nullable=False),
        sa.Column("volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("quote_volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("trades", sa.BigInteger(), nullable=False),
        sa.Column("taker_buy_volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("taker_buy_quote", sa.Numeric(38, 18), nullable=False),
        sa.Column(
            "is_closed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candles"),
        sa.UniqueConstraint(
            "symbol",
            "interval",
            "open_time",
            name="uq_candles_symbol_interval_open_time",
        ),
    )
    op.create_index(
        "ix_candles_symbol_interval_open_time",
        "candles",
        ["symbol", "interval", "open_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candles_symbol_interval_open_time", table_name="candles"
    )
    op.drop_table("candles")
