"""Create persistent research evaluation history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260715_08"
down_revision = "20260712_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_evaluation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("interval", sa.String(length=10), nullable=False),
        sa.Column("dataset_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("new_candles", sa.Integer(), nullable=False),
        sa.Column("required_candles", sa.Integer(), nullable=False),
        sa.Column("models_trained", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recommended_algorithm", sa.String(length=64), nullable=True),
        sa.Column("activated_algorithm", sa.String(length=64), nullable=True),
        sa.Column("metrics_summary", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED', 'SKIPPED')",
            name="ck_research_evaluation_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_research_evaluation_runs_dataset_id_datasets",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_evaluation_runs"),
    )
    op.create_index(
        "ix_research_evaluation_runs_symbol",
        "research_evaluation_runs",
        ["symbol"],
    )
    op.create_index(
        "ix_research_evaluation_runs_status",
        "research_evaluation_runs",
        ["status"],
    )
    op.create_index(
        "ix_research_evaluation_runs_started_at",
        "research_evaluation_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_evaluation_runs_started_at", table_name="research_evaluation_runs")
    op.drop_index("ix_research_evaluation_runs_status", table_name="research_evaluation_runs")
    op.drop_index("ix_research_evaluation_runs_symbol", table_name="research_evaluation_runs")
    op.drop_table("research_evaluation_runs")
