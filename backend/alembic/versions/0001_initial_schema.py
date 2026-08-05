"""Create VidInsight core schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-05
"""

from alembic import op
from app.database import Base
import app.models  # noqa: F401 - registers metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
