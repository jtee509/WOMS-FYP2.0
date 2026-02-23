# WOMS Database Migrations

WOMS uses two migration systems:

1. **Alembic (Python)** – Schema changes (tables, columns). Located in `alembic/versions/`.
2. **SQL scripts** – Triggers, indexes, views, seed data. Located in this `migrations/` folder.

## Quick Start (One Command)

Run everything at once using Python:

```bash
# Full initialization: tables + triggers + indexes + views
python -c "import asyncio; from app.database import init_db_full; asyncio.run(init_db_full())"

# Or for a full reset (WARNING: deletes all data!)
python -c "import asyncio; from app.database import reset_db_full; asyncio.run(reset_db_full())"
```

## Alternative: Manual Migration Order

If you prefer running scripts manually:

```bash
# 1. Run Alembic migrations (schema: tables, columns)
alembic upgrade head

# 2. Run SQL migrations (triggers, indexes, views, seed data)
python -c "import asyncio; from app.database import run_migrations; asyncio.run(run_migrations())"

# Or run SQL scripts directly with psql
psql -d woms_db -f migrations/001_triggers.sql
psql -d woms_db -f migrations/002_indexes.sql
psql -d woms_db -f migrations/003_views.sql
psql -d woms_db -f migrations/004_seed_data.sql
```

## Alembic Schema Migrations (Python)

Schema changes (new tables, new columns) are managed by Alembic in `alembic/versions/`:

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (after changing models)
alembic revision --autogenerate -m "add_my_feature"

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current
```

Recent schema migrations include:
- `b2c3d4e5f6a7` – Add test dataset columns (platform address/postcode, seller company_name, items sku_name/product_number)

## Available Python Functions

```python
from app.database import (
    init_db,          # Create tables only
    run_migrations,   # Run SQL files only (triggers, indexes, views)
    init_db_full,     # Create tables + run SQL migrations
    reset_db_full,    # Drop all, recreate tables + run SQL migrations
)
```

## Files (SQL Migrations)

| File | Description |
|------|-------------|
| `001_triggers.sql` | PostgreSQL trigger functions for auto-timestamps, inventory alerts, and transaction calculations |
| `002_indexes.sql` | GIN indexes for JSONB fields and composite indexes for common query patterns |
| `003_views.sql` | Reporting views for inventory status, order fulfillment, and dashboards |
| `004_seed_data.sql` | Initial seed data for lookup tables (action_type, status, roles, etc.) |

## Trigger Functions

### 1. `update_timestamp()`
Automatically updates `updated_at` column on row modification.

**Applied to:** items, orders, order_details, warehouse, inventory_levels, platform_sku, seller_warehouses

### 2. `check_inventory_threshold()`
Monitors inventory levels and creates alerts when:
- Stock reaches zero (`out_of_stock`)
- Stock falls below safety stock (`critical`)
- Stock falls below reorder point (`low_stock`)
- Stock exceeds maximum (`overstock`)

**Triggered by:** Updates to `inventory_levels.quantity_available`

### 3. `update_inventory_on_transaction()`
Automatically updates inventory levels when transactions are recorded.

**Triggered by:** Inserts to `inventory_transactions`

### 4. `auto_resolve_inventory_alerts()`
Automatically resolves alerts when stock is replenished above thresholds.

**Triggered by:** Updates to `inventory_levels.quantity_available`

## Key Indexes

### JSONB GIN Indexes
Enable efficient queries on JSONB fields:
- `idx_items_variations_gin` - Query item variations
- `idx_orders_platform_raw_gin` - Search platform raw data
- `idx_order_details_sku_gin` - Search platform SKU data

### Composite Indexes
Optimize common query patterns:
- `idx_orders_platform_store` - Orders by platform and store
- `idx_orders_warehouse_status` - Fulfillment queries
- `idx_inventory_item_location` - Stock lookups

### Partial Indexes
Filter-specific optimizations:
- `idx_items_active` - Only non-deleted items
- `idx_orders_pending` - Only pending orders
- `idx_alerts_unresolved` - Only active alerts

## Reporting Views

| View | Purpose |
|------|---------|
| `v_inventory_status` | Real-time inventory with stock status and expiry tracking |
| `v_order_fulfillment` | Order summary with aggregated amounts and fulfillment status |
| `v_seller_warehouse_routing` | Seller-warehouse assignments with statistics |
| `v_platform_import_status` | Raw import processing status |
| `v_active_inventory_alerts` | Active alerts dashboard with priority ranking |
| `v_warehouse_summary` | Warehouse statistics and capacity overview |
| `v_order_line_items` | Detailed order line items with SKU translation |

## Verification

After running the scripts, verify installation:

```sql
-- List all triggers
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 'public';

-- List all indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'public';

-- List all views
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'VIEW';
```

## Development Notes

- Triggers use `DROP TRIGGER IF EXISTS` for idempotency
- Indexes use `DROP INDEX IF EXISTS` for safe re-runs
- Views use `CREATE OR REPLACE VIEW` for updates without dropping

## Performance Considerations

- GIN indexes with `jsonb_path_ops` optimize containment queries (`@>`)
- Partial indexes reduce index size for common filtered queries
- Consider refreshing materialized views for heavy reporting (see `003_views.sql`)
