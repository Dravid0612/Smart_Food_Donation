from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_table(
        'food_donations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.String(length=100), nullable=False),
        sa.Column('preparation_time', sa.String(length=100), nullable=False),
        sa.Column('expiry_time', sa.String(length=100), nullable=False),
        sa.Column('pickup_address', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('donor_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')), 
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_food_donations_id'), 'food_donations', ['id'], unique=False)

    op.create_table(
        'ngos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('contact_person', sa.String(length=255), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ngos_email'), 'ngos', ['email'], unique=True)
    op.create_index(op.f('ix_ngos_id'), 'ngos', ['id'], unique=False)

    op.create_table(
        'donation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('donation_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('performed_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_donation_history_id'), 'donation_history', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('donation_history')
    op.drop_table('ngos')
    op.drop_table('food_donations')
    op.drop_table('users')
