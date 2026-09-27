"""003 Rescue Claim Tokens Schema for PostgreSQL and SQLite

Revision ID: 003
Revises: 002
Create Date: 2026-09-27 20:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = set(inspector.get_table_names())

    if 'rescue_claim_tokens' not in existing_tables:
        op.create_table(
            'rescue_claim_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('token', sa.String(128), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('claimed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_rescue_claim_tokens_id', 'rescue_claim_tokens', ['id'], unique=False)
        op.create_index('ix_rescue_claim_tokens_token', 'rescue_claim_tokens', ['token'], unique=True)
        op.create_index('ix_claim_token_active', 'rescue_claim_tokens', ['token', 'is_active'], unique=False)
        op.create_index('ix_claim_donation_active', 'rescue_claim_tokens', ['donation_id', 'is_active'], unique=False)


def downgrade() -> None:
    pass
