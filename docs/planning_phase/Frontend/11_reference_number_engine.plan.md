# Plan: Configurable Reference Numbering Engine — Full-Stack Implementation

**Module:** Settings → Reference Numbers Tab
**Status:** COMPLETED
**Version:** PRE-ALPHA v0.6.2
**Date Planned:** 2026-03-12
**Date Completed:** 2026-03-15
**Author:** James (via Claude Code)
**Supersedes:** Original "Barcode Naming Convention" plan (2026-03-12)

---

## 1. Overview & Strategic Rationale

This plan upgrades the original "Barcode Naming Convention" concept to a **full Reference Numbering Engine** — a centralized, configurable system that generates human-readable, structured identifiers for every transactional entity in the WMS: items (SKUs), orders, goods receipt notes (GRN), purchase orders (PO), delivery trips, inventory movements, stock lots (batch + serial), and stock checks.

### Why a dedicated engine, not ad-hoc fields

Reference numbers in a WMS are not cosmetic strings — they are the **digital license plates** that bind physical warehouse units to their database records. Every barcode label scanned at the picking station, every GRN printed at the receiving dock, and every order acknowledgment emailed to a platform references one of these IDs. An ad-hoc approach (manually typed `master_sku`, no structure) produces:

- Inconsistent scan results across different barcode hardware (linear vs. 2D scanners)
- No embedded metadata — staff cannot decode which category or warehouse a code belongs to without a DB lookup
- No mathematical error detection — transposition errors during manual entry cause silent data corruption
- Chargebacks from major retailers who require GS1-compliant labels
- Audit failures when regulators demand a continuous, traceable sequence for invoice documents

### What this engine provides

1. **Segment-based template configuration** — admins compose IDs from 16 typed building blocks (literal prefix, date, sequence counter, entity metadata, GS1 company prefix, Modulo-10 check digit, warehouse code, movement type, platform code)
2. **Versioned convention history** — each format change creates a new version row rather than overwriting; instant rollback to any previous version with one click
3. **Concurrency-safe generation** — row-level `FOR UPDATE` lock ensures zero duplicate IDs under hundreds of concurrent requests; gapless mode available for legally-mandated documents
4. **9-module support** — one engine, one settings UI, configures identifiers for ITEMS, ORDER, GRN, PO, DELIVERY, INVENTORY_MOVEMENT, STOCK_LOT_BATCH, STOCK_LOT_SERIAL, and STOCK_CHECK simultaneously
5. **GS1 compliance path** — optional GS1 prefix segment + Modulo-10 check digit make generated codes compatible with SSCC-18, GS1-128, and Code-128 standards
6. **ORDER guard clause** — orders imported from platforms (Shopee, Lazada, TikTok) with existing `platform_order_id` are skipped; only manual/internal orders receive generated `internal_order_ref`

---

## 2. Scope

### Implemented (v0.6.2)
- `sys_sequence_config` table — multi-module sequence registry with partial unique index (`is_active = TRUE`)
- `barcode` field on `Item` model (nullable, unique)
- `internal_order_ref` field on `Order` model (nullable, unique) — separate from `platform_order_id`
- `trip_number` field on `DeliveryTrip` model (nullable, unique)
- `reference_number` field on `StockCheck` model (nullable, unique)
- Backend service `SequenceService` — atomic ID generation via `FOR UPDATE` row lock
- Backend router — 10 REST endpoints at `/api/v1/sequence`
- Settings page: new **"Reference Numbers"** tab (4th tab)
- Module selector pills for all 9 modules (green dot for modules with active config)
- Segment builder UI — drag-reorder segments, live preview, GS1 prefix input
- Convention builder — name, separator, barcode format, reset period, auto-apply, gapless toggles
- Counter stats panel — global/display/offset counters, reset and bulk generate buttons
- Versioned history panel — view all past conventions, restore any previous version
- SKU immutability enforcement — PostgreSQL trigger `trg_items_sku_immutable`
- Bulk generation endpoint — apply active convention to all entities missing a reference
- Single-entity generation endpoint — generate/persist reference for one entity
- GRN/PO modules configurable in UI but return 501 Not Implemented for generation
- Alembic migration `l7m8n9o0p1q2` — creates table, adds columns, creates trigger, seeds 9 conventions

### Out of Scope — future phases
- Barcode image rendering (QR / EAN-13 / DataMatrix visual output) — print label module
- Per-warehouse sequence counters (v1 is org-wide)
- Platform barcode sync (Shopee/Lazada listing SKU mapping)
- Redis-backed distributed counter (for >200 concurrent sensor requests)
- Snowflake ID generation (for high-volume sensor/event telemetry)
- Scan pattern configuration UI (Linear / Raster / Sweep / Random)
- Full SSCC-18 Extension Digit + Company Prefix management UI
- ItemFormPage integration (barcode field + generate button in edit mode) — separate task

---

## 3. Architectural Principles

### 3.1 Segment-based vs. flat-string generation

Every reference ID is assembled from an ordered list of **typed segments**. The engine iterates the segment list at generation time, resolves each segment to a string, and concatenates them with the configured separator.

This is architecturally superior to a single `format_string` (e.g. `"ITM-{date}-{seq}"`) because:
- Each segment type has explicit, validated configuration (e.g. sequence padding must be 1-12, chars must be 1-10)
- The UI can render each segment as an interactive widget rather than a raw string editor
- New segment types (e.g. `warehouse_code`, `gs1_prefix`) can be added without changing the template parser

### 3.2 Versioned configuration (never in-place update)

Administrators **never** modify the active convention directly. Each "Save" creates a new version row with `version` incremented and `is_active = TRUE`, while the old row is set to `is_active = FALSE`. This allows:
- Instant rollback: reactivate any historical version
- Forensic audit: see exactly what format was active when a specific barcode was issued
- Zero-downtime format transitions: the new version is tested in preview before activation

### 3.3 Gapless vs. gap-tolerant sequences

| Mode | Mechanism | Use Case |
|---|---|---|
| **Gap-tolerant** (default) | Counter in `sys_sequence_config` + `FOR UPDATE` row lock | Item SKUs, License Plate IDs, Delivery trips |
| **Gapless** | Same `FOR UPDATE` lock, counter only advances on commit | Invoices, tax documents where legal continuity is required |

### 3.4 Reset strategy: Absolute ID + Offset (not ALTER SEQUENCE)

- `global_seq_offset` stores the value of `global_seq` at the time of the last reset
- The human-readable ID suffix is `global_seq - global_seq_offset`, zero-padded
- The global counter never goes backwards — only the displayed suffix resets
- This makes resets safe to apply during any transaction

### 3.5 GS1 compliance (Modulo-10 check digit)

When `barcode_format = 'GS1-128'` or `'SSCC-18'`, the engine appends a Modulo-10 check digit as the final character. Implemented as a `check_digit` segment type — UI forces it to last position and marks it read-only.

### 3.6 SKU immutability after creation

`master_sku` on the `items` table is immutable after creation, enforced by PostgreSQL trigger `prevent_master_sku_update()` which raises `integrity_constraint_violation` on UPDATE.

### 3.7 ORDER module platform guard

Orders imported from platforms (Shopee, Lazada, TikTok) already have `platform_order_id`. The `generate_for_order()` method checks if `platform_order_id` exists — if so, generation is skipped (returns 409). Only manual/internal orders without a platform ID receive `internal_order_ref`.

---

## 4. Data Model

### 4.1 `sys_sequence_config` table

File: `backend/app/models/system.py`

```python
class SysSequenceConfig(SQLModel, table=True):
    __tablename__ = "sys_sequence_config"
    __table_args__ = (
        Index("idx_sys_seq_active", "module_name",
              postgresql_where=text("is_active = TRUE")),
        Index("uq_sys_seq_one_active_per_module", "module_name",
              unique=True,
              postgresql_where=text("is_active = TRUE")),
    )

    config_id:           Optional[int]    # PK, serial
    module_name:         str              # 9 values (see Scope)
    version:             int              # starts at 1, increments per change
    is_active:           bool             # only one active per module (partial unique index)
    name:                str              # human label
    separator:           str              # '-', '_', '/', or ''
    barcode_format:      str              # 'Internal', 'Code-128', 'GS1-128', 'SSCC-18', 'QR'
    segments:            List[Dict]       # JSONB — ordered segment definitions
    global_seq:          int = 0          # monotonically increasing counter
    global_seq_offset:   int = 0          # for Absolute ID + Offset reset
    padding_length:      int = 4          # zero-pad width (1-12)
    reset_period:        str = 'NEVER'    # DAILY, MONTHLY, YEARLY, NEVER
    last_reset_date:     Optional[date]
    is_gapless:          bool = False
    auto_apply_on_create:bool = False
    gs1_company_prefix:  Optional[str]    # 7-10 digit GS1 prefix
    created_by:          Optional[int]    # FK -> users.user_id
    created_at:          datetime
    updated_at:          datetime
```

### 4.2 New fields on existing tables

| Table | Field | Type | Purpose |
|---|---|---|---|
| `items` | `barcode` | `VARCHAR(200) UNIQUE` | System-generated item reference/barcode |
| `orders` | `internal_order_ref` | `VARCHAR(100) UNIQUE` | WOMS-generated order ref (only for non-platform orders) |
| `delivery_trips` | `trip_number` | `VARCHAR(100) UNIQUE` | System-generated trip reference |
| `stock_checks` | `reference_number` | `VARCHAR(100) UNIQUE` | System-generated stock check reference |

All fields: nullable, unique, indexed. Immutable after first assignment.

### 4.3 Complete Segment Type Reference (16 types)

| Type | Config Fields | Description | Example | Modules |
|---|---|---|---|---|
| `literal` | `value` | Static text | `WH`, `ITM` | All |
| `sequence` | `padding` (1-12) | Display counter, zero-padded | `0042` | All |
| `year2` | -- | 2-digit year | `26` | All |
| `year4` | -- | 4-digit year | `2026` | All |
| `month` | -- | 2-digit month | `03` | All |
| `date` | -- | YYYYMMDD | `20260315` | All |
| `category_code` | `chars` (1-10) | First N chars of category name | `ELEC` | ITEMS |
| `brand_code` | `chars` (1-10) | First N chars of brand name | `NIK` | ITEMS |
| `item_type_code` | `chars` (1-10) | First N chars of item type | `PROD` | ITEMS |
| `master_sku` | -- | Full master SKU value | `AB-1234` | ITEMS, STOCK_LOT_* |
| `gs1_prefix` | -- | GS1 company prefix from config | `9501234` | ITEMS |
| `check_digit` | -- | GS1 Mod-10; forced last, locked | `7` | ITEMS |
| `attribute_link` | `field` (dot-path) | Dynamic entity field | `KL` | ITEMS, ORDER |
| `warehouse_code` | `chars` (1-10) | First N chars of warehouse name | `MAIN` | GRN, DELIVERY, INV_MOV, STOCK_LOT_*, STOCK_CHECK |
| `movement_type` | `chars` (1-10) | First N chars of movement type | `RECV` | INVENTORY_MOVEMENT |
| `platform_code` | `chars` (1-10) | First N chars of platform name | `LAZA` | ORDER |

### 4.4 Per-module segment allowlists

```python
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
# _UNIVERSAL = ["literal", "sequence", "year2", "year4", "month", "date"]
```

---

## 5. Backend Implementation (COMPLETED)

### 5.1 Files created/modified

| File | Action | Detail |
|---|---|---|
| `backend/app/models/system.py` | **Created** | `SysSequenceConfig` SQLModel class |
| `backend/app/models/items.py` | Modified | Added `barcode` field after `image_url` |
| `backend/app/models/orders.py` | Modified | Added `internal_order_ref` field after `platform_order_id` |
| `backend/app/models/delivery.py` | Modified | Added `trip_number` field to `DeliveryTrip` after `team_id` |
| `backend/app/models/stock_check.py` | Modified | Added `reference_number` field to `StockCheck` after `warehouse_id` |
| `backend/app/models/triggers.py` | Modified | Added trigger #12: `prevent_master_sku_update()` + `trg_items_sku_immutable` |
| `backend/app/models/__init__.py` | Modified | Added imports for `StockCheck`, `StockCheckLine`, `SysSequenceConfig` + `__all__` entries |
| `backend/app/schemas/sequence.py` | **Created** | Pydantic schemas with `Literal` types for strict validation |
| `backend/app/services/sequence.py` | **Created** | `SequenceService` -- template engine + atomic counter + entity loaders |
| `backend/app/routers/sequence.py` | **Created** | 10 REST endpoints |
| `backend/app/main.py` | Modified | Registered sequence router at `/api/v1/sequence` |
| `backend/alembic/versions/20260315_..._l7m8n9o0p1q2_add_sequence_config_engine.py` | **Created** | Migration: table + columns + trigger + seed |

### 5.2 API Endpoints

**Base prefix:** `/api/v1/sequence`

| Method | Path | Description | Status Codes |
|---|---|---|---|
| `GET` | `/modules` | List all 9 modules with status, allowed segments, table info | 200 |
| `GET` | `/stats/{module}` | Module counter stats + entities missing references | 200, 400 |
| `GET` | `/convention` | Active convention for module (`?module=ITEMS`) | 200, 404 |
| `GET` | `/convention/history` | All versions for module, newest first | 200 |
| `POST` | `/convention` | Create new version (auto-activates, deactivates previous) | 201, 422 |
| `POST` | `/convention/{config_id}/activate` | Restore historical version | 200, 404 |
| `POST` | `/convention/preview` | Preview rendered reference (no DB write, no counter change) | 200 |
| `POST` | `/generate/{module}/{entity_id}` | Generate + persist for one entity | 200, 409, 422, 501 |
| `POST` | `/generate/{module}/bulk` | Bulk generate for all entities missing reference | 200, 501 |
| `POST` | `/reset-offset/{module}` | Soft-reset display counter (snapshot offset) | 200, 422 |

**Special behaviours:**
- GRN/PO -> 501 Not Implemented for generation endpoints
- ORDER -> 409 if `platform_order_id` exists on the target order

### 5.3 Service Layer -- `SequenceService`

```
SequenceService
|
+-- get_active_convention(session, module_name) -> SysSequenceConfig | None
+-- get_convention_history(session, module_name) -> List[SysSequenceConfig]
+-- create_convention(session, ...) -> SysSequenceConfig
|     Validates segments against module allowlist, carries over counter,
|     deactivates previous, creates new version with is_active=True.
+-- activate_convention(session, config_id) -> SysSequenceConfig
|     Rollback: deactivates current, activates target historical version.
|
+-- _lock_and_increment(session, module_name) -> (config, display_seq)
|     FOR UPDATE lock on active config, applies reset if due,
|     increments global_seq, returns display_seq = global_seq - offset.
+-- _apply_reset_if_needed(config)
|     Checks reset_period vs last_reset_date, snapshots offset if due.
+-- reset_offset(session, module_name) -> SysSequenceConfig
|     Manual soft-reset: snapshot current counter as new offset.
|
+-- build_reference(config, display_seq, entity) -> str
|     Pure function: resolve each segment, join with separator,
|     append check digit if configured.
+-- _resolve_segment(seg, config, display_seq, entity) -> str
|     16 segment type handlers with fallback placeholders.
+-- peek_next(config) -> str
|     Read-only preview: next reference without incrementing.
+-- compute_check_digit(payload) -> str
|     GS1 Modulo-10: right-to-left, multiply by 3/1 alternating.
|
+-- generate_for_entity(session, module, entity_id, user_id) -> str
|     Lock + increment + build + write to entity target field via raw SQL.
+-- generate_for_order(session, order_id, user_id) -> str | None
|     Guard: skip if platform_order_id exists; otherwise delegate.
+-- bulk_generate(session, module, user_id) -> {total, success, failed, errors}
|     Find entities with NULL target field, generate for each.
|     ORDER: additional filter excludes platform orders.
|     ITEMS: additional filter excludes soft-deleted.
+-- get_module_stats(session, module_name) -> dict
|
+-- _load_item_entity(session, item_id) -> Item
|     selectinload(category, brand, item_type)
+-- _load_order_entity(session, order_id) -> Order
      selectinload(platform)
```

### 5.4 MODULE_TABLE_MAP

```python
MODULE_TABLE_MAP = {
    "ITEMS":              ("items",               "barcode",            "item_id"),
    "ORDER":              ("orders",              "internal_order_ref", "order_id"),
    "GRN":                None,  # table not yet built
    "PO":                 None,  # table not yet built
    "DELIVERY":           ("delivery_trips",      "trip_number",        "trip_id"),
    "INVENTORY_MOVEMENT": ("inventory_movements", "reference_id",       "id"),
    "STOCK_LOT_BATCH":    ("stock_lots",          "batch_number",       "id"),
    "STOCK_LOT_SERIAL":   ("stock_lots",          "serial_number",      "id"),
    "STOCK_CHECK":        ("stock_checks",        "reference_number",   "id"),
}
```

### 5.5 Alembic Migration (`l7m8n9o0p1q2`)

**Creates:**
1. `sys_sequence_config` table with all columns + partial unique index
2. `barcode VARCHAR(200)` on `items` table (idempotent)
3. `internal_order_ref VARCHAR(100)` on `orders` table (idempotent)
4. `trip_number VARCHAR(100)` on `delivery_trips` table (idempotent)
5. `reference_number VARCHAR(100)` on `stock_checks` table (idempotent)
6. SKU immutability trigger via `conn.execute(sa.text(...))` (not `op.execute()`)
7. Unique indexes on all new columns (idempotent)
8. Seeds 9 default conventions (all `is_active = FALSE`)

**Idempotent helpers:**
- `_add_column_if_not_exists()` -- checks `information_schema.columns` before `ALTER TABLE ADD COLUMN`
- `_create_index_if_not_exists()` -- checks `pg_indexes` before `CREATE UNIQUE INDEX`

### 5.6 SKU Immutability Trigger

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

---

## 6. Frontend Implementation (COMPLETED)

### 6.1 Files created/modified

| File | Action |
|---|---|
| `frontend/src/api/base_types/sequence.ts` | **Created** -- TypeScript types + constants |
| `frontend/src/api/base/sequence.ts` | **Created** -- 10 Axios API calls |
| `frontend/src/pages/settings/SettingsPage.tsx` | Modified -- added "Reference Numbers" tab |
| `frontend/src/pages/settings/ReferenceNumbersTab.tsx` | **Created** -- tab container + module selector |
| `frontend/src/pages/settings/reference_numbers/ModuleSelector.tsx` | **Created** -- pill strip for 9 modules |
| `frontend/src/pages/settings/reference_numbers/ConventionBuilder.tsx` | **Created** -- main form |
| `frontend/src/pages/settings/reference_numbers/SegmentBuilder.tsx` | **Created** -- drag-reorder list |
| `frontend/src/pages/settings/reference_numbers/SegmentRow.tsx` | **Created** -- single segment config |
| `frontend/src/pages/settings/reference_numbers/PreviewBar.tsx` | **Created** -- live preview + copy |
| `frontend/src/pages/settings/reference_numbers/GS1ConfigSection.tsx` | **Created** -- conditional GS1 fields |
| `frontend/src/pages/settings/reference_numbers/CounterStats.tsx` | **Created** -- counter display + actions |
| `frontend/src/pages/settings/reference_numbers/ConventionHistory.tsx` | **Created** -- version history + restore |

### 6.2 Reference Numbers Tab -- UI Layout

```
+-- Settings ----------------------------------------------------------+
|  [Items Data]  [Platforms]  [Warehouse Site]  [Reference Numbers]     |
+----------------------------------------------------------------------+
|                                                                      |
|  [ITEMS]  [ORDER]  [GRN]  [PO]  [DELIVERY]  [INV_MOV]  ...  pills   |
|   * green dot = has active config                                    |
|                                                                      |
|  -- Active Convention ---------------------------------------------- |
|  Name:          [Standard Item Format v2         ]                   |
|  Barcode Format:[Internal v]                                         |
|  Separator:     [*]-  [ ]_  [ ]/  [ ]none   (radio buttons)         |
|  Reset Period:  [NEVER v]                                            |
|  Auto-apply:    [toggle]     Gapless: [toggle]                       |
|                                                                      |
|  -- GS1 Settings  (GS1-128 / SSCC-18 only) ----------------------- |
|  GS1 Company Prefix: [9501234   ]                                    |
|                                                                      |
|  -- Segment Builder ---------------------------------------------- - |
|  +----------------------------------------------------------+       |
|  | ::  1.  [Literal     v]  value: [ITM      ]        [x]   |       |
|  | ::  2.  [Category    v]  chars: [4        ]        [x]   |       |
|  | ::  3.  [Sequence    v]  pad:   [4        ]        [x]   |       |
|  | [+ Add Segment]                                           |       |
|  +----------------------------------------------------------+       |
|                                                                      |
|  -- Live Preview -------------------------------------------------- |
|  |  ITM-ELEC-0043           [Copy] | chips: ITM | ELEC | 0043       |
|                                                                      |
|  [Save as New Version]                                               |
|                                                                      |
|  -- Counter Stats ------------------------------------------------- |
|  Global: 43  Display: 43  Offset: 0  Missing: 127                   |
|  [Reset Display Counter]  [Bulk Generate]                            |
|                                                                      |
|  > Version History (3)  <- collapsible                               |
|    v2 [ACTIVE] -- "Standard Format v2" -- ITM-ELEC-SEQ:4            |
|    v1          -- "Initial Format"     -- WH-CAT:4-SEQ:4  [Restore] |
+----------------------------------------------------------------------+
```

### 6.3 Key UI Interactions

- **ModuleSelector**: pill strip with green dot for active config; reduced opacity for not-implemented modules (GRN, PO)
- **SegmentBuilder**: HTML5 drag-and-drop (no library); type dropdown filtered by module's `allowed_segments`; new segment inserts before locked segments
- **PreviewBar**: debounced 300ms via `POST /convention/preview`; shows rendered string + segment breakdown chips; copy to clipboard
- **GS1ConfigSection**: only shown when `barcode_format` is GS1-128 or SSCC-18; 7-10 digit validation
- **CounterStats**: disabled for non-implemented modules; reset + bulk generate with loading states
- **ConventionHistory**: collapsed by default; active version highlighted with blue border + ACTIVE badge; restore with confirmation dialog

### 6.4 TypeScript Types (`sequence.ts`)

```typescript
export type ModuleName = 'ITEMS' | 'ORDER' | 'GRN' | 'PO' | 'DELIVERY'
  | 'INVENTORY_MOVEMENT' | 'STOCK_LOT_BATCH' | 'STOCK_LOT_SERIAL' | 'STOCK_CHECK';

export type SegmentType = 'literal' | 'category_code' | 'brand_code' | 'item_type_code'
  | 'master_sku' | 'sequence' | 'year2' | 'year4' | 'month' | 'date'
  | 'gs1_prefix' | 'attribute_link' | 'check_digit'
  | 'warehouse_code' | 'movement_type' | 'platform_code';

export type BarcodeFormat = 'Internal' | 'Code-128' | 'GS1-128' | 'SSCC-18' | 'QR';
export type ResetPeriod = 'DAILY' | 'MONTHLY' | 'YEARLY' | 'NEVER';
```

Constants: `SEGMENT_TYPE_LABELS` (16 human-readable labels), `MODULE_LABELS` (9 module display names)

---

## 7. Validation Rules

### Convention form
| Field | Rule |
|---|---|
| `name` | Required, 1-100 chars |
| `separator` | Max 3 chars; may be empty |
| `barcode_format` | Must be one of the BarcodeFormat values |
| `gs1_company_prefix` | Required if format is GS1-128 or SSCC-18; 7-10 numeric digits |
| `segments` | At least 1 segment; `check_digit` must be last if present |
| `literal.value` | Must match `^[A-Za-z0-9\-_]+$` |
| `chars` | Integer 1-10 |
| `padding_length` | Integer 1-12 |

### Segment validation (Pydantic)
- `validate_literal_value`: regex check for literal segment values
- `validate_gs1_prefix`: required when GS1 format and gs1_prefix segment present
- `validate_check_digit_position`: must be last segment if present

---

## 8. Bugs Encountered & Fixed

### Bug 1: `DuplicateColumn` on Alembic migration
**Cause:** Debug mode `init_db_full()` in `database.py` already created columns from model definitions (via `create_all()`) before the migration ran.
**Fix:** Added `_add_column_if_not_exists()` and `_create_index_if_not_exists()` idempotent helpers that check `information_schema.columns` and `pg_indexes` before executing DDL.

### Bug 2: `SyntaxError: too many parameters for RAISE`
**Cause:** `op.execute()` in Alembic double-escapes `%` characters (`%%` -> `%%%%`), corrupting PL/pgSQL RAISE format strings like `'Item ID: %, Change: % -> %'`.
**Fix:** Switched from `op.execute("""...""")` to `conn.execute(sa.text("""..."""))` in the migration's `with op.get_bind().begin() as conn:` block. `sa.text()` does not perform `%` escaping.

### Bug 3: Reference Numbers tab fails to load
**Cause:** `SysSequenceConfig` was not imported in `backend/app/models/__init__.py`, so SQLModel couldn't register the table for queries. Additionally, `StockCheck`/`StockCheckLine` were also missing (pre-existing issue).
**Fix:** Added all missing imports (`StockCheck`, `StockCheckLine`, `SysSequenceConfig`) and their `__all__` entries. Then ran `alembic upgrade head` to apply the migration.

---

## 9. Implementation Order (COMPLETED)

1. [x] `backend/app/models/system.py` -- `SysSequenceConfig` SQLModel
2. [x] `backend/app/models/items.py` -- added `barcode` field
3. [x] `backend/app/models/orders.py` -- added `internal_order_ref` field
4. [x] `backend/app/models/delivery.py` -- added `trip_number` field
5. [x] `backend/app/models/stock_check.py` -- added `reference_number` field
6. [x] `backend/app/models/triggers.py` -- added `prevent_master_sku_update` trigger
7. [x] `backend/app/schemas/sequence.py` -- all Pydantic schemas
8. [x] `backend/app/services/sequence.py` -- `SequenceService` (template engine, check digit, bulk apply)
9. [x] `backend/app/routers/sequence.py` -- 10 REST endpoints
10. [x] `backend/app/main.py` -- registered router at `/api/v1/sequence`
11. [x] `backend/alembic/versions/...l7m8n9o0p1q2...` -- Alembic migration
12. [x] `frontend/src/api/base_types/sequence.ts` -- TypeScript types + constants
13. [x] `frontend/src/api/base/sequence.ts` -- Axios API calls
14. [x] `frontend/.../ModuleSelector.tsx` -- module pill selector
15. [x] `frontend/.../SegmentRow.tsx` + `SegmentBuilder.tsx` -- segment editing
16. [x] `frontend/.../PreviewBar.tsx` -- live preview with segment chips
17. [x] `frontend/.../GS1ConfigSection.tsx` -- conditional GS1 fields
18. [x] `frontend/.../CounterStats.tsx` -- counter display + reset/bulk actions
19. [x] `frontend/.../ConventionHistory.tsx` -- versioned history + rollback
20. [x] `frontend/.../ConventionBuilder.tsx` -- full convention form
21. [x] `frontend/.../ReferenceNumbersTab.tsx` -- module selector + all sub-components
22. [x] `frontend/.../SettingsPage.tsx` -- added "Reference Numbers" tab
23. [x] `backend/app/models/__init__.py` -- bug fix: added missing imports
24. [x] Documentation -- `database_structure.md`, `web-api.md`, `version_update.md`

---

## 10. Open Questions (RESOLVED)

| # | Question | Resolution |
|---|---|---|
| 1 | Global or per-warehouse counter? | **Global** -- per-warehouse adds warehouse_id FK, deferred to future |
| 2 | Manual barcode override in UI? | **Yes** -- with explicit "Edit" unlock to prevent accidental overwrite |
| 3 | Barcode in Items List table? | Deferred to ItemFormPage integration task |
| 4 | Generation during bulk Excel import? | Yes, if `auto_apply_on_create = true` in active ITEMS convention |
| 5 | Gapless mode needed in v1? | **No** -- all v1 modules are operational IDs; gapless available but not required |
| 6 | GS1 prefix storage? | **Per-module** in `sys_sequence_config.gs1_company_prefix` |
| 7 | Counter on version rollback? | Counter is **NOT** rolled back -- offset is preserved; restored convention resumes from current `global_seq` |

---

## 11. Future Phase Roadmap

| Phase | Feature |
|---|---|
| Next | ItemFormPage integration: barcode field + generate button in edit mode |
| Next | Barcode image rendering: Code-128 / QR SVG from reference string |
| Future | Print label module: configurable label template -> PDF |
| Future | Full SSCC-18 support: Extension Digit, 18-digit enforcement |
| Future | Redis-backed distributed counter for high-concurrency warehouses |

---

## 12. Files NOT to Touch

- `backend/tests/` -- no test files committed (proprietary data)
- `.env` -- no secrets in version control
- `backend/app/migrations/` -- DEPRECATED SQL folder, reference only

---

*Plan completed -- v0.6.2 Reference Number Generation Engine fully implemented 2026-03-15.*
