"""add creator collector source events

Revision ID: 0003_source_events
Revises: 0002_douyin_oauth
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_source_events"
down_revision = "0002_douyin_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "source_events" in inspector.get_table_names():
        return
    op.create_table(
        "source_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("parse_status", sa.String(length=30), nullable=False, server_default="received"),
        sa.Column("parse_details", sa.JSON(), nullable=False),
    )
    op.create_index("ix_source_events_workspace_id", "source_events", ["workspace_id"])
    op.create_index("ix_source_events_account_id", "source_events", ["account_id"])
    op.create_index("ix_source_events_captured_at", "source_events", ["captured_at"])


def downgrade() -> None:
    op.drop_table("source_events")
