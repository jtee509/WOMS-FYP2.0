# Plan: Reference Number Generation Engine — Backend Implementation

**Status:** COMPLETED
**Version:** PRE-ALPHA v0.6.2
**Date Planned:** 2026-03-12
**Date Completed:** 2026-03-15
**Author:** James (via Claude Code)
**Related Frontend Plan:** `docs/planning_phase/Frontend/11_barcode_naming_convention.plan.md`

---

## 1. Overview

A centralized, segment-based reference number generation engine that produces structured identifiers for 9 transactional modules in the Warehouse Order Management System. Each module has its own independently configurable convention with versioned history, atomic sequence counters, and optional GS1 compliance.

### Modules

| Module | Target Table | Target Field | Status |
|---|---|---|---|
| ITEMS | `items` | `barcode` | Active |
| ORDER | `orders` | `internal_order_ref` | Active (with platform guard) |
| GRN | -- | -- | Config only (501 on generation) |
| PO | -- | -- | Config only (501 on generation) |
| DELIVERY | `delivery_trips` | `trip_number` | Active |
| INVENTORY_MOVEMENT | `inventory_movements` | `reference_id` | Active |
| STOCK_LOT_BATCH | `stock_lots` | `batch_number` | Active |
| STOCK_LOT_SERIAL | `stock_lots` | `serial_number` | Active |
| STOCK_CHECK | `stock_checks` | `reference_number` | Active |

---

## 2. Architecture

### 2.1 Core Model: `SysSequenceConfig`

File: `backend/app/models/system.py`

- One row per (module_name, version) pair
- Only one row per module may have `is_active = TRUE` (enforced by partial unique index)
- Conventions are never updated in-place -- each "Save" creates a new version row
- Counters carried over from previous version on version change

**Key table constraints:**
```sql
-- Fast active convention lookup
CREATE INDEX idx_sys_seq_active ON sys_sequence_config (module_name) WHERE is_active = TRUE;
-- One active per module
CREATE UNIQUE INDEX uq_sys_seq_one_active_per_module ON sys_sequence_config (module_name) WHERE is_active = TRUE;
```

### 2.2 Atomic Counter: FOR UPDATE Row Lock

```
Session A                               Session B
----------------------------------     ----------------------------------
BEGIN;
SELECT * FROM sys_sequence_config
  WHERE module_name='ITEMS'
  AND is_active=TRUE
  FOR UPDATE;  <- acquires row lock

                                        BEGIN;
                                        SELECT * FROM sys_sequence_config
                                          WHERE module_name='ITEMS'
                                          AND is_active=TRUE
                                          FOR UPDATE;
                                        ^ BLOCKS until A commits

UPDATE sys_sequence_config
  SET global_seq = 43;
UPDATE items SET barcode='ITM-ELEC-0043'
  WHERE item_id = 100;
COMMIT;  <- releases lock

                                        <- unblocks, reads global_seq=43
                                        UPDATE SET global_seq = 44;
                                        UPDATE items SET barcode='ITM-ELEC-0044'
                                          WHERE item_id = 101;
                                        COMMIT;
```

### 2.3 Reset Strategy: Absolute ID + Offset

- `global_seq` monotonically increases and NEVER resets
- `global_seq_offset` records the counter value at the last reset
- Display number = `global_seq - global_seq_offset`, zero-padded
- `_apply_reset_if_needed()` checks `reset_period` (DAILY/MONTHLY/YEARLY/NEVER) against `last_reset_date`
- Manual reset via `POST /reset-offset/{module}` snapshots offset

### 2.4 ORDER Module Platform Guard

Orders imported from platforms (Shopee, Lazada, TikTok) already have `platform_order_id`. The `generate_for_order()` method:
1. Checks if `platform_order_id IS NOT NULL` for the target order
2. If exists -> returns `None` (router returns 409)
3. If empty -> delegates to `generate_for_entity()` which writes to `internal_order_ref`

This ensures platform order IDs are never overwritten.

---

## 3. Service Layer: `SequenceService`

File: `backend/app/services/sequence.py`

### 3.1 Constants

**MODULE_TABLE_MAP** -- maps module name to `(table_name, target_field, pk_column)`:
```python
MODULE_TABLE_MAP = {
    "ITEMS":              ("items",               "barcode",            "item_id"),
    "ORDER":              ("orders",              "internal_order_ref", "order_id"),
    "GRN":                None,
    "PO":                 None,
    "DELIVERY":           ("delivery_trips",      "trip_number",        "trip_id"),
    "INVENTORY_MOVEMENT": ("inventory_movements", "reference_id",       "id"),
    "STOCK_LOT_BATCH":    ("stock_lots",          "batch_number",       "id"),
    "STOCK_LOT_SERIAL":   ("stock_lots",          "serial_number",      "id"),
    "STOCK_CHECK":        ("stock_checks",        "reference_number",   "id"),
}
```

**ALLOWED_SEGMENTS** -- per-module segment type allowlists:
```python
_UNIVERSAL = ["literal", "sequence", "year2", "year4", "month", "date"]

ALLOWED_SEGMENTS = {
    "ITEMS":              _UNIVERSAL + ["category_code", "brand_code", "item_type_code",
                                        "master_sku", "gs1_prefix", "check_digit", "attribute_link"],
    "ORDER":              _UNIVERSAL + ["attribute_link", "platform_code"],
    "GRN":                _UNIVERSAL + ["warehouse_code"],
    "PO":                 _UNIVERSAL + [],
    "DELIVERY":           _UNIVERSAL + ["warehouse_code"],
    "INVENTORY_MOVEMENT": _UNIVERSAL + ["warehouse_code", "movement_type"],
    "STOCK_LOT_BATCH":    _UNIVERSAL + ["master_sku", "warehouse_code"],
    "STOCK_LOT_SERIAL":   _UNIVERSAL + ["master_sku", "warehouse_code"],
    "STOCK_CHECK":        _UNIVERSAL + ["warehouse_code"],
}
```

### 3.2 Methods

| Method | Purpose |
|---|---|
| `get_active_convention(session, module)` | Fetch active config (no lock) |
| `get_convention_history(session, module)` | All versions, newest first |
| `create_convention(session, ...)` | Validate segments, deactivate old, create new version, carry over counter |
| `activate_convention(session, config_id)` | Rollback: deactivate current, activate target |
| `_lock_and_increment(session, module)` | FOR UPDATE lock + reset check + increment -> (config, display_seq) |
| `_apply_reset_if_needed(config)` | Check period vs last_reset_date, snapshot offset if due |
| `reset_offset(session, module)` | Manual soft-reset |
| `build_reference(config, display_seq, entity)` | Pure function: resolve segments + join with separator |
| `_resolve_segment(seg, config, display_seq, entity)` | 16 type handlers with fallback placeholders |
| `peek_next(config)` | Read-only preview without incrementing |
| `compute_check_digit(payload)` | GS1 Modulo-10 algorithm |
| `generate_for_entity(session, module, entity_id, user_id)` | Lock + increment + build + write via raw SQL |
| `generate_for_order(session, order_id, user_id)` | Platform guard -> delegate to generate_for_entity |
| `bulk_generate(session, module, user_id)` | Find NULL target fields, generate for each; ORDER excludes platform orders, ITEMS excludes soft-deleted |
| `get_module_stats(session, module)` | Counter values + missing/total entity counts |
| `_load_item_entity(session, item_id)` | selectinload(category, brand, item_type) |
| `_load_order_entity(session, order_id)` | selectinload(platform) |

### 3.3 Segment Resolution (16 types)

| Type | Resolution Logic | Fallback |
|---|---|---|
| `literal` | `seg.value` | `""` |
| `sequence` | `str(display_seq).zfill(padding)` | -- |
| `year2` | `strftime("%y")` | -- |
| `year4` | `str(today.year)` | -- |
| `month` | `strftime("%m")` | -- |
| `date` | `strftime("%Y%m%d")` | -- |
| `category_code` | `entity.category.category_name[:chars]` | `"NOCAT"` |
| `brand_code` | `entity.brand.brand_name[:chars]` | `"NOBR"` |
| `item_type_code` | `entity.item_type.item_type_name[:chars]` | `"NOTY"` |
| `master_sku` | `entity.master_sku` | `"NOSKU"` |
| `gs1_prefix` | `config.gs1_company_prefix` | `"0000000"` |
| `warehouse_code` | `entity.warehouse.warehouse_name[:chars]` | `"NOWH"` |
| `movement_type` | `entity.movement_type_rel.movement_name[:chars]` | `"NOMT"` |
| `platform_code` | `entity.platform.platform_name[:chars]` | `"NOPL"` |
| `attribute_link` | `getattr(entity, field_path)` | `"NA"` |
| `check_digit` | Computed after all other segments via `compute_check_digit()` | -- |

### 3.4 GS1 Modulo-10 Check Digit

```python
@staticmethod
def compute_check_digit(payload: str) -> str:
    digits = [int(c) for c in payload if c.isdigit()]
    if not digits:
        return "0"
    total = sum(
        d * (3 if i % 2 == 0 else 1)
        for i, d in enumerate(reversed(digits))
    )
    return str((10 - (total % 10)) % 10)
```

---

## 4. Router: 10 Endpoints

File: `backend/app/routers/sequence.py`
Base prefix: `/api/v1/sequence`
Auth: All endpoints require `require_current_user`

| Method | Path | Description | Status Codes |
|---|---|---|---|
| `GET` | `/modules` | List all 9 modules with status, allowed segments | 200 |
| `GET` | `/stats/{module}` | Counter stats + missing entity count | 200, 400 |
| `GET` | `/convention` | Active convention (`?module=ITEMS`) | 200, 404 |
| `GET` | `/convention/history` | All versions (`?module=ITEMS`) | 200 |
| `POST` | `/convention` | Create new version (auto-activates) | 201, 422 |
| `POST` | `/convention/{config_id}/activate` | Restore historical version | 200, 404 |
| `POST` | `/convention/preview` | Preview rendered reference (no write) | 200 |
| `POST` | `/generate/{module}/{entity_id}` | Generate + persist one reference | 200, 409, 422, 501 |
| `POST` | `/generate/{module}/bulk` | Bulk generate for module | 200, 501 |
| `POST` | `/reset-offset/{module}` | Soft-reset display counter | 200, 422 |

**501 Not Implemented:** GRN, PO modules (table not built yet)
**409 Conflict:** ORDER when `platform_order_id` exists on target order

---

## 5. Schemas

File: `backend/app/schemas/sequence.py`

Uses `Literal` types for strict validation:
- `ModuleName` -- 9 values
- `SegmentType` -- 16 values
- `BarcodeFormat` -- 5 values
- `ResetPeriod` -- 4 values

**Key schemas:**
- `SegmentDefinition` -- order, type, value, chars, padding, field, uppercase, locked
- `ConventionCreate` -- module_name, name, separator, barcode_format, segments, padding_length, reset_period, is_gapless, auto_apply_on_create, gs1_company_prefix
- `ConventionRead` -- all fields from DB + config_id, version, is_active, timestamps
- `PreviewRequest` -- module_name, segments, separator, padding_length, gs1_company_prefix, sample_entity_id
- `PreviewResponse` -- rendered string + segment_breakdown list
- `GenerateResult` -- entity_id, generated_reference, module_name
- `BulkGenerateResult` -- total, success, failed, errors
- `ModuleInfo` -- module_name, display_name, allowed_segments, table_exists, has_active_config
- `ModuleStats` -- module_name, global_seq, global_seq_offset, display_counter, entities_missing_reference, total_entities

**Custom validators:**
- `validate_literal_value` -- regex `^[A-Za-z0-9\-_]+$` for literal segments
- `validate_gs1_prefix` -- required when format is GS1-128/SSCC-18
- `validate_check_digit_position` -- must be last segment

---

## 6. Alembic Migration

File: `backend/alembic/versions/20260315_0000_00_l7m8n9o0p1q2_add_sequence_config_engine.py`

### Creates
1. `sys_sequence_config` table (all columns + partial indexes)
2. `barcode` column on `items` (VARCHAR 200, UNIQUE, idempotent)
3. `internal_order_ref` column on `orders` (VARCHAR 100, UNIQUE, idempotent)
4. `trip_number` column on `delivery_trips` (VARCHAR 100, UNIQUE, idempotent)
5. `reference_number` column on `stock_checks` (VARCHAR 100, UNIQUE, idempotent)
6. SKU immutability trigger (`prevent_master_sku_update` + `trg_items_sku_immutable`)
7. Seeds 9 default conventions (all `is_active = FALSE`)

### Idempotent Helpers

```python
def _add_column_if_not_exists(conn, table, column, col_type, **kwargs):
    """Check information_schema.columns before ALTER TABLE ADD COLUMN."""
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table, "col": column})
    if result.scalar() is None:
        # Execute ALTER TABLE ADD COLUMN
        ...

def _create_index_if_not_exists(conn, index_name, table, column, unique=False):
    """Check pg_indexes before CREATE INDEX."""
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    if result.scalar() is None:
        # Execute CREATE INDEX
        ...
```

### Trigger Creation: `sa.text()` not `op.execute()`

The SKU immutability trigger is created using `conn.execute(sa.text(...))` instead of `op.execute(...)` because `op.execute()` double-escapes `%` characters, corrupting PL/pgSQL RAISE format strings.

```python
with op.get_bind().begin() as conn:
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION prevent_master_sku_update() ...
    """))
```

---

## 7. Model Changes

### 7.1 `items.py` -- added `barcode`
```python
barcode: Optional[str] = Field(
    default=None, max_length=200, unique=True, index=True,
    description="System-generated reference code. Immutable after first assignment."
)
```

### 7.2 `orders.py` -- added `internal_order_ref`
```python
internal_order_ref: Optional[str] = Field(
    default=None, max_length=100, unique=True, index=True,
    description="WOMS-generated internal order reference. "
    "Only populated for manual/internal orders (when platform_order_id is NULL)."
)
```

### 7.3 `delivery.py` -- added `trip_number`
```python
trip_number: Optional[str] = Field(
    default=None, max_length=100, unique=True, index=True,
    description="System-generated trip reference (e.g. DLV-20260315-0001)"
)
```

### 7.4 `stock_check.py` -- added `reference_number`
```python
reference_number: Optional[str] = Field(
    default=None, max_length=100, unique=True, index=True,
    description="System-generated stock check reference (e.g. SC-20260315-0001)"
)
```

### 7.5 `triggers.py` -- added SKU immutability trigger (#12)
```sql
CREATE OR REPLACE FUNCTION prevent_master_sku_update()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.master_sku IS DISTINCT FROM NEW.master_sku THEN
        RAISE EXCEPTION
            'master_sku is immutable after creation. Item ID: %, Change: % -> %',
            OLD.item_id, OLD.master_sku, NEW.master_sku
        USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_items_sku_immutable
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION prevent_master_sku_update();
```

### 7.6 `__init__.py` -- added missing imports
```python
from app.models.stock_check import (StockCheck, StockCheckLine)
from app.models.system import (SysSequenceConfig)
```

---

## 8. Bugs Encountered & Solutions

### Bug 1: `DuplicateColumn` on Alembic migration
**Symptom:** `DuplicateColumn: column "barcode" of relation "items" already exists`
**Root Cause:** Debug mode `init_db_full()` in `database.py` runs `create_all()` which creates columns from model definitions before the migration runs.
**Solution:** Added `_add_column_if_not_exists()` and `_create_index_if_not_exists()` idempotent helpers that check `information_schema.columns` and `pg_indexes` before DDL.

### Bug 2: `SyntaxError: too many parameters for RAISE`
**Symptom:** PL/pgSQL trigger creation fails with syntax error
**Root Cause:** `op.execute()` in Alembic double-escapes `%` characters (`%%` -> `%%%%`), corrupting RAISE format strings.
**Solution:** Switched to `conn.execute(sa.text(...))` which does not perform `%` escaping. Used `with op.get_bind().begin() as conn:` pattern.

### Bug 3: Reference Numbers tab fails to load (frontend reports 500)
**Symptom:** `GET /api/v1/sequence/modules` returns 500 Internal Server Error
**Root Cause:** `SysSequenceConfig` not imported in `backend/app/models/__init__.py` -- SQLModel cannot register the table for queries. `StockCheck`/`StockCheckLine` also missing (pre-existing).
**Solution:** Added all missing imports and `__all__` entries, then ran `alembic upgrade head`.

---

## 9. Files Created/Modified

| File | Action |
|---|---|
| `backend/app/models/system.py` | **Created** |
| `backend/app/models/items.py` | Modified |
| `backend/app/models/orders.py` | Modified |
| `backend/app/models/delivery.py` | Modified |
| `backend/app/models/stock_check.py` | Modified |
| `backend/app/models/triggers.py` | Modified |
| `backend/app/models/__init__.py` | Modified |
| `backend/app/schemas/sequence.py` | **Created** |
| `backend/app/services/sequence.py` | **Created** |
| `backend/app/routers/sequence.py` | **Created** |
| `backend/app/main.py` | Modified |
| `backend/alembic/versions/20260315_..._l7m8n9o0p1q2_...py` | **Created** |
| `docs/official_documentation/database_structure.md` | Modified |
| `docs/official_documentation/web-api.md` | Modified |
| `docs/official_documentation/version_update.md` | Modified |

---

## 10. Lessons Learned

1. **Always use `sa.text()` for PL/pgSQL in Alembic** -- `op.execute()` corrupts `%` characters in format strings
2. **Make migration DDL idempotent** -- debug mode `create_all()` may pre-create columns; use `information_schema` checks
3. **Register all models in `__init__.py`** -- SQLModel requires imports to register tables; missing imports cause silent query failures
4. **Separate ORDER fields** -- `internal_order_ref` is separate from `platform_order_id` to avoid any conflict with platform-imported data
5. **Split STOCK_LOT into two configs** -- batch numbers and serial numbers have different reset policies and segment compositions, so they get independent conventions (STOCK_LOT_BATCH and STOCK_LOT_SERIAL)

---

*Backend implementation completed -- v0.6.2 Reference Number Generation Engine, 2026-03-15.*
