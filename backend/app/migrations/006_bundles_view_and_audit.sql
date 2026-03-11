-- =============================================================================
-- 006_bundles_view_and_audit.sql
--
-- PURPOSE: Prepare the database to distinguish individual items from bundles.
--
-- This script is a REFERENCE ONLY — the canonical implementations live in:
--   - backend/app/models/views.py   (v_bundles view)
--   - backend/app/models/triggers.py (items_history audit trigger)
--   - backend/app/models/seed.py    ("Bundle" item_type seed)
--
-- These Python modules are executed at startup via init_db_full().
-- This SQL file documents the raw SQL for manual inspection / ad-hoc use.
--
-- DATE: 2026-03-09
-- =============================================================================


-- =============================================================================
-- 1. SEED: Add "Bundle" to item_type lookup table
--
-- WHY: Provides a formal item_type classification so items can be explicitly
--      tagged as bundles, enabling frontend filtering (exclude_item_type_id).
-- =============================================================================
INSERT INTO item_type (item_type_name)
VALUES ('Bundle')
ON CONFLICT (item_type_name) DO NOTHING;


-- =============================================================================
-- 2. CONSTRAINT CHECK: master_sku UNIQUE NOT NULL
--
-- WHY: Every item (including bundles) must have a unique, non-null master_sku
--      to serve as the canonical identifier across the system.
--
-- VERIFICATION: The items table already enforces this at the model level:
--   master_sku: str = Field(max_length=100, unique=True, index=True)
--   → DDL: master_sku VARCHAR(100) NOT NULL UNIQUE
--
-- The following query verifies the constraint exists; no ALTER needed:
-- =============================================================================
-- SELECT conname, contype
-- FROM pg_constraint
-- WHERE conrelid = 'items'::regclass
--   AND conname LIKE '%master_sku%';
--
-- Expected output:
--   items_master_sku_key | u   (unique constraint)


-- =============================================================================
-- 3. VIEW: v_bundles — Identify bundles from listing_component
--
-- DEFINITION: A "Bundle" is any listing_id in listing_component that either:
--   (a) has more than one unique item_id, OR
--   (b) has a single item_id with quantity > 1.
--
-- WHY: Enables SQL-level queries to distinguish bundle listings from single-item
--      listings without application logic. Used by reporting views, inventory
--      planning, and the frontend bundle catalog.
-- =============================================================================
CREATE OR REPLACE VIEW v_bundles AS
WITH bundle_candidates AS (
    SELECT
        lc.listing_id,
        COUNT(DISTINCT lc.item_id)       AS distinct_items,
        SUM(lc.quantity)                  AS total_quantity,
        MAX(lc.quantity)                  AS max_component_qty
    FROM listing_component lc
    GROUP BY lc.listing_id
    HAVING COUNT(DISTINCT lc.item_id) > 1
        OR (COUNT(DISTINCT lc.item_id) = 1 AND MAX(lc.quantity) > 1)
)
SELECT
    ps.listing_id,
    ps.platform_sku,
    ps.platform_seller_sku_name,
    p.platform_name,
    s.store_name                         AS seller_name,
    bc.distinct_items                    AS component_count,
    bc.total_quantity                    AS total_bundle_quantity,
    ps.is_active                         AS listing_active,
    ps.created_at                        AS listing_created_at,
    ps.updated_at                        AS listing_updated_at
FROM bundle_candidates bc
JOIN platform_sku ps   ON bc.listing_id  = ps.listing_id
JOIN platform p        ON ps.platform_id = p.platform_id
JOIN seller s          ON ps.seller_id   = s.seller_id;


-- =============================================================================
-- 4. TRIGGER: Auto-insert items_history on item creation (audit trail)
--
-- WHY: Ensures every new item (including bundles) automatically gets an
--      audit trail record in items_history with operation = 'INSERT'.
--      The snapshot_data captures the full initial state of the new item
--      so the creation event is always traceable.
-- =============================================================================

-- 4a. Trigger function
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
$$ LANGUAGE plpgsql;

-- 4b. Trigger registration
DROP TRIGGER IF EXISTS trg_items_history_on_insert ON items;
CREATE TRIGGER trg_items_history_on_insert
    AFTER INSERT ON items
    FOR EACH ROW
    EXECUTE FUNCTION insert_items_history_on_create();


-- =============================================================================
-- 5. VERIFICATION QUERIES (run manually to confirm)
-- =============================================================================

-- 5a. Verify "Bundle" item_type exists
-- SELECT * FROM item_type WHERE item_type_name = 'Bundle';

-- 5b. Verify v_bundles view works
-- SELECT * FROM v_bundles LIMIT 10;

-- 5c. Verify audit trigger fires on new item insert
-- INSERT INTO items (item_name, master_sku) VALUES ('Test Bundle', 'TEST-BUNDLE-001');
-- SELECT * FROM items_history WHERE reference_id = (SELECT item_id FROM items WHERE master_sku = 'TEST-BUNDLE-001');

-- 5d. Verify master_sku uniqueness constraint
-- INSERT INTO items (item_name, master_sku) VALUES ('Duplicate', 'TEST-BUNDLE-001');
-- Expected: ERROR: duplicate key value violates unique constraint "items_master_sku_key"
