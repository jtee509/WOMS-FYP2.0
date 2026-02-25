# Order Import Database – Implementation Summary

**Date:** 2026-02-21  
**Plan:** [02_order_import_database.plan.md](02_order_import_database.plan.md)

---

## What Was Implemented

### 1. Alembic Migration

**File:** `alembic/versions/20260220_1600_00_c4d5e6f7a8b9_create_order_import_schema.py`

- **Schema:** `order_import` schema in `woms_db`
- **Tables:**
  - `order_import_raw` – Original copies of every Excel row (JSONB)
  - `order_import_staging` – Normalized view for processing
- **Foreign keys:** `seller_id` → `seller.seller_id`; `raw_import_id` → `order_import_raw.id`; `normalized_order_id` → `orders.order_id`

**Why:** Option B (new schema in same DB) was chosen to keep one connection and allow FK to `seller`.

### 2. SQLModel Models

**File:** `app/models/order_import.py`

- **OrderImportRaw** – Immutable raw row storage with `seller_id`, `platform_source`, `raw_row_data` (JSONB)
- **OrderImportStaging** – Normalized columns for mapping to WOMS, with `raw_import_id` link

**Why:** `raw_import_id` has no FK in the model for cross-schema compatibility; relationship uses `primaryjoin`. The migration adds the FK in the database.

### 3. Model Exports

**File:** `app/models/__init__.py`

- Exported `OrderImportRaw` and `OrderImportStaging` for use in the app.

### 4. Documentation

- **`docs/DATABASE.md`** – Updated with Order Import Module table, column definitions, and schema description
- **`docs/ORDER_IMPORT_DATABASE.md`** – Import flow, seller_id usage, and original-copy preservation

### 5. Test Setup

**File:** `tests/conftest.py`

- Added `CREATE SCHEMA IF NOT EXISTS order_import` before `create_all`
- Added `DROP SCHEMA IF EXISTS order_import CASCADE` in teardown

**Why:** Schema must exist before tables are created; teardown cleans up for next run.

---

## How to Test

```bash
# Run migration
alembic upgrade head

# Run all tests
pytest tests/ -v
```

**Result:** All 42 tests passed.

---

## Original Copy Guarantee

- `order_import_raw` is append-only for imports
- Each Excel row → one `order_import_raw` row with full JSONB snapshot
- `order_import_staging.raw_import_id` points back to the original
- Query: `SELECT s.*, r.raw_row_data FROM order_import.order_import_staging s JOIN order_import.order_import_raw r ON s.raw_import_id = r.id WHERE s.normalized_order_id = ?`

---

## Seller ID Requirement

At import time, the user must select which `seller_id` the file belongs to. This is stored on every row in both `order_import_raw` and `order_import_staging`.
