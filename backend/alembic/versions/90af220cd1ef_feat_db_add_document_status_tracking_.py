"""feat(db): add document status tracking and chat history schemas

Revision ID: 90af220cd1ef
Revises: fc3a39f65bb7
Create Date: 2026-08-21 00:51:36.933970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '90af220cd1ef'
down_revision: Union[str, Sequence[str], None] = 'fc3a39f65bb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    ingeststatus_enum = postgresql.ENUM('QUEUED', 'PROCESSING_TEXT', 'PROCESSING_VISUAL', 'COMPLETED', 'FAILED', name='ingeststatus')
    ingeststatus_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        """
        ALTER TABLE documents
        ALTER COLUMN status TYPE ingeststatus
        USING (
            CASE status
                WHEN 'pending' THEN 'QUEUED'
                WHEN 'uploaded' THEN 'QUEUED'
                WHEN 'processing' THEN 'PROCESSING_TEXT'
                WHEN 'indexed' THEN 'COMPLETED'
                WHEN 'failed' THEN 'FAILED'
                WHEN 'QUEUED' THEN 'QUEUED'
                WHEN 'PROCESSING_TEXT' THEN 'PROCESSING_TEXT'
                WHEN 'PROCESSING_VISUAL' THEN 'PROCESSING_VISUAL'
                WHEN 'COMPLETED' THEN 'COMPLETED'
                WHEN 'FAILED' THEN 'FAILED'
                ELSE 'QUEUED'
            END
        )::ingeststatus
        """
    )
    op.add_column('documents', sa.Column('error_message', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('metadata_json', sa.JSON(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE documents
        ALTER COLUMN status TYPE VARCHAR(50)
        USING (
            CASE status
                WHEN 'QUEUED' THEN 'pending'
                WHEN 'PROCESSING_TEXT' THEN 'processing'
                WHEN 'PROCESSING_VISUAL' THEN 'processing'
                WHEN 'COMPLETED' THEN 'indexed'
                WHEN 'FAILED' THEN 'failed'
                ELSE 'pending'
            END
        )
        """
    )
    op.drop_column('documents', 'metadata_json')
    op.drop_column('documents', 'error_message')
    ingeststatus_enum = postgresql.ENUM('QUEUED', 'PROCESSING_TEXT', 'PROCESSING_VISUAL', 'COMPLETED', 'FAILED', name='ingeststatus')
    ingeststatus_enum.drop(op.get_bind(), checkfirst=True)
