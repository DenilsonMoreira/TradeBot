"""Create indicators table.

Revision ID: 20260710_02
Revises: 20260710_01
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260710_02"
down_revision = "20260710_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "indicators",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("candle_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("config_version", sa.String(length=32), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(38, 18), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candle_id"],
            ["candles.id"],
            name="fk_indicators_candle_id_candles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_indicators"),
        sa.UniqueConstraint(
            "candle_id",
            "name",
            "config_version",
            name="uq_indicators_candle_name_config_version",
        ),
    )
    op.create_index(
        "ix_indicators_name_config_version",
        "indicators",
        ["name", "config_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_indicators_name_config_version", table_name="indicators")
    op.drop_table("indicators")
