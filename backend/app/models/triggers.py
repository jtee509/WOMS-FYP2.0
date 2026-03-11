"""
WOMS Database Triggers (Python Module)

All PostgreSQL trigger functions and trigger registrations are defined here
as Python string constants.  The single entry-point `apply_triggers(conn)`
executes every statement idempotently against an open async connection.

WHY Python instead of migrations/001_triggers.sql:
- All DB logic lives in one codebase — no external .sql file dependency.
- `apply_triggers()` is called from database.init_db_full() so a fresh DB
  gets triggers automatically alongside table creation.
- Every function uses CREATE OR REPLACE and every trigger uses
  DROP TRIGGER IF EXISTS, so re-running is always safe.

Triggers defined:
  1. update_timestamp            — auto-update updated_at on all mutable tables
  2. check_inventory_threshold   — create inventory_alerts on threshold breach
  3. update_inventory_on_transaction — maintain inventory_levels from transactions
  4. auto_resolve_inventory_alerts — resolve alerts when stock recovers
  5. update_updated_at_column    — alias used by order_operations tables
  6. sync_order_detail_return_status — sync return_status back to order_details
  7. calculate_exchange_value_difference — auto-compute value_difference
  8. calculate_price_adjustment_final  — auto-compute final_amount
  9. generate_location_display_code — concatenate location hierarchy into display_code
 10. insert_items_history_on_create — audit trail: auto-INSERT into items_history on new item
 11. insert_items_history_on_update — audit trail: capture old state on UPDATE (incl. soft-delete)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


# =============================================================================
# Trigger SQL statements (one entry per logical block)
# =============================================================================

_TRIGGER_SQL: list[str] = [

    # -------------------------------------------------------------------------
    # 1. AUTO-UPDATE TIMESTAMP — applied to all tables with updated_at
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION update_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_items_timestamp ON items",
    """
    CREATE TRIGGER trg_items_timestamp
        BEFORE UPDATE ON items
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_orders_timestamp ON orders",
    """
    CREATE TRIGGER trg_orders_timestamp
        BEFORE UPDATE ON orders
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_order_details_timestamp ON order_details",
    """
    CREATE TRIGGER trg_order_details_timestamp
        BEFORE UPDATE ON order_details
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_warehouse_timestamp ON warehouse",
    """
    CREATE TRIGGER trg_warehouse_timestamp
        BEFORE UPDATE ON warehouse
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_inventory_levels_timestamp ON inventory_levels",
    """
    CREATE TRIGGER trg_inventory_levels_timestamp
        BEFORE UPDATE ON inventory_levels
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_platform_sku_timestamp ON platform_sku",
    """
    CREATE TRIGGER trg_platform_sku_timestamp
        BEFORE UPDATE ON platform_sku
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    "DROP TRIGGER IF EXISTS trg_seller_warehouses_timestamp ON seller_warehouses",
    """
    CREATE TRIGGER trg_seller_warehouses_timestamp
        BEFORE UPDATE ON seller_warehouses
        FOR EACH ROW
        EXECUTE FUNCTION update_timestamp()
    """,

    # -------------------------------------------------------------------------
    # 2. INVENTORY THRESHOLD CHECK — fires on inventory_levels update
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION check_inventory_threshold()
    RETURNS TRIGGER AS $$
    DECLARE
        v_warehouse_id INTEGER;
        v_alert_type   VARCHAR(50);
        v_alert_message VARCHAR(500);
        v_threshold    INTEGER;
    BEGIN
        SELECT warehouse_id INTO v_warehouse_id
        FROM inventory_location
        WHERE id = NEW.location_id;

        IF NEW.quantity_available = 0 THEN
            v_alert_type    := 'out_of_stock';
            v_threshold     := 0;
            v_alert_message := 'Item is out of stock at this location';
        ELSIF NEW.safety_stock IS NOT NULL AND NEW.quantity_available <= NEW.safety_stock THEN
            v_alert_type    := 'critical';
            v_threshold     := NEW.safety_stock;
            v_alert_message := 'Stock level below safety stock threshold';
        ELSIF NEW.reorder_point IS NOT NULL AND NEW.quantity_available <= NEW.reorder_point THEN
            v_alert_type    := 'low_stock';
            v_threshold     := NEW.reorder_point;
            v_alert_message := 'Stock level below reorder point';
        ELSIF NEW.max_stock IS NOT NULL AND NEW.quantity_available >= NEW.max_stock THEN
            v_alert_type    := 'overstock';
            v_threshold     := NEW.max_stock;
            v_alert_message := 'Stock level exceeds maximum threshold';
        ELSE
            IF OLD.alert_triggered_at IS NOT NULL THEN
                NEW.alert_triggered_at := NULL;
                NEW.alert_acknowledged := FALSE;
            END IF;
            RETURN NEW;
        END IF;

        IF OLD.quantity_available IS DISTINCT FROM NEW.quantity_available
           OR OLD.alert_triggered_at IS NULL THEN
            INSERT INTO inventory_alerts (
                inventory_level_id, item_id, warehouse_id, alert_type,
                current_quantity, threshold_quantity, alert_message,
                is_resolved, created_at
            )
            SELECT
                NEW.id, NEW.item_id, v_warehouse_id, v_alert_type,
                NEW.quantity_available, v_threshold, v_alert_message,
                FALSE, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM inventory_alerts
                WHERE inventory_level_id = NEW.id
                  AND alert_type = v_alert_type
                  AND is_resolved = FALSE
            );
            NEW.alert_triggered_at := NOW();
            NEW.alert_acknowledged := FALSE;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_inventory_threshold_check ON inventory_levels",
    """
    CREATE TRIGGER trg_inventory_threshold_check
        BEFORE UPDATE OF quantity_available, reorder_point, safety_stock, max_stock
        ON inventory_levels
        FOR EACH ROW
        EXECUTE FUNCTION check_inventory_threshold()
    """,

    # -------------------------------------------------------------------------
    # 3. INVENTORY TRANSACTION AUTO-CALCULATOR
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION update_inventory_on_transaction()
    RETURNS TRIGGER AS $$
    DECLARE
        v_current_qty INTEGER;
    BEGIN
        SELECT quantity_available INTO v_current_qty
        FROM inventory_levels
        WHERE location_id = NEW.location_id AND item_id = NEW.item_id;

        IF v_current_qty IS NULL THEN
            INSERT INTO inventory_levels (
                location_id, item_id, quantity_available, created_at, updated_at
            )
            VALUES (
                NEW.location_id, NEW.item_id,
                CASE WHEN NEW.is_inbound THEN NEW.quantity_change
                     ELSE -NEW.quantity_change END,
                NOW(), NOW()
            );
        ELSE
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
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_inventory_transaction ON inventory_transactions",
    """
    CREATE TRIGGER trg_inventory_transaction
        AFTER INSERT ON inventory_transactions
        FOR EACH ROW
        EXECUTE FUNCTION update_inventory_on_transaction()
    """,

    # -------------------------------------------------------------------------
    # 4. AUTO-RESOLVE INVENTORY ALERTS
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION auto_resolve_inventory_alerts()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.quantity_available > COALESCE(NEW.reorder_point, 0)
           AND NEW.quantity_available > COALESCE(NEW.safety_stock, 0)
           AND NEW.quantity_available > 0 THEN
            UPDATE inventory_alerts
            SET is_resolved = TRUE,
                resolved_at = NOW(),
                resolution_notes = 'Auto-resolved: Stock replenished above threshold'
            WHERE inventory_level_id = NEW.id
              AND alert_type IN ('low_stock', 'critical', 'out_of_stock')
              AND is_resolved = FALSE;
        END IF;

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
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_auto_resolve_alerts ON inventory_levels",
    """
    CREATE TRIGGER trg_auto_resolve_alerts
        AFTER UPDATE OF quantity_available ON inventory_levels
        FOR EACH ROW
        EXECUTE FUNCTION auto_resolve_inventory_alerts()
    """,

    # -------------------------------------------------------------------------
    # 5. UPDATE_UPDATED_AT_COLUMN — alias for order_operations tables
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS update_order_returns_updated_at ON order_returns",
    """
    CREATE TRIGGER update_order_returns_updated_at
        BEFORE UPDATE ON order_returns
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """,

    "DROP TRIGGER IF EXISTS update_order_exchanges_updated_at ON order_exchanges",
    """
    CREATE TRIGGER update_order_exchanges_updated_at
        BEFORE UPDATE ON order_exchanges
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """,

    "DROP TRIGGER IF EXISTS update_order_price_adjustments_updated_at ON order_price_adjustments",
    """
    CREATE TRIGGER update_order_price_adjustments_updated_at
        BEFORE UPDATE ON order_price_adjustments
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """,

    # -------------------------------------------------------------------------
    # 6. SYNC RETURN STATUS → order_details
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION sync_order_detail_return_status()
    RETURNS TRIGGER AS $$
    BEGIN
        UPDATE order_details
        SET return_status      = NEW.return_status,
            returned_quantity  = NEW.returned_quantity,
            updated_at         = NOW()
        WHERE detail_id = NEW.order_detail_id;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS sync_return_status_trigger ON order_returns",
    """
    CREATE TRIGGER sync_return_status_trigger
        AFTER INSERT OR UPDATE ON order_returns
        FOR EACH ROW
        EXECUTE FUNCTION sync_order_detail_return_status()
    """,

    # -------------------------------------------------------------------------
    # 7. AUTO-CALCULATE value_difference FOR EXCHANGES
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION calculate_exchange_value_difference()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.value_difference = COALESCE(NEW.new_value, 0) - COALESCE(NEW.original_value, 0);
        IF NEW.value_difference = 0 THEN
            NEW.adjustment_status = 'not_applicable';
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS calc_exchange_value_diff_trigger ON order_exchanges",
    """
    CREATE TRIGGER calc_exchange_value_diff_trigger
        BEFORE INSERT OR UPDATE ON order_exchanges
        FOR EACH ROW
        EXECUTE FUNCTION calculate_exchange_value_difference()
    """,

    # -------------------------------------------------------------------------
    # 8. AUTO-CALCULATE final_amount FOR PRICE ADJUSTMENTS
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION calculate_price_adjustment_final()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.final_amount = COALESCE(NEW.original_amount, 0) + COALESCE(NEW.adjustment_amount, 0);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS calc_price_adjustment_final_trigger ON order_price_adjustments",
    """
    CREATE TRIGGER calc_price_adjustment_final_trigger
        BEFORE INSERT OR UPDATE ON order_price_adjustments
        FOR EACH ROW
        EXECUTE FUNCTION calculate_price_adjustment_final()
    """,

    # -------------------------------------------------------------------------
    # 9. GENERATE LOCATION DISPLAY CODE — fires BEFORE INSERT on inventory_location
    #
    # WHY: The Python property `full_location_code` only works in-memory.
    # A persisted `display_code` column enables SQL-level WHERE / ORDER BY
    # on the human-readable location address (e.g. "A1-Z1-A01-R5-B12").
    #
    # Uses CONCAT_WS('-', ...) which skips NULLs automatically, and NULLIF
    # to treat empty strings as NULL so they are also skipped.
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION generate_location_display_code()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.display_code = CONCAT_WS(
            '-',
            NULLIF(NEW.section, ''),
            NULLIF(NEW.zone, ''),
            NULLIF(NEW.aisle, ''),
            NULLIF(NEW.rack, ''),
            NULLIF(NEW.bin, '')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_generate_display_code ON inventory_location",
    """
    CREATE TRIGGER trg_generate_display_code
        BEFORE INSERT ON inventory_location
        FOR EACH ROW
        EXECUTE FUNCTION generate_location_display_code()
    """,

    # -------------------------------------------------------------------------
    # 10. ITEMS HISTORY AUDIT TRAIL — fires AFTER INSERT on items
    #
    # WHY: Ensures every new item (including bundles) gets an automatic
    # audit trail record in items_history with operation = 'INSERT'.
    # The snapshot_data captures the full initial state of the new item.
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION insert_items_history_on_create()
    RETURNS TRIGGER AS $$
    BEGIN
        INSERT INTO items_history (
            reference_id,
            timestamp,
            changed_by_user_id,
            operation,
            snapshot_data
        )
        VALUES (
            NEW.item_id,
            NOW(),
            NULL,
            'INSERT',
            jsonb_build_object(
                'item_name',      NEW.item_name,
                'master_sku',     NEW.master_sku,
                'sku_name',       NEW.sku_name,
                'item_type_id',   NEW.item_type_id,
                'category_id',    NEW.category_id,
                'brand_id',       NEW.brand_id,
                'uom_id',         NEW.uom_id,
                'is_active',      NEW.is_active,
                'has_variation',  NEW.has_variation,
                'parent_id',      NEW.parent_id,
                'image_url',      NEW.image_url
            )
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_items_history_on_insert ON items",
    """
    CREATE TRIGGER trg_items_history_on_insert
        AFTER INSERT ON items
        FOR EACH ROW
        EXECUTE FUNCTION insert_items_history_on_create()
    """,

    # -------------------------------------------------------------------------
    # 11. ITEMS HISTORY AUDIT TRAIL — fires AFTER UPDATE on items
    #
    # WHY: Captures the old (pre-update) state in items_history every time an
    # item row is modified.  This covers:
    #   - Metadata edits (name, SKU, brand, category, etc.)
    #   - Soft-delete (deleted_at set → operation = 'SOFT_DELETE')
    #   - Restore  (deleted_at cleared → operation = 'RESTORE')
    #   - Any other column change (operation = 'UPDATE')
    #
    # The snapshot_data stores the NEW values at top level and the OLD
    # (pre-change) values under the "previous_values" key, so the full
    # before/after picture is in a single JSONB document.
    # -------------------------------------------------------------------------
    """
    CREATE OR REPLACE FUNCTION insert_items_history_on_update()
    RETURNS TRIGGER AS $$
    DECLARE
        v_operation VARCHAR(20);
        v_snapshot  JSONB;
    BEGIN
        -- Determine the operation type
        IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
            v_operation := 'SOFT_DELETE';
        ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
            v_operation := 'RESTORE';
        ELSE
            v_operation := 'UPDATE';
        END IF;

        -- Build snapshot: new values at top level, old values nested
        v_snapshot := jsonb_build_object(
            'item_name',      NEW.item_name,
            'master_sku',     NEW.master_sku,
            'sku_name',       NEW.sku_name,
            'item_type_id',   NEW.item_type_id,
            'category_id',    NEW.category_id,
            'brand_id',       NEW.brand_id,
            'uom_id',         NEW.uom_id,
            'is_active',      NEW.is_active,
            'has_variation',  NEW.has_variation,
            'parent_id',      NEW.parent_id,
            'image_url',      NEW.image_url,
            'deleted_at',     NEW.deleted_at,
            'deleted_by',     NEW.deleted_by,
            'previous_values', jsonb_build_object(
                'item_name',      OLD.item_name,
                'master_sku',     OLD.master_sku,
                'sku_name',       OLD.sku_name,
                'item_type_id',   OLD.item_type_id,
                'category_id',    OLD.category_id,
                'brand_id',       OLD.brand_id,
                'uom_id',         OLD.uom_id,
                'is_active',      OLD.is_active,
                'has_variation',  OLD.has_variation,
                'parent_id',      OLD.parent_id,
                'image_url',      OLD.image_url,
                'deleted_at',     OLD.deleted_at,
                'deleted_by',     OLD.deleted_by
            )
        );

        -- Resolve user ID: prefer session variable (set by app layer),
        -- fall back to deleted_by for soft-delete/restore operations.
        INSERT INTO items_history (
            reference_id,
            timestamp,
            changed_by_user_id,
            operation,
            snapshot_data
        )
        VALUES (
            NEW.item_id,
            NOW(),
            COALESCE(
                NULLIF(current_setting('app.current_user_id', true), '')::INTEGER,
                NEW.deleted_by
            ),
            v_operation,
            v_snapshot
        );

        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,

    "DROP TRIGGER IF EXISTS trg_items_history_on_update ON items",
    """
    CREATE TRIGGER trg_items_history_on_update
        AFTER UPDATE ON items
        FOR EACH ROW
        EXECUTE FUNCTION insert_items_history_on_update()
    """,
]


# =============================================================================
# Public API
# =============================================================================

async def apply_triggers(conn: AsyncConnection) -> None:
    """
    Apply all trigger functions and trigger registrations to the database.

    Idempotent: every function uses CREATE OR REPLACE and every trigger uses
    DROP TRIGGER IF EXISTS, so this can be called on any live DB safely.

    Called by database.init_db_full() so triggers are always in place after
    a fresh DB initialisation without running external SQL files.
    """
    for stmt in _TRIGGER_SQL:
        clean = stmt.strip()
        if clean:
            await conn.execute(text(clean))
    print("[OK] All triggers applied")
