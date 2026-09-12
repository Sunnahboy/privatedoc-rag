"""add_seq_column_to_chat_messages

Revision ID: a2f59cb078b2
Revises: 2e2d42acfa06
Create Date: 2026-09-13 00:53:43.089201

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2f59cb078b2"
down_revision: str | Sequence[str] | None = "2e2d42acfa06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the missing chat_messages_seq sequence and wire it up."""
    # The seq column already exists in the table, but the sequence it
    # references was never created.  Fix that.
    op.execute("CREATE SEQUENCE IF NOT EXISTS chat_messages_seq")

    # Point the column's default at the sequence (idempotent).
    op.execute(
        "ALTER TABLE chat_messages "
        "ALTER COLUMN seq SET DEFAULT nextval('chat_messages_seq')"
    )

    # Backfill any existing rows that have a NULL seq.
    op.execute(
        "UPDATE chat_messages SET seq = nextval('chat_messages_seq') WHERE seq IS NULL"
    )


def downgrade() -> None:
    """Remove the sequence default and drop the sequence."""
    op.execute("ALTER TABLE chat_messages ALTER COLUMN seq DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS chat_messages_seq")
