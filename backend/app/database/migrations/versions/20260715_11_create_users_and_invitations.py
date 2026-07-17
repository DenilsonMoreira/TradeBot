"""Create invited users and one-time invitations."""

from alembic import op
import sqlalchemy as sa


revision = "20260715_11"
down_revision = "20260715_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("telegram_chat_id", sa.String(64), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("document_type", sa.String(16), nullable=False),
        sa.Column("document_fingerprint", sa.String(64), nullable=False),
        sa.Column("document_last4", sa.String(4), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(24), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("terms_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("document_fingerprint"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_telegram_chat_id", "users", ["telegram_chat_id"])
    op.create_index("ix_users_document_fingerprint", "users", ["document_fingerprint"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "user_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invited_by", sa.String(320), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("destination", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("delivery_status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("delivery_error", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_invitations_invited_by", "user_invitations", ["invited_by"])
    op.create_index("ix_user_invitations_destination", "user_invitations", ["destination"])
    op.create_index("ix_user_invitations_token_hash", "user_invitations", ["token_hash"])
    op.create_index("ix_user_invitations_status", "user_invitations", ["status"])
    op.create_index("ix_user_invitations_expires_at", "user_invitations", ["expires_at"])


def downgrade() -> None:
    op.drop_table("user_invitations")
    op.drop_table("users")
