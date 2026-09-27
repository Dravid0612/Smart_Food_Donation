"""002 Production Schema for PostgreSQL and SQLite

Revision ID: 002
Revises: 001
Create Date: 2026-09-25 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. users
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('email', sa.String(255), nullable=False),
            sa.Column('password_hash', sa.String(255), nullable=False),
            sa.Column('role', sa.String(50), nullable=False),
            sa.Column('phone', sa.String(50), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('preferred_language', sa.String(10), default='en'),
            sa.Column('is_verified', sa.Boolean(), default=False),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('is_available', sa.Boolean(), default=True),
            sa.Column('reward_points', sa.Integer(), default=0),
            sa.Column('reliability_score', sa.Float(), default=100.0),
            sa.Column('donor_trust_score', sa.Float(), default=98.0),
            sa.Column('completed_deliveries', sa.Integer(), default=0),
            sa.Column('failed_deliveries', sa.Integer(), default=0),
            sa.Column('vehicle_type', sa.String(50), nullable=True),
            sa.Column('max_carry_kg', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_users_email', 'users', ['email'], unique=True)
        op.create_index('ix_users_id', 'users', ['id'], unique=False)

    # 2. ngos
    if 'ngos' not in existing_tables:
        op.create_table(
            'ngos',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('organization_name', sa.String(255), nullable=False),
            sa.Column('registration_number', sa.String(100), nullable=True),
            sa.Column('contact_person', sa.String(100), nullable=True),
            sa.Column('phone', sa.String(50), nullable=True),
            sa.Column('address', sa.Text(), nullable=False),
            sa.Column('latitude', sa.Float(), nullable=False),
            sa.Column('longitude', sa.Float(), nullable=False),
            sa.Column('capacity_kg', sa.Float(), default=100.0),
            sa.Column('is_verified', sa.Boolean(), default=False),
            sa.Column('is_available', sa.Boolean(), default=True),
            sa.Column('trust_score', sa.Float(), default=95.0),
            sa.Column('total_distributed_meals', sa.Float(), default=0.0),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_ngos_id', 'ngos', ['id'], unique=False)

    # 3. food_donations
    if 'food_donations' not in existing_tables:
        op.create_table(
            'food_donations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('assigned_ngo_id', sa.Integer(), sa.ForeignKey('ngos.id'), nullable=True),
            sa.Column('assigned_volunteer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('food_name', sa.String(255), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('quantity_unit', sa.String(20), default='meals'),
            sa.Column('food_category', sa.String(50), default='cooked_meals'),
            sa.Column('pickup_address', sa.Text(), nullable=False),
            sa.Column('latitude', sa.Float(), nullable=False),
            sa.Column('longitude', sa.Float(), nullable=False),
            sa.Column('preparation_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expiry_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('status', sa.String(50), default='pending'),
            sa.Column('is_emergency', sa.Boolean(), default=False),
            sa.Column('current_alert_wave', sa.Integer(), default=0),
            sa.Column('tracking_status', sa.String(50), default='IDLE'),
            sa.Column('verification_otp', sa.String(20), nullable=True),
            sa.Column('otp_expiry', sa.DateTime(timezone=True), nullable=True),
            sa.Column('otp_used_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_food_donations_id', 'food_donations', ['id'], unique=False)
        op.create_index('ix_food_donations_status', 'food_donations', ['status'], unique=False)

    # 4. notifications
    if 'notifications' not in existing_tables:
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('type', sa.String(50), default='info'),
            sa.Column('event_type', sa.String(100), nullable=True),
            sa.Column('related_donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=True),
            sa.Column('deep_link_data', sa.Text(), nullable=True),
            sa.Column('dedup_key', sa.String(255), nullable=True),
            sa.Column('is_read', sa.Boolean(), default=False),
            sa.Column('is_sent', sa.Boolean(), default=False),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_notifications_id', 'notifications', ['id'], unique=False)
        op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
        op.create_index('ix_notifications_dedup_key', 'notifications', ['dedup_key'], unique=False)

    # 5. notification_preferences
    if 'notification_preferences' not in existing_tables:
        op.create_table(
            'notification_preferences',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), unique=True, nullable=False),
            sa.Column('operational_notifications', sa.Boolean(), default=True),
            sa.Column('urgent_rescue_alerts', sa.Boolean(), default=True),
            sa.Column('impact_updates', sa.Boolean(), default=True),
            sa.Column('feedback_reminders', sa.Boolean(), default=True),
            sa.Column('fcm_token', sa.String(500), nullable=True),
            sa.Column('fcm_token_updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_notification_preferences_id', 'notification_preferences', ['id'], unique=False)

    # 6. match_offers
    if 'match_offers' not in existing_tables:
        op.create_table(
            'match_offers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=False),
            sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('candidate_type', sa.String(50), nullable=False),
            sa.Column('score', sa.Float(), default=0.0),
            sa.Column('status', sa.String(50), default='offered'),
            sa.Column('wave_number', sa.Integer(), default=1),
            sa.Column('offered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('response_time_seconds', sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_match_offers_id', 'match_offers', ['id'], unique=False)
        op.create_index('ix_match_offers_donation_id', 'match_offers', ['donation_id'], unique=False)

    # 7. volunteer_assignments
    if 'volunteer_assignments' not in existing_tables:
        op.create_table(
            'volunteer_assignments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=False),
            sa.Column('volunteer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('status', sa.String(50), default='assigned'),
            sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_volunteer_assignments_id', 'volunteer_assignments', ['id'], unique=False)

    # 8. pickup_otp_records
    if 'pickup_otp_records' not in existing_tables:
        op.create_table(
            'pickup_otp_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=False),
            sa.Column('donor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('volunteer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('purpose', sa.String(50), default='PICKUP_VERIFICATION_OTP'),
            sa.Column('otp_hash', sa.String(128), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('delivery_status', sa.String(50), default='QUEUED'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_pickup_otp_records_id', 'pickup_otp_records', ['id'], unique=False)
        op.create_index('ix_pickup_otp_records_donation_id', 'pickup_otp_records', ['donation_id'], unique=False)

    # 9. otp_delivery_records
    if 'otp_delivery_records' not in existing_tables:
        op.create_table(
            'otp_delivery_records',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('otp_record_id', sa.Integer(), sa.ForeignKey('pickup_otp_records.id'), nullable=False),
            sa.Column('provider', sa.String(50), default='MOCK_SMS'),
            sa.Column('provider_message_id', sa.String(100), nullable=True),
            sa.Column('phone_masked', sa.String(50), nullable=True),
            sa.Column('delivery_status', sa.String(50), default='QUEUED'),
            sa.Column('attempt_count', sa.Integer(), default=1),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_otp_delivery_records_id', 'otp_delivery_records', ['id'], unique=False)

    # 10. audit_logs
    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('action', sa.String(100), nullable=False),
            sa.Column('resource_type', sa.String(50), nullable=True),
            sa.Column('resource_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(50), default='success'),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(50), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)

    # 11. rescue_feedbacks
    if 'rescue_feedbacks' not in existing_tables:
        op.create_table(
            'rescue_feedbacks',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=False),
            sa.Column('submitted_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('participant_role', sa.String(50), nullable=False),
            sa.Column('food_condition_on_arrival', sa.String(50), nullable=True),
            sa.Column('packaging_integrity_rating', sa.Integer(), nullable=True),
            sa.Column('overall_rating', sa.Integer(), nullable=False),
            sa.Column('comments', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_rescue_feedbacks_id', 'rescue_feedbacks', ['id'], unique=False)

    # 12. rescue_issue_reports
    if 'rescue_issue_reports' not in existing_tables:
        op.create_table(
            'rescue_issue_reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('donation_id', sa.Integer(), sa.ForeignKey('food_donations.id'), nullable=False),
            sa.Column('reporter_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('reporter_role', sa.String(50), nullable=False),
            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('severity', sa.String(50), default='NORMAL'),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('status', sa.String(50), default='OPEN'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_rescue_issue_reports_id', 'rescue_issue_reports', ['id'], unique=False)


def downgrade() -> None:
    pass
