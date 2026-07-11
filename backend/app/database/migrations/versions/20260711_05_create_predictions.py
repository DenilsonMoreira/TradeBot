"""Create versioned predictions table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260711_05"
down_revision = "20260711_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.BigInteger(), nullable=False),
        sa.Column("dataset_id", sa.BigInteger(), nullable=False),
        sa.Column("candle_id", sa.BigInteger(), nullable=False),
        sa.Column("probability", sa.Numeric(20, 18), nullable=False),
        sa.Column("signal", sa.String(16), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["trained_models.id"], name="fk_predictions_model_id_trained_models", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], name="fk_predictions_dataset_id_datasets", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candle_id"], ["candles.id"], name="fk_predictions_candle_id_candles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
        sa.UniqueConstraint("model_id", "candle_id", name="uq_predictions_model_candle"),
    )


def downgrade() -> None:
    op.drop_table("predictions")
