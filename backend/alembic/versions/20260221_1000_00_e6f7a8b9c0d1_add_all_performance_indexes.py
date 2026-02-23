"""Add all performance indexes (GIN, composite, partial)

All PostgreSQL indexes previously defined only in migrations/002_indexes.sql and
migrations/005_order_operations.sql are now embedded in the SQLModel __table_args__
so they are created automatically on a fresh database via create_all().

This migration applies them to any existing database that was built before the
__table_args__ approach was adopted.

All CREATE INDEX statements use IF NOT EXISTS — safe to re-run on any database.

Indexes added:
  GIN (JSONB): items.variations_data, items_history.snapshot_data,
               warehouse.address, company_firms.contact_info, roles.permissions,
               audit_log.old_data, audit_log.new_data,
               orders.platform_raw_data, orders.billing_address,
               order_details.platform_sku_data, customer_platform.customer_data,
               platform_raw_imports.raw_data,
               order_modifications.old_value, order_modifications.new_value
  Composite:   inventory_levels, inventory_alerts, seller_warehouses,
               inventory_transactions, delivery_trips, tracking_status,
               platform_sku, platform_raw_imports, orders, order_details
  Partial:     items, warehouse, seller, platform_sku, orders,
               inventory_levels, inventory_alerts, platform_raw_imports,
               return_reason, order_returns, exchange_reason,
               order_exchanges, order_modifications, order_price_adjustments

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-02-21 10:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # GIN INDEXES — JSONB fields
    # =========================================================================

    # items.variations_data — enables WHERE variations_data @> '{"color":"red"}'
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_items_variations_gin
        ON items USING GIN (variations_data jsonb_path_ops)
    """)

    # items_history.snapshot_data — enables JSON queries on historical snapshots
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_items_history_snapshot_gin
        ON items_history USING GIN (snapshot_data jsonb_path_ops)
    """)

    # warehouse.address — enables address-component queries on warehouse JSONB
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_warehouse_address_gin
        ON warehouse USING GIN (address jsonb_path_ops)
    """)

    # company_firms.contact_info — enables phone/email/address field queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_company_contact_gin
        ON company_firms USING GIN (contact_info jsonb_path_ops)
    """)

    # roles.permissions — enables permission-level queries on role JSONB
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_roles_permissions_gin
        ON roles USING GIN (permissions jsonb_path_ops)
    """)

    # audit_log.old_data / new_data — enables before/after change queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_old_data_gin
        ON audit_log USING GIN (old_data jsonb_path_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_new_data_gin
        ON audit_log USING GIN (new_data jsonb_path_ops)
    """)

    # orders.platform_raw_data / billing_address — platform fee/variation queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_platform_raw_gin
        ON orders USING GIN (platform_raw_data jsonb_path_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_billing_address_gin
        ON orders USING GIN (billing_address jsonb_path_ops)
    """)

    # order_details.platform_sku_data — enables querying raw SKU/variation data
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_details_sku_gin
        ON order_details USING GIN (platform_sku_data jsonb_path_ops)
    """)

    # customer_platform.customer_data — enables loyalty/tier/ID queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_customer_data_gin
        ON customer_platform USING GIN (customer_data jsonb_path_ops)
    """)

    # platform_raw_imports.raw_data — enables field-level queries on raw import JSONB
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_raw_import_data_gin
        ON platform_raw_imports USING GIN (raw_data jsonb_path_ops)
    """)

    # order_modifications.old_value / new_value — enables querying JSONB diffs
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_modifications_old_value
        ON order_modifications USING GIN (old_value jsonb_path_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_modifications_new_value
        ON order_modifications USING GIN (new_value jsonb_path_ops)
    """)

    # =========================================================================
    # COMPOSITE INDEXES — common multi-column query patterns
    # =========================================================================

    # inventory_levels: stock lookup (item + location) and FIFO/FEFO (location + lot)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_item_location
        ON inventory_levels (item_id, location_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_location_lot
        ON inventory_levels (location_id, lot_id)
    """)

    # inventory_alerts: dashboard by type and per-warehouse dashboard
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_alerts_status_type
        ON inventory_alerts (is_resolved, alert_type)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_alerts_warehouse
        ON inventory_alerts (warehouse_id, is_resolved)
    """)

    # seller_warehouses: active seller routing lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_seller_warehouses_active
        ON seller_warehouses (seller_id, is_active)
    """)

    # inventory_transactions: movement history and item-location history
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_movement_date
        ON inventory_transactions (movement_id, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_item_location
        ON inventory_transactions (item_id, location_id, created_at DESC)
    """)

    # delivery_trips: trip scheduling / dispatch queue
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_delivery_trips_team_status
        ON delivery_trips (team_id, trip_status)
    """)

    # tracking_status: status history timeline per tracking number
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tracking_status_history
        ON tracking_status (tracking_number, status_date DESC)
    """)

    # platform_sku: SKU translation lookups (seller→platform, platform→SKU)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_platform_sku_seller
        ON platform_sku (seller_id, platform_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_platform_sku_lookup
        ON platform_sku (platform_id, platform_sku)
    """)

    # platform_raw_imports: processing queue by status+platform
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_raw_imports_processing
        ON platform_raw_imports (status, platform_id)
    """)

    # orders: store/platform filter, warehouse fulfillment queue, date reporting
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_platform_store
        ON orders (platform_id, store_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_warehouse_status
        ON orders (assigned_warehouse_id, order_status)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_date_status
        ON orders (order_date, order_status)
    """)

    # order_details: fulfillment and item lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_details_order_item
        ON order_details (order_id, resolved_item_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_details_fulfillment
        ON order_details (fulfillment_status, order_id)
    """)

    # =========================================================================
    # PARTIAL INDEXES — filtered queries (skip irrelevant rows)
    # =========================================================================

    # items: active items only (deleted_at IS NULL is the most common WHERE)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_items_active
        ON items (item_id, master_sku)
        WHERE deleted_at IS NULL
    """)

    # warehouse: active warehouses only
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_warehouse_active
        ON warehouse (id, warehouse_name)
        WHERE is_active = TRUE
    """)

    # seller: active sellers only (routing/lookup almost always filters active)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_sellers_active
        ON seller (seller_id, store_name)
        WHERE is_active = TRUE
    """)

    # platform_sku: active SKUs only (translation always requires active listings)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_platform_sku_active
        ON platform_sku (platform_id, seller_id, platform_sku)
        WHERE is_active = TRUE
    """)

    # orders: pending orders only (the primary fulfillment queue)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_pending
        ON orders (order_id, order_date)
        WHERE order_status = 'pending'
    """)

    # inventory_levels: rows that have triggered an alert (alert dashboard)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_inventory_low_stock
        ON inventory_levels (item_id, location_id)
        WHERE alert_triggered_at IS NOT NULL
    """)

    # inventory_alerts: unresolved alerts only (the live alert dashboard)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_unresolved
        ON inventory_alerts (warehouse_id, alert_type, created_at)
        WHERE is_resolved = FALSE
    """)

    # platform_raw_imports: pending imports only (background processing queue)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_raw_imports_pending
        ON platform_raw_imports (platform_id, created_at)
        WHERE status = 'pending'
    """)

    # return_reason / exchange_reason: active reasons only (form dropdowns)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_return_reason_active
        ON return_reason (is_active)
        WHERE is_active = TRUE
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_exchange_reason_active
        ON exchange_reason (is_active)
        WHERE is_active = TRUE
    """)

    # order_returns: rows with a platform reference (marketplace return portal)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_returns_platform_ref
        ON order_returns (platform_return_reference)
        WHERE platform_return_reference IS NOT NULL
    """)

    # order_exchanges: optional FK partial indexes (avoid indexing NULLs)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_exchanges_new_order
        ON order_exchanges (new_order_id)
        WHERE new_order_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_exchanges_return
        ON order_exchanges (return_id)
        WHERE return_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_exchanges_platform_ref
        ON order_exchanges (platform_exchange_reference)
        WHERE platform_exchange_reference IS NOT NULL
    """)

    # order_modifications: optional FK partial indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_modifications_detail_id
        ON order_modifications (order_detail_id)
        WHERE order_detail_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_modifications_exchange
        ON order_modifications (related_exchange_id)
        WHERE related_exchange_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_modifications_return
        ON order_modifications (related_return_id)
        WHERE related_return_id IS NOT NULL
    """)

    # order_price_adjustments: optional FK partial indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_price_adj_detail_id
        ON order_price_adjustments (order_detail_id)
        WHERE order_detail_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_price_adj_exchange
        ON order_price_adjustments (related_exchange_id)
        WHERE related_exchange_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_order_price_adj_modification
        ON order_price_adjustments (related_modification_id)
        WHERE related_modification_id IS NOT NULL
    """)


def downgrade() -> None:
    # Drop all indexes created in upgrade() — reverse order for clarity
    indexes = [
        # order_price_adjustments
        ("idx_order_price_adj_modification", "order_price_adjustments"),
        ("idx_order_price_adj_exchange", "order_price_adjustments"),
        ("idx_order_price_adj_detail_id", "order_price_adjustments"),
        # order_modifications
        ("idx_order_modifications_return", "order_modifications"),
        ("idx_order_modifications_exchange", "order_modifications"),
        ("idx_order_modifications_detail_id", "order_modifications"),
        ("idx_order_modifications_new_value", "order_modifications"),
        ("idx_order_modifications_old_value", "order_modifications"),
        # order_exchanges
        ("idx_order_exchanges_platform_ref", "order_exchanges"),
        ("idx_order_exchanges_return", "order_exchanges"),
        ("idx_order_exchanges_new_order", "order_exchanges"),
        # order_returns
        ("idx_order_returns_platform_ref", "order_returns"),
        # reason tables
        ("idx_exchange_reason_active", "exchange_reason"),
        ("idx_return_reason_active", "return_reason"),
        # platform_raw_imports
        ("idx_raw_imports_pending", "platform_raw_imports"),
        ("idx_alerts_unresolved", "inventory_alerts"),
        ("idx_inventory_low_stock", "inventory_levels"),
        ("idx_orders_pending", "orders"),
        ("idx_platform_sku_active", "platform_sku"),
        ("idx_sellers_active", "seller"),
        ("idx_warehouse_active", "warehouse"),
        ("idx_items_active", "items"),
        # composite
        ("idx_order_details_fulfillment", "order_details"),
        ("idx_order_details_order_item", "order_details"),
        ("idx_orders_date_status", "orders"),
        ("idx_orders_warehouse_status", "orders"),
        ("idx_orders_platform_store", "orders"),
        ("idx_raw_imports_processing", "platform_raw_imports"),
        ("idx_platform_sku_lookup", "platform_sku"),
        ("idx_platform_sku_seller", "platform_sku"),
        ("idx_tracking_status_history", "tracking_status"),
        ("idx_delivery_trips_team_status", "delivery_trips"),
        ("idx_transactions_item_location", "inventory_transactions"),
        ("idx_transactions_movement_date", "inventory_transactions"),
        ("idx_seller_warehouses_active", "seller_warehouses"),
        ("idx_inventory_alerts_warehouse", "inventory_alerts"),
        ("idx_inventory_alerts_status_type", "inventory_alerts"),
        ("idx_inventory_location_lot", "inventory_levels"),
        ("idx_inventory_item_location", "inventory_levels"),
        # GIN
        ("idx_raw_import_data_gin", "platform_raw_imports"),
        ("idx_customer_data_gin", "customer_platform"),
        ("idx_order_details_sku_gin", "order_details"),
        ("idx_orders_billing_address_gin", "orders"),
        ("idx_orders_platform_raw_gin", "orders"),
        ("idx_audit_new_data_gin", "audit_log"),
        ("idx_audit_old_data_gin", "audit_log"),
        ("idx_roles_permissions_gin", "roles"),
        ("idx_company_contact_gin", "company_firms"),
        ("idx_warehouse_address_gin", "warehouse"),
        ("idx_items_history_snapshot_gin", "items_history"),
        ("idx_items_variations_gin", "items"),
    ]
    for idx_name, _ in indexes:
        op.execute(f"DROP INDEX IF EXISTS {idx_name}")
