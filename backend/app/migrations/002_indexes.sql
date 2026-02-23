-- =============================================================================
-- WOMS PostgreSQL Indexes
-- 
-- This file contains all performance indexes for the WOMS database.
-- Run this after Alembic migrations have created the schema.
--
-- Index Types:
-- 1. GIN indexes for JSONB fields (enable efficient JSON queries)
-- 2. Composite indexes for common query patterns
-- 3. Partial indexes for filtered queries
-- =============================================================================

-- =============================================================================
-- 1. GIN INDEXES FOR JSONB FIELDS
-- =============================================================================

-- Items: Variations data JSONB index
-- Enables queries like: WHERE variations_data @> '{"color": "red"}'
DROP INDEX IF EXISTS idx_items_variations_gin;
CREATE INDEX idx_items_variations_gin 
    ON items USING GIN (variations_data jsonb_path_ops);

-- Orders: Platform raw data JSONB index
-- Enables queries on preserved platform data
DROP INDEX IF EXISTS idx_orders_platform_raw_gin;
CREATE INDEX idx_orders_platform_raw_gin 
    ON orders USING GIN (platform_raw_data jsonb_path_ops);

-- Orders: Billing address JSONB index
DROP INDEX IF EXISTS idx_orders_billing_address_gin;
CREATE INDEX idx_orders_billing_address_gin 
    ON orders USING GIN (billing_address jsonb_path_ops);

-- Order Details: Platform SKU data JSONB index
DROP INDEX IF EXISTS idx_order_details_sku_gin;
CREATE INDEX idx_order_details_sku_gin 
    ON order_details USING GIN (platform_sku_data jsonb_path_ops);

-- Customer Platform: Customer data JSONB index
DROP INDEX IF EXISTS idx_customer_data_gin;
CREATE INDEX idx_customer_data_gin 
    ON customer_platform USING GIN (customer_data jsonb_path_ops);

-- Warehouse: Address JSONB index
DROP INDEX IF EXISTS idx_warehouse_address_gin;
CREATE INDEX idx_warehouse_address_gin 
    ON warehouse USING GIN (address jsonb_path_ops);

-- Platform Raw Imports: Raw data JSONB index
DROP INDEX IF EXISTS idx_raw_import_data_gin;
CREATE INDEX idx_raw_import_data_gin 
    ON platform_raw_imports USING GIN (raw_data jsonb_path_ops);

-- Company Firms: Contact info JSONB index
DROP INDEX IF EXISTS idx_company_contact_gin;
CREATE INDEX idx_company_contact_gin 
    ON company_firms USING GIN (contact_info jsonb_path_ops);

-- Roles: Permissions JSONB index
DROP INDEX IF EXISTS idx_roles_permissions_gin;
CREATE INDEX idx_roles_permissions_gin 
    ON roles USING GIN (permissions jsonb_path_ops);

-- Items History: Snapshot data JSONB index
DROP INDEX IF EXISTS idx_items_history_snapshot_gin;
CREATE INDEX idx_items_history_snapshot_gin 
    ON items_history USING GIN (snapshot_data jsonb_path_ops);

-- Audit Log: Old and new data JSONB indexes
DROP INDEX IF EXISTS idx_audit_old_data_gin;
CREATE INDEX idx_audit_old_data_gin 
    ON audit_log USING GIN (old_data jsonb_path_ops);

DROP INDEX IF EXISTS idx_audit_new_data_gin;
CREATE INDEX idx_audit_new_data_gin 
    ON audit_log USING GIN (new_data jsonb_path_ops);

-- =============================================================================
-- 2. COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
-- =============================================================================

-- Orders: Platform + Store combination (common filter)
DROP INDEX IF EXISTS idx_orders_platform_store;
CREATE INDEX idx_orders_platform_store 
    ON orders (platform_id, store_id);

-- Orders: Warehouse + Status (fulfillment queries)
DROP INDEX IF EXISTS idx_orders_warehouse_status;
CREATE INDEX idx_orders_warehouse_status 
    ON orders (assigned_warehouse_id, order_status);

-- Orders: Date range + Status (reporting queries)
DROP INDEX IF EXISTS idx_orders_date_status;
CREATE INDEX idx_orders_date_status 
    ON orders (order_date, order_status);

-- Inventory Levels: Item + Location (stock lookup)
DROP INDEX IF EXISTS idx_inventory_item_location;
CREATE INDEX idx_inventory_item_location 
    ON inventory_levels (item_id, location_id);

-- Inventory Levels: Location + Lot (FIFO/FEFO queries)
DROP INDEX IF EXISTS idx_inventory_location_lot;
CREATE INDEX idx_inventory_location_lot 
    ON inventory_levels (location_id, lot_id);

-- Platform SKU: Seller + Platform (listing lookup)
DROP INDEX IF EXISTS idx_platform_sku_seller;
CREATE INDEX idx_platform_sku_seller 
    ON platform_sku (seller_id, platform_id);

-- Platform SKU: Platform + SKU (translation lookup)
DROP INDEX IF EXISTS idx_platform_sku_lookup;
CREATE INDEX idx_platform_sku_lookup 
    ON platform_sku (platform_id, platform_sku);

-- Order Details: Order + Item (fulfillment queries)
DROP INDEX IF EXISTS idx_order_details_order_item;
CREATE INDEX idx_order_details_order_item 
    ON order_details (order_id, resolved_item_id);

-- Order Details: Fulfillment status (picking/packing queries)
DROP INDEX IF EXISTS idx_order_details_fulfillment;
CREATE INDEX idx_order_details_fulfillment 
    ON order_details (fulfillment_status, order_id);

-- Inventory Alerts: Resolution status + Type (dashboard queries)
DROP INDEX IF EXISTS idx_inventory_alerts_status_type;
CREATE INDEX idx_inventory_alerts_status_type 
    ON inventory_alerts (is_resolved, alert_type);

-- Inventory Alerts: Warehouse + Status (per-warehouse dashboard)
DROP INDEX IF EXISTS idx_inventory_alerts_warehouse;
CREATE INDEX idx_inventory_alerts_warehouse 
    ON inventory_alerts (warehouse_id, is_resolved);

-- Seller Warehouses: Seller + Active (routing lookup)
DROP INDEX IF EXISTS idx_seller_warehouses_active;
CREATE INDEX idx_seller_warehouses_active 
    ON seller_warehouses (seller_id, is_active);

-- Delivery Trips: Team + Status (trip scheduling)
DROP INDEX IF EXISTS idx_delivery_trips_team_status;
CREATE INDEX idx_delivery_trips_team_status 
    ON delivery_trips (team_id, trip_status);

-- Tracking Status: Tracking number + Date (status history)
DROP INDEX IF EXISTS idx_tracking_status_history;
CREATE INDEX idx_tracking_status_history 
    ON tracking_status (tracking_number, status_date DESC);

-- Platform Raw Imports: Status + Platform (processing queue)
DROP INDEX IF EXISTS idx_raw_imports_processing;
CREATE INDEX idx_raw_imports_processing 
    ON platform_raw_imports (status, platform_id);

-- Platform Raw Imports: Batch ID (batch processing)
DROP INDEX IF EXISTS idx_raw_imports_batch;
CREATE INDEX idx_raw_imports_batch 
    ON platform_raw_imports (import_batch_id);

-- Inventory Transactions: Movement + Date (transaction history)
DROP INDEX IF EXISTS idx_transactions_movement_date;
CREATE INDEX idx_transactions_movement_date 
    ON inventory_transactions (movement_id, created_at DESC);

-- Inventory Transactions: Item + Location + Date (item history)
DROP INDEX IF EXISTS idx_transactions_item_location;
CREATE INDEX idx_transactions_item_location 
    ON inventory_transactions (item_id, location_id, created_at DESC);

-- =============================================================================
-- 3. PARTIAL INDEXES FOR FILTERED QUERIES
-- =============================================================================

-- Active items only (common filter)
DROP INDEX IF EXISTS idx_items_active;
CREATE INDEX idx_items_active 
    ON items (item_id, master_sku) 
    WHERE deleted_at IS NULL;

-- Active warehouses only
DROP INDEX IF EXISTS idx_warehouse_active;
CREATE INDEX idx_warehouse_active 
    ON warehouse (id, warehouse_name) 
    WHERE is_active = TRUE;

-- Active sellers only
DROP INDEX IF EXISTS idx_sellers_active;
CREATE INDEX idx_sellers_active 
    ON seller (seller_id, store_name) 
    WHERE is_active = TRUE;

-- Pending orders (fulfillment queue)
DROP INDEX IF EXISTS idx_orders_pending;
CREATE INDEX idx_orders_pending 
    ON orders (order_id, order_date) 
    WHERE order_status = 'pending';

-- Unresolved inventory alerts (dashboard)
DROP INDEX IF EXISTS idx_alerts_unresolved;
CREATE INDEX idx_alerts_unresolved 
    ON inventory_alerts (warehouse_id, alert_type, created_at) 
    WHERE is_resolved = FALSE;

-- Low stock inventory (quick lookup)
DROP INDEX IF EXISTS idx_inventory_low_stock;
CREATE INDEX idx_inventory_low_stock 
    ON inventory_levels (item_id, location_id) 
    WHERE alert_triggered_at IS NOT NULL;

-- Pending raw imports (processing queue)
DROP INDEX IF EXISTS idx_raw_imports_pending;
CREATE INDEX idx_raw_imports_pending 
    ON platform_raw_imports (platform_id, created_at) 
    WHERE status = 'pending';

-- Active platform SKUs (listing lookup)
DROP INDEX IF EXISTS idx_platform_sku_active;
CREATE INDEX idx_platform_sku_active 
    ON platform_sku (platform_id, seller_id, platform_sku) 
    WHERE is_active = TRUE;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- List all indexes in the database
-- SELECT indexname, tablename, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'public'
-- ORDER BY tablename, indexname;

-- Check index sizes
-- SELECT
--     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
--     indexrelname AS index_name,
--     relname AS table_name
-- FROM pg_stat_user_indexes
-- ORDER BY pg_relation_size(indexrelid) DESC;
