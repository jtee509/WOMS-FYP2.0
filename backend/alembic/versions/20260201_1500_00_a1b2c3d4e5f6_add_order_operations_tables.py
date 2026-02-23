"""Add order operations tables (returns, exchanges, modifications, price adjustments)

Revision ID: a1b2c3d4e5f6
Revises: d3872ba21745
Create Date: 2026-02-01 15:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd3872ba21745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Return Reason Lookup Table ###
    op.create_table('return_reason',
        sa.Column('reason_id', sa.Integer(), nullable=False),
        sa.Column('reason_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('reason_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('reason_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('requires_inspection', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('reason_id')
    )
    op.create_index(op.f('ix_return_reason_reason_code'), 'return_reason', ['reason_code'], unique=True)
    op.create_index(op.f('ix_return_reason_reason_type'), 'return_reason', ['reason_type'], unique=False)
    op.create_index(op.f('ix_return_reason_is_active'), 'return_reason', ['is_active'], unique=False)
    
    # ### Exchange Reason Lookup Table ###
    op.create_table('exchange_reason',
        sa.Column('reason_id', sa.Integer(), nullable=False),
        sa.Column('reason_code', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('reason_name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column('requires_return', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('reason_id')
    )
    op.create_index(op.f('ix_exchange_reason_reason_code'), 'exchange_reason', ['reason_code'], unique=True)
    op.create_index(op.f('ix_exchange_reason_is_active'), 'exchange_reason', ['is_active'], unique=False)
    
    # ### Order Returns Table ###
    op.create_table('order_returns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('order_detail_id', sa.Integer(), nullable=False),
        sa.Column('return_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('return_reason_id', sa.Integer(), nullable=True),
        sa.Column('return_status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='requested'),
        sa.Column('returned_quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('inspection_status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True, server_default='pending'),
        sa.Column('inspection_notes', sa.Text(), nullable=True),
        sa.Column('inspected_at', sa.DateTime(), nullable=True),
        sa.Column('inspected_by_user_id', sa.Integer(), nullable=True),
        sa.Column('restock_decision', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column('restocked_quantity', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('restocked_at', sa.DateTime(), nullable=True),
        sa.Column('platform_return_reference', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column('initiated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_detail_id'], ['order_details.detail_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['return_reason_id'], ['return_reason.reason_id']),
        sa.ForeignKeyConstraint(['inspected_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['initiated_by_user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_returns_order_id'), 'order_returns', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_returns_order_detail_id'), 'order_returns', ['order_detail_id'], unique=False)
    op.create_index(op.f('ix_order_returns_return_status'), 'order_returns', ['return_status'], unique=False)
    op.create_index(op.f('ix_order_returns_return_type'), 'order_returns', ['return_type'], unique=False)
    op.create_index(op.f('ix_order_returns_inspection_status'), 'order_returns', ['inspection_status'], unique=False)
    op.create_index(op.f('ix_order_returns_platform_return_reference'), 'order_returns', ['platform_return_reference'], unique=False)
    op.create_index(op.f('ix_order_returns_requested_at'), 'order_returns', ['requested_at'], unique=False)
    
    # ### Order Exchanges Table ###
    op.create_table('order_exchanges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_order_id', sa.Integer(), nullable=False),
        sa.Column('original_detail_id', sa.Integer(), nullable=False),
        sa.Column('exchange_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('exchange_reason_id', sa.Integer(), nullable=True),
        sa.Column('exchange_status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='requested'),
        sa.Column('new_order_id', sa.Integer(), nullable=True),
        sa.Column('new_detail_id', sa.Integer(), nullable=True),
        sa.Column('exchanged_item_id', sa.Integer(), nullable=True),
        sa.Column('exchanged_quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('original_value', sa.Float(), nullable=True, server_default='0'),
        sa.Column('new_value', sa.Float(), nullable=True, server_default='0'),
        sa.Column('value_difference', sa.Float(), nullable=True, server_default='0'),
        sa.Column('adjustment_status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='pending'),
        sa.Column('return_id', sa.Integer(), nullable=True),
        sa.Column('platform_exchange_reference', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True),
        sa.Column('initiated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['original_order_id'], ['orders.order_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['original_detail_id'], ['order_details.detail_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['exchange_reason_id'], ['exchange_reason.reason_id']),
        sa.ForeignKeyConstraint(['new_order_id'], ['orders.order_id']),
        sa.ForeignKeyConstraint(['new_detail_id'], ['order_details.detail_id']),
        sa.ForeignKeyConstraint(['exchanged_item_id'], ['items.item_id']),
        sa.ForeignKeyConstraint(['return_id'], ['order_returns.id']),
        sa.ForeignKeyConstraint(['initiated_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_exchanges_original_order_id'), 'order_exchanges', ['original_order_id'], unique=False)
    op.create_index(op.f('ix_order_exchanges_original_detail_id'), 'order_exchanges', ['original_detail_id'], unique=False)
    op.create_index(op.f('ix_order_exchanges_new_order_id'), 'order_exchanges', ['new_order_id'], unique=False)
    op.create_index(op.f('ix_order_exchanges_exchange_status'), 'order_exchanges', ['exchange_status'], unique=False)
    op.create_index(op.f('ix_order_exchanges_exchange_type'), 'order_exchanges', ['exchange_type'], unique=False)
    op.create_index(op.f('ix_order_exchanges_return_id'), 'order_exchanges', ['return_id'], unique=False)
    op.create_index(op.f('ix_order_exchanges_platform_exchange_reference'), 'order_exchanges', ['platform_exchange_reference'], unique=False)
    op.create_index(op.f('ix_order_exchanges_requested_at'), 'order_exchanges', ['requested_at'], unique=False)
    
    # ### Order Modifications Table ###
    op.create_table('order_modifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('order_detail_id', sa.Integer(), nullable=True),
        sa.Column('modification_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('field_changed', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('modification_reason', sa.Text(), nullable=True),
        sa.Column('related_exchange_id', sa.Integer(), nullable=True),
        sa.Column('related_return_id', sa.Integer(), nullable=True),
        sa.Column('modified_by_user_id', sa.Integer(), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_detail_id'], ['order_details.detail_id']),
        sa.ForeignKeyConstraint(['related_exchange_id'], ['order_exchanges.id']),
        sa.ForeignKeyConstraint(['related_return_id'], ['order_returns.id']),
        sa.ForeignKeyConstraint(['modified_by_user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_modifications_order_id'), 'order_modifications', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_modifications_order_detail_id'), 'order_modifications', ['order_detail_id'], unique=False)
    op.create_index(op.f('ix_order_modifications_modification_type'), 'order_modifications', ['modification_type'], unique=False)
    op.create_index(op.f('ix_order_modifications_field_changed'), 'order_modifications', ['field_changed'], unique=False)
    op.create_index(op.f('ix_order_modifications_modified_by_user_id'), 'order_modifications', ['modified_by_user_id'], unique=False)
    op.create_index(op.f('ix_order_modifications_modified_at'), 'order_modifications', ['modified_at'], unique=False)
    op.create_index(op.f('ix_order_modifications_related_exchange_id'), 'order_modifications', ['related_exchange_id'], unique=False)
    op.create_index(op.f('ix_order_modifications_related_return_id'), 'order_modifications', ['related_return_id'], unique=False)
    # GIN indexes for JSONB
    op.create_index('ix_order_modifications_old_value_gin', 'order_modifications', ['old_value'], unique=False, postgresql_using='gin')
    op.create_index('ix_order_modifications_new_value_gin', 'order_modifications', ['new_value'], unique=False, postgresql_using='gin')
    
    # ### Order Price Adjustments Table ###
    op.create_table('order_price_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('order_detail_id', sa.Integer(), nullable=True),
        sa.Column('adjustment_type', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('adjustment_reason', sa.Text(), nullable=False),
        sa.Column('original_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('adjustment_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('final_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('related_exchange_id', sa.Integer(), nullable=True),
        sa.Column('related_modification_id', sa.Integer(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False, server_default='pending'),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('applied_by_user_id', sa.Integer(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_detail_id'], ['order_details.detail_id']),
        sa.ForeignKeyConstraint(['related_exchange_id'], ['order_exchanges.id']),
        sa.ForeignKeyConstraint(['related_modification_id'], ['order_modifications.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['applied_by_user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_price_adjustments_order_id'), 'order_price_adjustments', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_order_detail_id'), 'order_price_adjustments', ['order_detail_id'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_adjustment_type'), 'order_price_adjustments', ['adjustment_type'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_status'), 'order_price_adjustments', ['status'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_related_exchange_id'), 'order_price_adjustments', ['related_exchange_id'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_related_modification_id'), 'order_price_adjustments', ['related_modification_id'], unique=False)
    op.create_index(op.f('ix_order_price_adjustments_created_at'), 'order_price_adjustments', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of creation (due to foreign key dependencies)
    
    # Drop order_price_adjustments
    op.drop_index(op.f('ix_order_price_adjustments_created_at'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_related_modification_id'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_related_exchange_id'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_status'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_adjustment_type'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_order_detail_id'), table_name='order_price_adjustments')
    op.drop_index(op.f('ix_order_price_adjustments_order_id'), table_name='order_price_adjustments')
    op.drop_table('order_price_adjustments')
    
    # Drop order_modifications
    op.drop_index('ix_order_modifications_new_value_gin', table_name='order_modifications')
    op.drop_index('ix_order_modifications_old_value_gin', table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_related_return_id'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_related_exchange_id'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_modified_at'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_modified_by_user_id'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_field_changed'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_modification_type'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_order_detail_id'), table_name='order_modifications')
    op.drop_index(op.f('ix_order_modifications_order_id'), table_name='order_modifications')
    op.drop_table('order_modifications')
    
    # Drop order_exchanges
    op.drop_index(op.f('ix_order_exchanges_requested_at'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_platform_exchange_reference'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_return_id'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_exchange_type'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_exchange_status'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_new_order_id'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_original_detail_id'), table_name='order_exchanges')
    op.drop_index(op.f('ix_order_exchanges_original_order_id'), table_name='order_exchanges')
    op.drop_table('order_exchanges')
    
    # Drop order_returns
    op.drop_index(op.f('ix_order_returns_requested_at'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_platform_return_reference'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_inspection_status'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_return_type'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_return_status'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_order_detail_id'), table_name='order_returns')
    op.drop_index(op.f('ix_order_returns_order_id'), table_name='order_returns')
    op.drop_table('order_returns')
    
    # Drop exchange_reason
    op.drop_index(op.f('ix_exchange_reason_is_active'), table_name='exchange_reason')
    op.drop_index(op.f('ix_exchange_reason_reason_code'), table_name='exchange_reason')
    op.drop_table('exchange_reason')
    
    # Drop return_reason
    op.drop_index(op.f('ix_return_reason_is_active'), table_name='return_reason')
    op.drop_index(op.f('ix_return_reason_reason_type'), table_name='return_reason')
    op.drop_index(op.f('ix_return_reason_reason_code'), table_name='return_reason')
    op.drop_table('return_reason')
