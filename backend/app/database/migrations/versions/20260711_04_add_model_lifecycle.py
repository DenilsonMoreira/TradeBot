"""Add trained model lifecycle.

Revision ID: 20260711_04
Revises: 20260710_03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260711_04"
down_revision = "20260710_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trained_models", sa.Column("status", sa.String(16), server_default="CANDIDATE", nullable=False))
    op.add_column("trained_models", sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("trained_models", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_trained_models_status", "trained_models", "status IN ('CANDIDATE', 'ACTIVE', 'INACTIVE')")
    op.create_index(
        "uq_trained_models_one_active_per_dataset",
        "trained_models",
        ["dataset_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_trained_models_one_active_per_dataset", table_name="trained_models")
    op.drop_constraint("ck_trained_models_status", "trained_models", type_="check")
    op.drop_column("trained_models", "deactivated_at")
    op.drop_column("trained_models", "promoted_at")
    op.drop_column("trained_models", "status")
