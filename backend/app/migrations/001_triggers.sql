-- =============================================================================
-- WOMS PostgreSQL Triggers
-- 
-- This file contains all trigger functions for the WOMS database.
-- Run this after Alembic migrations have created the schema.
--
-- Triggers:
-- 1. update_timestamp() - Auto-update updated_at columns
-- 2. check_inventory_threshold() - Low stock alert trigger
-- 3. update_inventory_on_transaction() - Auto-calculate inventory levels
-- =============================================================================

-- =============================================================================
-- 1. AUTO-UPDATE TIMESTAMP TRIGGER
-- =============================================================================

-- Function: Automatically update updated_at timestamp on row modification
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply timestamp trigger to items table
DROP TRIGGER IF EXISTS trg_items_timestamp ON items;
CREATE TRIGGER trg_items_timestamp
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to orders table
DROP TRIGGER IF EXISTS trg_orders_timestamp ON orders;
CREATE TRIGGER trg_orders_timestamp
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to order_details table
DROP TRIGGER IF EXISTS trg_order_details_timestamp ON order_details;
CREATE TRIGGER trg_order_details_timestamp
    BEFORE UPDATE ON order_details
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to warehouse table
DROP TRIGGER IF EXISTS trg_warehouse_timestamp ON warehouse;
CREATE TRIGGER trg_warehouse_timestamp
    BEFORE UPDATE ON warehouse
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to inventory_levels table
DROP TRIGGER IF EXISTS trg_inventory_levels_timestamp ON inventory_levels;
CREATE TRIGGER trg_inventory_levels_timestamp
    BEFORE UPDATE ON inventory_levels
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to platform_sku table
DROP TRIGGER IF EXISTS trg_platform_sku_timestamp ON platform_sku;
CREATE TRIGGER trg_platform_sku_timestamp
    BEFORE UPDATE ON platform_sku
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Apply timestamp trigger to seller_warehouses table
DROP TRIGGER IF EXISTS trg_seller_warehouses_timestamp ON seller_warehouses;
CREATE TRIGGER trg_seller_warehouses_timestamp
    BEFORE UPDATE ON seller_warehouses
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- =============================================================================
-- 2. INVENTORY THRESHOLD CHECK TRIGGER
-- =============================================================================

-- Function: Check inventory levels and create alerts when thresholds breached
CREATE OR REPLACE FUNCTION check_inventory_threshold()
RETURNS TRIGGER AS $$
DECLARE
    v_warehouse_id INTEGER;
    v_alert_type VARCHAR(50);
    v_alert_message VARCHAR(500);
    v_threshold INTEGER;
BEGIN
    -- Get warehouse_id from inventory_location
    SELECT warehouse_id INTO v_warehouse_id
    FROM inventory_location
    WHERE id = NEW.location_id;
    
    -- Determine alert type based on quantity and thresholds
    IF NEW.quantity_available = 0 THEN
        v_alert_type := 'out_of_stock';
        v_threshold := 0;
        v_alert_message := 'Item is out of stock at this location';
    ELSIF NEW.safety_stock IS NOT NULL AND NEW.quantity_available <= NEW.safety_stock THEN
        v_alert_type := 'critical';
        v_threshold := NEW.safety_stock;
        v_alert_message := 'Stock level below safety stock threshold';
    ELSIF NEW.reorder_point IS NOT NULL AND NEW.quantity_available <= NEW.reorder_point THEN
        v_alert_type := 'low_stock';
        v_threshold := NEW.reorder_point;
        v_alert_message := 'Stock level below reorder point';
    ELSIF NEW.max_stock IS NOT NULL AND NEW.quantity_available >= NEW.max_stock THEN
        v_alert_type := 'overstock';
        v_threshold := NEW.max_stock;
        v_alert_message := 'Stock level exceeds maximum threshold';
    ELSE
        -- No alert needed, clear alert status if previously triggered
        IF OLD.alert_triggered_at IS NOT NULL THEN
            NEW.alert_triggered_at := NULL;
            NEW.alert_acknowledged := FALSE;
        END IF;
        RETURN NEW;
    END IF;
    
    -- Only create alert if quantity actually changed or alert not already active
    IF OLD.quantity_available IS DISTINCT FROM NEW.quantity_available 
       OR OLD.alert_triggered_at IS NULL THEN
        
        -- Insert new alert (only if not already exists unresolved for same type)
        INSERT INTO inventory_alerts (
            inventory_level_id,
            item_id,
            warehouse_id,
            alert_type,
            current_quantity,
            threshold_quantity,
            alert_message,
            is_resolved,
            created_at
        )
        SELECT
            NEW.id,
            NEW.item_id,
            v_warehouse_id,
            v_alert_type,
            NEW.quantity_available,
            v_threshold,
            v_alert_message,
            FALSE,
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM inventory_alerts
            WHERE inventory_level_id = NEW.id
              AND alert_type = v_alert_type
              AND is_resolved = FALSE
        );
        
        -- Update alert timestamp on inventory level
        NEW.alert_triggered_at := NOW();
        NEW.alert_acknowledged := FALSE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire on inventory level updates
DROP TRIGGER IF EXISTS trg_inventory_threshold_check ON inventory_levels;
CREATE TRIGGER trg_inventory_threshold_check
    BEFORE UPDATE OF quantity_available, reorder_point, safety_stock, max_stock
    ON inventory_levels
    FOR EACH ROW
    EXECUTE FUNCTION check_inventory_threshold();

-- =============================================================================
-- 3. INVENTORY TRANSACTION AUTO-CALCULATOR
-- =============================================================================

-- Function: Update inventory level when a transaction is recorded
CREATE OR REPLACE FUNCTION update_inventory_on_transaction()
RETURNS TRIGGER AS $$
DECLARE
    v_current_qty INTEGER;
BEGIN
    -- Get current quantity (or 0 if level doesn't exist)
    SELECT quantity_available INTO v_current_qty
    FROM inventory_levels
    WHERE location_id = NEW.location_id AND item_id = NEW.item_id;
    
    IF v_current_qty IS NULL THEN
        -- Create new inventory level record
        INSERT INTO inventory_levels (
            location_id,
            item_id,
            quantity_available,
            created_at,
            updated_at
        )
        VALUES (
            NEW.location_id,
            NEW.item_id,
            CASE WHEN NEW.is_inbound THEN NEW.quantity_change ELSE -NEW.quantity_change END,
            NOW(),
            NOW()
        );
    ELSE
        -- Update existing inventory level
        IF NEW.is_inbound THEN
            UPDATE inventory_levels
            SET quantity_available = quantity_available + NEW.quantity_change,
                updated_at = NOW()
            WHERE location_id = NEW.location_id AND item_id = NEW.item_id;
        ELSE
            UPDATE inventory_levels
            SET quantity_available = GREATEST(0, quantity_available - NEW.quantity_change),
                updated_at = NOW()
            WHERE location_id = NEW.location_id AND item_id = NEW.item_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire after inventory transaction is inserted
DROP TRIGGER IF EXISTS trg_inventory_transaction ON inventory_transactions;
CREATE TRIGGER trg_inventory_transaction
    AFTER INSERT ON inventory_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_inventory_on_transaction();

-- =============================================================================
-- 4. AUTO-RESOLVE INVENTORY ALERTS
-- =============================================================================

-- Function: Automatically resolve alerts when stock is replenished
CREATE OR REPLACE FUNCTION auto_resolve_inventory_alerts()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if we should resolve low_stock/critical/out_of_stock alerts
    IF NEW.quantity_available > COALESCE(NEW.reorder_point, 0) 
       AND NEW.quantity_available > COALESCE(NEW.safety_stock, 0) 
       AND NEW.quantity_available > 0 THEN
        -- Resolve any open low stock alerts
        UPDATE inventory_alerts
        SET is_resolved = TRUE,
            resolved_at = NOW(),
            resolution_notes = 'Auto-resolved: Stock replenished above threshold'
        WHERE inventory_level_id = NEW.id
          AND alert_type IN ('low_stock', 'critical', 'out_of_stock')
          AND is_resolved = FALSE;
    END IF;
    
    -- Check if we should resolve overstock alerts
    IF NEW.max_stock IS NOT NULL AND NEW.quantity_available < NEW.max_stock THEN
        UPDATE inventory_alerts
        SET is_resolved = TRUE,
            resolved_at = NOW(),
            resolution_notes = 'Auto-resolved: Stock reduced below maximum threshold'
        WHERE inventory_level_id = NEW.id
          AND alert_type = 'overstock'
          AND is_resolved = FALSE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Fire after inventory level is updated (separate from threshold check)
DROP TRIGGER IF EXISTS trg_auto_resolve_alerts ON inventory_levels;
CREATE TRIGGER trg_auto_resolve_alerts
    AFTER UPDATE OF quantity_available ON inventory_levels
    FOR EACH ROW
    EXECUTE FUNCTION auto_resolve_inventory_alerts();

-- =============================================================================
-- 5. ORDER STATUS HISTORY TRACKING (OPTIONAL)
-- =============================================================================

-- This trigger can be enabled if you want to track order status changes
-- Uncomment if needed

/*
CREATE OR REPLACE FUNCTION track_order_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.order_status IS DISTINCT FROM NEW.order_status THEN
        -- Insert into an order_status_history table if you create one
        -- INSERT INTO order_status_history (order_id, old_status, new_status, changed_at)
        -- VALUES (NEW.order_id, OLD.order_status, NEW.order_status, NOW());
        
        -- For now, just update the updated_at timestamp (handled by other trigger)
        NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_order_status_change ON orders;
CREATE TRIGGER trg_order_status_change
    AFTER UPDATE OF order_status ON orders
    FOR EACH ROW
    EXECUTE FUNCTION track_order_status_change();
*/

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- List all triggers in the database
-- SELECT trigger_name, event_manipulation, event_object_table, action_statement
-- FROM information_schema.triggers
-- WHERE trigger_schema = 'public';

-- List all functions
-- SELECT routine_name, routine_type
-- FROM information_schema.routines
-- WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';
