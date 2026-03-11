"""
WOMS Database Views (Python Module)

All 12 PostgreSQL reporting views are defined here as Python string constants.
The single entry-point `apply_views(conn)` executes every CREATE OR REPLACE
VIEW statement against an open async connection.

WHY Python instead of migrations/003_views.sql:
- No external .sql file dependency — everything lives in the Python codebase.
- `apply_views()` is called from database.init_db_full() so views are
  available immediately after a fresh DB initialisation.
- CREATE OR REPLACE VIEW makes every call idempotent.

Views defined:
  1.  v_inventory_status          — real-time stock levels, expiry, alerts
  2.  v_order_fulfillment         — order summary with aggregated line items
  3.  v_seller_warehouse_routing  — seller→warehouse assignments with stats
  4.  v_platform_import_status    — raw import processing status
  5.  v_active_inventory_alerts   — active alert dashboard with priority rank
  6.  v_warehouse_summary         — warehouse capacity and resource overview
  7.  v_order_line_items          — detailed line items with SKU translation
  8.  v_order_returns             — return workflow tracking
  9.  v_order_exchanges           — exchange details with value adjustments
  10. v_order_modifications       — order modification audit trail
  11. v_order_price_adjustments   — price adjustment tracking
  12. v_order_operations_summary  — complete order operations overview
  13. v_bundles                    — bundle listings identified from listing_component
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


# =============================================================================
# View SQL statements — order matters (dependent views last)
# =============================================================================

_VIEW_SQL: list[tuple[str, str]] = [

    # -------------------------------------------------------------------------
    # 1. INVENTORY STATUS
    # -------------------------------------------------------------------------
    ("v_inventory_status", """
    CREATE OR REPLACE VIEW v_inventory_status AS
    SELECT
        w.id                                                       AS warehouse_id,
        w.warehouse_name,
        i.item_id,
        i.item_name,
        i.master_sku,
        il.id                                                      AS inventory_level_id,
        il.location_id,
        CONCAT_WS('-', loc.section, loc.zone, loc.aisle, loc.rack, loc.bin) AS location_code,
        il.quantity_available,
        il.reorder_point,
        il.safety_stock,
        il.max_stock,
        CASE
            WHEN il.quantity_available = 0                                    THEN 'OUT_OF_STOCK'
            WHEN il.quantity_available <= COALESCE(il.safety_stock, 0)        THEN 'CRITICAL'
            WHEN il.quantity_available <= COALESCE(il.reorder_point, 0)       THEN 'LOW'
            WHEN il.max_stock IS NOT NULL
             AND il.quantity_available >= il.max_stock                        THEN 'OVERSTOCK'
            ELSE 'OK'
        END                                                        AS stock_status,
        il.alert_triggered_at,
        il.alert_acknowledged,
        sl.id                                                      AS lot_id,
        sl.batch_number,
        sl.serial_number,
        sl.expiry_date,
        CASE
            WHEN sl.expiry_date IS NOT NULL
             AND sl.expiry_date < CURRENT_DATE                                THEN 'EXPIRED'
            WHEN sl.expiry_date IS NOT NULL
             AND sl.expiry_date < CURRENT_DATE + INTERVAL '30 days'          THEN 'EXPIRING_SOON'
            ELSE 'OK'
        END                                                        AS expiry_status,
        it.inventory_type_name                                     AS location_type,
        c.category_name,
        b.brand_name,
        il.updated_at                                              AS last_updated
    FROM inventory_levels il
    JOIN items i            ON il.item_id        = i.item_id
    JOIN inventory_location loc ON il.location_id = loc.id
    JOIN warehouse w        ON loc.warehouse_id   = w.id
    LEFT JOIN stock_lots sl ON il.lot_id          = sl.id
    LEFT JOIN inventory_type it ON loc.inventory_type_id = it.inventory_type_id
    LEFT JOIN category c    ON i.category_id      = c.category_id
    LEFT JOIN brand b       ON i.brand_id         = b.brand_id
    WHERE i.deleted_at IS NULL
      AND w.is_active = TRUE
    """),

    # -------------------------------------------------------------------------
    # 2. ORDER FULFILLMENT
    # -------------------------------------------------------------------------
    ("v_order_fulfillment", """
    CREATE OR REPLACE VIEW v_order_fulfillment AS
    SELECT
        o.order_id,
        o.platform_order_id,
        p.platform_id,
        p.platform_name,
        s.seller_id,
        s.store_name,
        o.recipient_name,
        o.phone_number,
        o.shipping_address,
        o.shipping_postcode,
        o.shipping_state,
        o.country,
        o.order_status,
        w.id                                                       AS warehouse_id,
        w.warehouse_name                                           AS assigned_warehouse,
        COUNT(DISTINCT od.detail_id)                               AS total_line_items,
        SUM(od.quantity)                                           AS total_quantity,
        SUM(od.paid_amount)                                        AS total_paid_amount,
        SUM(od.shipping_fee)                                       AS total_shipping_fee,
        SUM(od.discount)                                           AS total_discount,
        SUM(od.paid_amount - od.discount)                          AS net_amount,
        STRING_AGG(DISTINCT od.tracking_number, ', ')              AS tracking_numbers,
        STRING_AGG(DISTINCT od.courier_type,    ', ')              AS courier_types,
        STRING_AGG(DISTINCT od.tracking_source, ', ')              AS tracking_sources,
        STRING_AGG(DISTINCT od.fulfillment_status, ', ')           AS fulfillment_statuses,
        CASE
            WHEN COUNT(*) FILTER (WHERE od.fulfillment_status = 'pending')   = COUNT(*) THEN 'PENDING'
            WHEN COUNT(*) FILTER (WHERE od.fulfillment_status = 'delivered') = COUNT(*) THEN 'COMPLETED'
            WHEN COUNT(*) FILTER (WHERE od.fulfillment_status = 'shipped')   > 0        THEN 'SHIPPED'
            WHEN COUNT(*) FILTER (WHERE od.fulfillment_status = 'packed')    > 0        THEN 'PACKING'
            WHEN COUNT(*) FILTER (WHERE od.fulfillment_status = 'picked')    > 0        THEN 'PICKING'
            ELSE 'IN_PROGRESS'
        END                                                        AS overall_fulfillment_status,
        o.order_date,
        o.created_at,
        o.updated_at
    FROM orders o
    JOIN platform p     ON o.platform_id          = p.platform_id
    JOIN seller s       ON o.store_id             = s.seller_id
    LEFT JOIN warehouse w ON o.assigned_warehouse_id = w.id
    JOIN order_details od ON o.order_id           = od.order_id
    GROUP BY
        o.order_id, o.platform_order_id,
        p.platform_id, p.platform_name,
        s.seller_id, s.store_name,
        o.recipient_name, o.phone_number,
        o.shipping_address, o.shipping_postcode, o.shipping_state, o.country,
        o.order_status,
        w.id, w.warehouse_name,
        o.order_date, o.created_at, o.updated_at
    """),

    # -------------------------------------------------------------------------
    # 3. SELLER WAREHOUSE ROUTING
    # -------------------------------------------------------------------------
    ("v_seller_warehouse_routing", """
    CREATE OR REPLACE VIEW v_seller_warehouse_routing AS
    SELECT
        s.seller_id,
        s.store_name,
        p.platform_name,
        sw.id                                                      AS assignment_id,
        w.id                                                       AS warehouse_id,
        w.warehouse_name,
        sw.is_primary,
        sw.priority,
        sw.is_active                                               AS assignment_active,
        s.is_active                                                AS seller_active,
        w.is_active                                                AS warehouse_active,
        w.address->>'city'                                         AS warehouse_city,
        w.address->>'state'                                        AS warehouse_state,
        (
            SELECT COUNT(*)
            FROM orders o
            WHERE o.store_id              = s.seller_id
              AND o.assigned_warehouse_id = w.id
        )                                                          AS total_orders_fulfilled,
        sw.created_at                                              AS assigned_since,
        sw.updated_at                                              AS last_updated
    FROM seller_warehouses sw
    JOIN seller s       ON sw.seller_id   = s.seller_id
    JOIN warehouse w    ON sw.warehouse_id = w.id
    LEFT JOIN platform p ON s.platform_id  = p.platform_id
    ORDER BY s.seller_id, sw.priority, sw.is_primary DESC
    """),

    # -------------------------------------------------------------------------
    # 4. PLATFORM IMPORT STATUS
    # -------------------------------------------------------------------------
    ("v_platform_import_status", """
    CREATE OR REPLACE VIEW v_platform_import_status AS
    SELECT
        pri.id                                                     AS import_id,
        p.platform_name,
        s.store_name,
        pri.import_source,
        pri.import_filename,
        pri.import_batch_id,
        pri.status,
        pri.error_message,
        pri.normalized_order_id,
        o.platform_order_id                                        AS normalized_to_order,
        o.order_status                                             AS normalized_order_status,
        pri.raw_data->>'order_id'                                  AS raw_order_id,
        pri.raw_data->>'order_status'                              AS raw_order_status,
        pri.raw_data->>'total_amount'                              AS raw_total_amount,
        pri.created_at                                             AS imported_at,
        pri.processed_at,
        EXTRACT(EPOCH FROM (COALESCE(pri.processed_at, NOW()) - pri.created_at)) AS processing_seconds
    FROM platform_raw_imports pri
    JOIN platform p     ON pri.platform_id = p.platform_id
    LEFT JOIN seller s  ON pri.seller_id   = s.seller_id
    LEFT JOIN orders o  ON pri.normalized_order_id = o.order_id
    ORDER BY pri.created_at DESC
    """),

    # -------------------------------------------------------------------------
    # 5. ACTIVE INVENTORY ALERTS
    # -------------------------------------------------------------------------
    ("v_active_inventory_alerts", """
    CREATE OR REPLACE VIEW v_active_inventory_alerts AS
    SELECT
        ia.id                                                      AS alert_id,
        ia.alert_type,
        ia.alert_message,
        ia.current_quantity,
        ia.threshold_quantity,
        w.id                                                       AS warehouse_id,
        w.warehouse_name,
        i.item_id,
        i.item_name,
        i.master_sku,
        il.location_id,
        CONCAT_WS('-', loc.section, loc.zone, loc.aisle, loc.rack, loc.bin) AS location_code,
        il.reorder_point,
        il.safety_stock,
        ia.created_at                                              AS alert_created_at,
        EXTRACT(EPOCH FROM (NOW() - ia.created_at)) / 3600        AS hours_since_alert,
        CASE
            WHEN ia.alert_type = 'out_of_stock' THEN 1
            WHEN ia.alert_type = 'critical'     THEN 2
            WHEN ia.alert_type = 'low_stock'    THEN 3
            WHEN ia.alert_type = 'overstock'    THEN 4
            ELSE 5
        END                                                        AS priority_rank
    FROM inventory_alerts ia
    JOIN warehouse w        ON ia.warehouse_id       = w.id
    JOIN items i            ON ia.item_id            = i.item_id
    JOIN inventory_levels il ON ia.inventory_level_id = il.id
    JOIN inventory_location loc ON il.location_id    = loc.id
    WHERE ia.is_resolved = FALSE
      AND i.deleted_at   IS NULL
    ORDER BY priority_rank, ia.created_at
    """),

    # -------------------------------------------------------------------------
    # 6. WAREHOUSE SUMMARY
    # -------------------------------------------------------------------------
    ("v_warehouse_summary", """
    CREATE OR REPLACE VIEW v_warehouse_summary AS
    SELECT
        w.id                                                       AS warehouse_id,
        w.warehouse_name,
        w.address->>'city'                                         AS city,
        w.address->>'state'                                        AS state,
        w.is_active,
        COUNT(DISTINCT loc.id)                                     AS total_locations,
        COUNT(DISTINCT il.id)                                      AS locations_with_stock,
        COUNT(DISTINCT il.item_id)                                 AS unique_items,
        SUM(il.quantity_available)                                 AS total_quantity,
        COUNT(DISTINCT CASE WHEN ia.is_resolved = FALSE THEN ia.id END) AS active_alerts,
        COUNT(DISTINCT sw.seller_id)                               AS assigned_sellers,
        COUNT(DISTINCT o.order_id)
            FILTER (WHERE o.order_status = 'pending')              AS pending_orders,
        COUNT(DISTINCT d.driver_id)                                AS assigned_drivers,
        COUNT(DISTINCT l.plate_number)                             AS assigned_lorries
    FROM warehouse w
    LEFT JOIN inventory_location loc ON w.id = loc.warehouse_id
    LEFT JOIN inventory_levels il    ON loc.id = il.location_id
    LEFT JOIN inventory_alerts ia    ON w.id = ia.warehouse_id
    LEFT JOIN seller_warehouses sw   ON w.id = sw.warehouse_id AND sw.is_active = TRUE
    LEFT JOIN orders o               ON w.id = o.assigned_warehouse_id
    LEFT JOIN drivers d              ON w.id = d.warehouse_id AND d.is_active = TRUE
    LEFT JOIN lorries l              ON w.id = l.warehouse_id AND l.is_active = TRUE
    GROUP BY w.id, w.warehouse_name, w.address, w.is_active
    """),

    # -------------------------------------------------------------------------
    # 7. ORDER LINE ITEMS
    # -------------------------------------------------------------------------
    ("v_order_line_items", """
    CREATE OR REPLACE VIEW v_order_line_items AS
    SELECT
        o.order_id,
        o.platform_order_id,
        p.platform_name,
        s.store_name,
        od.detail_id,
        od.platform_sku_data->>'platform_sku'  AS platform_sku,
        od.platform_sku_data->>'sku_name'      AS sku_name,
        od.platform_sku_data->>'variation'     AS variation,
        i.item_id                              AS resolved_item_id,
        i.item_name                            AS resolved_item_name,
        i.master_sku                           AS resolved_master_sku,
        od.quantity,
        od.paid_amount,
        od.shipping_fee,
        od.discount,
        (od.paid_amount - od.discount)         AS net_amount,
        od.courier_type,
        od.tracking_number,
        od.tracking_source,
        od.fulfillment_status,
        w.warehouse_name                       AS assigned_warehouse,
        o.order_status,
        o.order_date,
        od.created_at,
        od.updated_at
    FROM order_details od
    JOIN orders o       ON od.order_id          = o.order_id
    JOIN platform p     ON o.platform_id        = p.platform_id
    JOIN seller s       ON o.store_id           = s.seller_id
    LEFT JOIN items i   ON od.resolved_item_id  = i.item_id
    LEFT JOIN warehouse w ON o.assigned_warehouse_id = w.id
    """),

    # -------------------------------------------------------------------------
    # 8. ORDER RETURNS
    # -------------------------------------------------------------------------
    ("v_order_returns", """
    CREATE OR REPLACE VIEW v_order_returns AS
    SELECT
        r.id                                                       AS return_id,
        r.order_id,
        o.platform_order_id,
        p.platform_name,
        s.store_name,
        r.order_detail_id,
        od.platform_sku_data->>'platform_sku'  AS platform_sku,
        i.item_name                            AS resolved_item_name,
        i.master_sku,
        r.return_type,
        rr.reason_code                         AS return_reason_code,
        rr.reason_name                         AS return_reason,
        r.return_status,
        r.returned_quantity,
        r.inspection_status,
        r.restock_decision,
        r.restocked_quantity,
        r.platform_return_reference,
        r.requested_at,
        r.approved_at,
        r.received_at,
        r.completed_at,
        EXTRACT(EPOCH FROM (COALESCE(r.completed_at, NOW()) - r.requested_at)) / 86400 AS days_since_request,
        u.username                             AS initiated_by,
        r.notes,
        w.warehouse_name                       AS assigned_warehouse
    FROM order_returns r
    JOIN orders o       ON r.order_id           = o.order_id
    JOIN platform p     ON o.platform_id        = p.platform_id
    JOIN seller s       ON o.store_id           = s.seller_id
    JOIN order_details od ON r.order_detail_id  = od.detail_id
    LEFT JOIN items i   ON od.resolved_item_id  = i.item_id
    LEFT JOIN return_reason rr ON r.return_reason_id = rr.reason_id
    LEFT JOIN users u   ON r.initiated_by_user_id = u.user_id
    LEFT JOIN warehouse w ON o.assigned_warehouse_id = w.id
    """),

    # -------------------------------------------------------------------------
    # 9. ORDER EXCHANGES
    # -------------------------------------------------------------------------
    ("v_order_exchanges", """
    CREATE OR REPLACE VIEW v_order_exchanges AS
    SELECT
        e.id                                                       AS exchange_id,
        e.original_order_id,
        o_orig.platform_order_id                                   AS original_platform_order_id,
        p.platform_name,
        s.store_name,
        e.original_detail_id,
        od_orig.platform_sku_data->>'platform_sku'                 AS original_platform_sku,
        i_orig.item_name                                           AS original_item_name,
        i_orig.master_sku                                          AS original_master_sku,
        e.exchange_type,
        er.reason_code                                             AS exchange_reason_code,
        er.reason_name                                             AS exchange_reason,
        e.exchange_status,
        e.new_order_id,
        o_new.platform_order_id                                    AS new_platform_order_id,
        e.new_detail_id,
        e.exchanged_item_id,
        i_new.item_name                                            AS exchanged_item_name,
        i_new.master_sku                                           AS exchanged_master_sku,
        e.exchanged_quantity,
        e.original_value,
        e.new_value,
        e.value_difference,
        e.adjustment_status,
        e.return_id,
        r.return_status                                            AS linked_return_status,
        e.platform_exchange_reference,
        e.requested_at,
        e.approved_at,
        e.completed_at,
        EXTRACT(EPOCH FROM (COALESCE(e.completed_at, NOW()) - e.requested_at)) / 86400 AS days_since_request,
        u_init.username                                            AS initiated_by,
        u_appr.username                                            AS approved_by,
        e.notes,
        w.warehouse_name                                           AS assigned_warehouse
    FROM order_exchanges e
    JOIN orders o_orig      ON e.original_order_id  = o_orig.order_id
    JOIN platform p         ON o_orig.platform_id   = p.platform_id
    JOIN seller s           ON o_orig.store_id      = s.seller_id
    JOIN order_details od_orig ON e.original_detail_id = od_orig.detail_id
    LEFT JOIN items i_orig  ON od_orig.resolved_item_id = i_orig.item_id
    LEFT JOIN orders o_new  ON e.new_order_id        = o_new.order_id
    LEFT JOIN items i_new   ON e.exchanged_item_id   = i_new.item_id
    LEFT JOIN exchange_reason er ON e.exchange_reason_id = er.reason_id
    LEFT JOIN order_returns r ON e.return_id          = r.id
    LEFT JOIN users u_init  ON e.initiated_by_user_id = u_init.user_id
    LEFT JOIN users u_appr  ON e.approved_by_user_id  = u_appr.user_id
    LEFT JOIN warehouse w   ON o_orig.assigned_warehouse_id = w.id
    """),

    # -------------------------------------------------------------------------
    # 10. ORDER MODIFICATIONS
    # -------------------------------------------------------------------------
    ("v_order_modifications", """
    CREATE OR REPLACE VIEW v_order_modifications AS
    SELECT
        m.id                                                       AS modification_id,
        m.order_id,
        o.platform_order_id,
        p.platform_name,
        s.store_name,
        m.order_detail_id,
        od.platform_sku_data->>'platform_sku'  AS platform_sku,
        m.modification_type,
        m.field_changed,
        m.old_value,
        m.new_value,
        m.modification_reason,
        m.related_exchange_id,
        e.exchange_type                        AS related_exchange_type,
        m.related_return_id,
        r.return_type                          AS related_return_type,
        m.modified_at,
        u.username                             AS modified_by,
        o.order_status,
        o.order_date
    FROM order_modifications m
    JOIN orders o       ON m.order_id           = o.order_id
    JOIN platform p     ON o.platform_id        = p.platform_id
    JOIN seller s       ON o.store_id           = s.seller_id
    LEFT JOIN order_details od ON m.order_detail_id = od.detail_id
    LEFT JOIN order_exchanges e ON m.related_exchange_id = e.id
    LEFT JOIN order_returns r   ON m.related_return_id   = r.id
    LEFT JOIN users u   ON m.modified_by_user_id = u.user_id
    ORDER BY m.modified_at DESC
    """),

    # -------------------------------------------------------------------------
    # 11. ORDER PRICE ADJUSTMENTS
    # -------------------------------------------------------------------------
    ("v_order_price_adjustments", """
    CREATE OR REPLACE VIEW v_order_price_adjustments AS
    SELECT
        pa.id                                                      AS adjustment_id,
        pa.order_id,
        o.platform_order_id,
        p.platform_name,
        s.store_name,
        pa.order_detail_id,
        od.platform_sku_data->>'platform_sku'  AS platform_sku,
        i.item_name,
        pa.adjustment_type,
        pa.adjustment_reason,
        pa.original_amount,
        pa.adjustment_amount,
        pa.final_amount,
        pa.status,
        pa.related_exchange_id,
        e.exchange_type                        AS related_exchange_type,
        pa.related_modification_id,
        m.modification_type                    AS related_modification_type,
        pa.created_at,
        pa.applied_at,
        u_create.username                      AS created_by,
        u_apply.username                       AS applied_by
    FROM order_price_adjustments pa
    JOIN orders o           ON pa.order_id          = o.order_id
    JOIN platform p         ON o.platform_id        = p.platform_id
    JOIN seller s           ON o.store_id           = s.seller_id
    LEFT JOIN order_details od ON pa.order_detail_id = od.detail_id
    LEFT JOIN items i           ON od.resolved_item_id = i.item_id
    LEFT JOIN order_exchanges e ON pa.related_exchange_id = e.id
    LEFT JOIN order_modifications m ON pa.related_modification_id = m.id
    LEFT JOIN users u_create ON pa.created_by_user_id = u_create.user_id
    LEFT JOIN users u_apply  ON pa.applied_by_user_id  = u_apply.user_id
    """),

    # -------------------------------------------------------------------------
    # 12. ORDER OPERATIONS SUMMARY
    # -------------------------------------------------------------------------
    ("v_order_operations_summary", """
    CREATE OR REPLACE VIEW v_order_operations_summary AS
    SELECT
        o.order_id,
        o.platform_order_id,
        p.platform_name,
        s.store_name,
        o.order_status,
        o.cancellation_status,
        COUNT(DISTINCT r.id)                                       AS total_returns,
        COUNT(DISTINCT r.id)
            FILTER (WHERE r.return_status NOT IN ('completed','cancelled','rejected'))
                                                                   AS active_returns,
        COUNT(DISTINCT e.id)                                       AS total_exchanges,
        COUNT(DISTINCT e.id)
            FILTER (WHERE e.exchange_status NOT IN ('completed','cancelled'))
                                                                   AS active_exchanges,
        COUNT(DISTINCT m.id)                                       AS total_modifications,
        COUNT(DISTINCT pa.id)                                      AS total_price_adjustments,
        SUM(CASE WHEN pa.status = 'applied' THEN pa.adjustment_amount ELSE 0 END)
                                                                   AS total_adjustment_applied,
        SUM(od.paid_amount)                                        AS original_order_total,
        SUM(od.discount)                                           AS total_discounts,
        o.order_date,
        o.created_at,
        o.updated_at
    FROM orders o
    JOIN platform p     ON o.platform_id        = p.platform_id
    JOIN seller s       ON o.store_id           = s.seller_id
    JOIN order_details od ON o.order_id         = od.order_id
    LEFT JOIN order_returns r   ON o.order_id   = r.order_id
    LEFT JOIN order_exchanges e ON o.order_id   = e.original_order_id
    LEFT JOIN order_modifications m ON o.order_id = m.order_id
    LEFT JOIN order_price_adjustments pa ON o.order_id = pa.order_id
    GROUP BY
        o.order_id, o.platform_order_id,
        p.platform_name, s.store_name,
        o.order_status, o.cancellation_status,
        o.order_date, o.created_at, o.updated_at
    """),

    # -------------------------------------------------------------------------
    # 13. BUNDLES VIEW
    #
    # WHY: Distinguishes bundles from individual items at the database level.
    # A "Bundle" is any listing_id in listing_component that either:
    #   (a) has more than one unique item_id, OR
    #   (b) has a single item_id with quantity > 1.
    #
    # Returns one row per bundle listing with component count, total quantity,
    # and the resolved item details from the items table.
    # -------------------------------------------------------------------------
    ("v_bundles", """
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
    JOIN seller s          ON ps.seller_id   = s.seller_id
    """),
]


# =============================================================================
# Public API
# =============================================================================

async def apply_views(conn: AsyncConnection) -> None:
    """
    Apply all reporting views to the database.

    Uses CREATE OR REPLACE VIEW so each call is idempotent.
    Called by database.init_db_full() after table creation.
    """
    for view_name, sql in _VIEW_SQL:
        await conn.execute(text(sql.strip()))
    print(f"[OK] {len(_VIEW_SQL)} views applied")
