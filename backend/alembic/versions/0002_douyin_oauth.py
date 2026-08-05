"""Add encrypted Douyin OAuth credentials and state records.

Revision ID: 0002_douyin_oauth
Revises: 0001_initial_schema
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_douyin_oauth"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    account_columns = {column["name"] for column in sa.inspect(bind).get_columns("accounts")}
    for name, column in (
        ("access_token_encrypted", sa.Column("access_token_encrypted", sa.Text(), nullable=True)),
        ("refresh_token_encrypted", sa.Column("refresh_token_encrypted", sa.Text(), nullable=True)),
        ("token_expires_at", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True)),
        ("refresh_token_expires_at", sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True)),
        ("authorized_scopes", sa.Column("authorized_scopes", sa.Text(), nullable=True)),
    ):
        if name not in account_columns:
            op.add_column("accounts", column)
    if "oauth_states" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_oauth_states_account_id", "oauth_states", ["account_id"])
    op.create_index("ix_oauth_states_state_hash", "oauth_states", ["state_hash"])
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_oauth_states_expires_at", table_name="oauth_states")
    op.drop_index("ix_oauth_states_state_hash", table_name="oauth_states")
    op.drop_index("ix_oauth_states_account_id", table_name="oauth_states")
    op.drop_table("oauth_states")
    op.drop_column("accounts", "authorized_scopes")
    op.drop_column("accounts", "refresh_token_expires_at")
    op.drop_column("accounts", "token_expires_at")
    op.drop_column("accounts", "refresh_token_encrypted")
    op.drop_column("accounts", "access_token_encrypted")
