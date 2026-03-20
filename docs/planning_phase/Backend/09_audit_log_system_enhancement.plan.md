# Audit Log System Enhancement — Technical Plan

> **Version:** PRE-ALPHA v0.6.0 (Planned)
> **Created:** 2026-03-11
> **Status:** PLANNING
> **Scope:** Database triggers, backend API, frontend UI, soft-restore mechanism

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Gap Analysis](#2-gap-analysis)
3. [Database Schema Design](#3-database-schema-design)
4. [Change Tracking via Triggers](#4-change-tracking-via-triggers)
5. [Restore Mechanism](#5-restore-mechanism)
6. [Backend API Endpoints](#6-backend-api-endpoints)
7. [Frontend Components](#7-frontend-components)
8. [Migration Strategy](#8-migration-strategy)
9. [Security Considerations](#9-security-considerations)
10. [Implementation Phases](#10-implementation-phases)

---

## 1. Current State Analysis

### What Already Exists

| Component | Location | Coverage |
|---|---|---|
| **AuditLog model** | `backend/app/models/users.py:137-223` | Table defined with `old_data`/`new_data` JSONB, `changed_by_user_id` FK, `action_id` FK |
| **ActionType lookup** | `backend/app/models/users.py:22-40` | 9 seeded types: INSERT, UPDATE, DELETE, SOFT_DELETE, RESTORE, LOGIN, LOGOUT, EXPORT, IMPORT |
| **ItemsHistory model** | `backend/app/models/items.py:219-279` | Per-item version snapshots with `snapshot_data` JSONB |
| **Items audit triggers** | `backend/app/models/triggers.py:414-557` | AFTER INSERT/UPDATE on `items` → auto-inserts into `items_history` |
| **Soft-delete fields** | 7 models | `deleted_at` + `deleted_by` on Item, Warehouse, InventoryLocation, ItemType, Category, Brand, BaseUOM |
| **GIN indexes** | AuditLog | `idx_audit_old_data_gin`, `idx_audit_new_data_gin` on JSONB columns |

### What's Working

- Items table has **full** trigger-based history tracking (INSERT + UPDATE + SOFT_DELETE + RESTORE)
- AuditLog table schema supports system-wide tracking with JSONB diff storage
- ActionType lookup normalises action labels
- Soft-delete pattern is consistent across 7 models

### What's Missing

The **AuditLog table is defined but never populated**. No triggers, no application-level code, and no API endpoints write to it. ItemsHistory is populated by triggers, but audit_log itself is an empty table. There is no restore API. There is no frontend for viewing logs.

---

## 2. Gap Analysis

| Gap | Impact | Priority |
|---|---|---|
| **No universal audit triggers** — only `items` has AFTER INSERT/UPDATE triggers; 48 other tables are untracked | Changes to warehouses, orders, users, inventory, etc. are invisible | **P0** |
| **AuditLog table never written to** — no trigger or app code inserts rows | The table exists but has zero rows; it's dead schema | **P0** |
| **No user context in triggers** — PostgreSQL triggers can't access the FastAPI session's user_id without session variables | `changed_by_user_id` will always be NULL in trigger-based writes | **P0** |
| **No restore endpoint** — soft-deleted records can only be restored by direct DB UPDATE | Admins cannot self-service undo mistakes | **P1** |
| **No audit API endpoints** — no router to query audit_log | Frontend cannot display history | **P1** |
| **No frontend audit viewer** — no UI to browse/filter/restore | Users have no visibility into what changed | **P1** |
| **`history_id` FK couples AuditLog to items_history** — limits extensibility to other tables | Adding per-table history tables would require new FK columns or a polymorphic approach | **P2** |
| **No retention policy** — audit_log will grow unbounded | Performance degradation over time | **P3** |

---

## 3. Database Schema Design

### 3.1 Enhanced AuditLog Table

The existing `audit_log` table schema is already well-designed. We enhance it with two new columns and make `changed_by_user_id` **mandatory for data mutations** (nullable only for system-initiated actions like triggers during migrations).

```
audit_log (ENHANCED)
├── audit_id          SERIAL PRIMARY KEY
├── table_name        VARCHAR(100) NOT NULL  [indexed]  -- e.g. "items", "warehouse"
├── record_id         VARCHAR(100)           [indexed]  -- PK of changed record (string for composite keys)
├── action_id         INT NOT NULL FK→action_type(action_id)  [indexed]
├── old_data          JSONB                  [GIN index] -- full row snapshot BEFORE change (NULL for INSERT)
├── new_data          JSONB                  [GIN index] -- full row snapshot AFTER change (NULL for DELETE)
├── changed_fields    TEXT[]                 [NEW] -- array of column names that changed (UPDATE only)
├── changed_by_user_id INT FK→users(user_id) [indexed]  -- who performed the action
├── changed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()  [indexed]
├── ip_address        VARCHAR(50)            -- request IP
├── user_agent        VARCHAR(500)           -- browser/client info
├── restore_source_audit_id  INT FK→audit_log(audit_id)  [NEW] -- if this row was created by a RESTORE, points to the audit entry being reverted
├── history_id        INT FK→items_history(history_id)    -- kept for backward compat, will be deprecated
└── __table_args__
    ├── idx_audit_table_record     (table_name, record_id)  -- composite for record history lookups
    ├── idx_audit_changed_at_desc  (changed_at DESC)        -- chronological browsing
    ├── idx_audit_old_data_gin     (old_data) USING gin     -- JSONB queries
    └── idx_audit_new_data_gin     (new_data) USING gin     -- JSONB queries
```

**New columns explained:**

| Column | Type | Why |
|---|---|---|
| `changed_fields` | `TEXT[]` | Fast filtering: "show me all audit entries that changed `item_name`" without parsing JSONB. Populated only for UPDATE actions. |
| `restore_source_audit_id` | `INT` (self-FK) | Creates a chain: when an admin restores a record, the new RESTORE audit entry points back to the original audit entry that captured the state being reverted. Enables "undo of undo" traceability. |

### 3.2 Deprecating history_id FK

The `history_id` column coupling `audit_log` → `items_history` is architecturally limiting. Plan:

1. **Phase 1:** Keep `history_id` as-is (nullable, no new writes)
2. **Phase 2:** Stop writing to `history_id` in items triggers
3. **Phase 3:** Drop column in a future migration once confirmed unused

**Rationale:** `audit_log` should be the single source of truth for all change history. `items_history` remains as a denormalised read-optimisation for the items module but is no longer the canonical audit record.

### 3.3 ActionType Additions

Add one new action type to the existing 9:

| action_id | action_name | description |
|---|---|---|
| 10 | `RESTORE_DATA` | "Record data restored from audit log to previous state" |

**Why separate from RESTORE (5)?** The existing `RESTORE` means "soft-delete reversed" (setting `deleted_at = NULL`). `RESTORE_DATA` means "field values reverted to a previous snapshot" — a data-level undo, not a soft-delete undo. They have different semantics and different security implications.

---

## 4. Change Tracking via Triggers

### 4.1 Architecture Decision: Universal Audit Trigger Function

Instead of writing one trigger function per table (which would require 49+ functions), we create a **single generic PL/pgSQL function** that works on any table via `TG_TABLE_NAME`, `TG_OP`, and `row_to_json()`.

```sql
CREATE OR REPLACE FUNCTION audit_log_trigger_fn()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data  JSONB;
    v_new_data  JSONB;
    v_action_id INT;
    v_record_id TEXT;
    v_user_id   INT;
    v_changed   TEXT[];
    v_key       TEXT;
BEGIN
    -- ---------------------------------------------------------------
    -- 1. Resolve user_id from session variable (set by FastAPI middleware)
    -- ---------------------------------------------------------------
    BEGIN
        v_user_id := current_setting('app.current_user_id', true)::INT;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    -- ---------------------------------------------------------------
    -- 2. Determine action and build data snapshots
    -- ---------------------------------------------------------------
    IF TG_OP = 'INSERT' THEN
        v_new_data  := row_to_json(NEW)::JSONB;
        v_old_data  := NULL;
        v_action_id := 1;  -- INSERT
        -- Extract record PK (column name passed as trigger arg)
        v_record_id := v_new_data ->> TG_ARGV[0];

    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := row_to_json(OLD)::JSONB;
        v_new_data := row_to_json(NEW)::JSONB;
        v_record_id := v_old_data ->> TG_ARGV[0];

        -- Detect soft-delete vs. restore vs. regular update
        IF v_old_data->>'deleted_at' IS NULL AND v_new_data->>'deleted_at' IS NOT NULL THEN
            v_action_id := 4;  -- SOFT_DELETE
        ELSIF v_old_data->>'deleted_at' IS NOT NULL AND v_new_data->>'deleted_at' IS NULL THEN
            v_action_id := 5;  -- RESTORE
        ELSE
            v_action_id := 2;  -- UPDATE
        END IF;

        -- Build changed_fields array
        v_changed := ARRAY[]::TEXT[];
        FOR v_key IN SELECT jsonb_object_keys(v_new_data)
        LOOP
            IF v_old_data->v_key IS DISTINCT FROM v_new_data->v_key THEN
                v_changed := array_append(v_changed, v_key);
            END IF;
        END LOOP;

    ELSIF TG_OP = 'DELETE' THEN
        v_old_data  := row_to_json(OLD)::JSONB;
        v_new_data  := NULL;
        v_action_id := 3;  -- DELETE
        v_record_id := v_old_data ->> TG_ARGV[0];
    END IF;

    -- ---------------------------------------------------------------
    -- 3. Skip audit if nothing actually changed (UPDATE with same values)
    -- ---------------------------------------------------------------
    IF TG_OP = 'UPDATE' AND v_old_data = v_new_data THEN
        RETURN NEW;
    END IF;

    -- ---------------------------------------------------------------
    -- 4. Insert audit record
    -- ---------------------------------------------------------------
    INSERT INTO audit_log (
        table_name, record_id, action_id,
        old_data, new_data, changed_fields,
        changed_by_user_id, changed_at
    ) VALUES (
        TG_TABLE_NAME, v_record_id, v_action_id,
        v_old_data, v_new_data, v_changed,
        v_user_id, NOW()
    );

    -- ---------------------------------------------------------------
    -- 5. Return appropriate row
    -- ---------------------------------------------------------------
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

### 4.2 Trigger Attachment — Per Table

Each audited table gets a single trigger that calls the universal function, passing the **primary key column name** as an argument:

```sql
-- Items
CREATE TRIGGER trg_audit_items
    AFTER INSERT OR UPDATE OR DELETE ON items
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('item_id');

-- Warehouse
CREATE TRIGGER trg_audit_warehouse
    AFTER INSERT OR UPDATE OR DELETE ON warehouse
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('warehouse_id');

-- Inventory Levels
CREATE TRIGGER trg_audit_inventory_levels
    AFTER INSERT OR UPDATE OR DELETE ON inventory_levels
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('inventory_level_id');

-- Inventory Locations
CREATE TRIGGER trg_audit_inventory_location
    AFTER INSERT OR UPDATE OR DELETE ON inventory_location
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('location_id');

-- Orders
CREATE TRIGGER trg_audit_orders
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('order_id');

-- Order Details
CREATE TRIGGER trg_audit_order_details
    AFTER INSERT OR UPDATE OR DELETE ON order_details
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('order_detail_id');

-- Users
CREATE TRIGGER trg_audit_users
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('user_id');

-- Platforms
CREATE TRIGGER trg_audit_platform
    AFTER INSERT OR UPDATE OR DELETE ON platform
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('platform_id');

-- Sellers
CREATE TRIGGER trg_audit_sellers
    AFTER INSERT OR UPDATE OR DELETE ON sellers
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('seller_id');

-- Roles
CREATE TRIGGER trg_audit_roles
    AFTER INSERT OR UPDATE OR DELETE ON roles
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('role_id');

-- Item Types
CREATE TRIGGER trg_audit_item_type
    AFTER INSERT OR UPDATE OR DELETE ON item_type
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('item_type_id');

-- Categories
CREATE TRIGGER trg_audit_category
    AFTER INSERT OR UPDATE OR DELETE ON category
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('category_id');

-- Brands
CREATE TRIGGER trg_audit_brand
    AFTER INSERT OR UPDATE OR DELETE ON brand
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('brand_id');

-- Base UOM
CREATE TRIGGER trg_audit_base_uom
    AFTER INSERT OR UPDATE OR DELETE ON base_uom
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger_fn('uom_id');
```

**Tables to audit (priority order):**

| Priority | Tables | Rationale |
|---|---|---|
| **P0 — Core data** | `items`, `warehouse`, `inventory_levels`, `inventory_location`, `orders`, `order_details` | Primary business data — must track all changes |
| **P1 — Users & config** | `users`, `roles`, `platform`, `sellers`, `seller_warehouses` | Security and config changes |
| **P2 — Operations** | `inventory_transactions`, `inventory_movements`, `inventory_alerts`, `delivery_trips`, `delivery_trip_items` | Operational data — high volume, may need retention policy |
| **P3 — Reference** | `item_type`, `category`, `brand`, `base_uom`, `action_type`, `movement_type` | Rarely change; audit for compliance |
| **Skip** | `audit_log`, `items_history`, `order_import_staging`, `platform_raw_imports` | Audit tables should not audit themselves; staging/import tables are transient |

### 4.3 User Context Propagation (Critical Design)

PostgreSQL triggers cannot access FastAPI's request context. We solve this with **session-level variables** set by a new dependency.

**New FastAPI Dependency** (`backend/app/dependencies/audit.py`):

```python
"""
Audited session dependency.

Injects PostgreSQL session-level variables so that the universal audit trigger
can attribute changes to the authenticated user. Uses SET LOCAL to scope
variables to the current transaction — safe for connection pooling.
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.dependencies.auth import require_current_user
from app.models.users import User


async def get_audited_session(
    request: Request,
    current_user: User = Depends(require_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Database session with audit context variables set.

    Sets three PostgreSQL session variables via SET LOCAL:
      - app.current_user_id  → user's PK (read by audit trigger)
      - app.current_ip       → client IP address
      - app.current_user_agent → User-Agent header (truncated to 500 chars)

    SET LOCAL scopes variables to the current transaction only.
    After COMMIT or ROLLBACK, variables are automatically cleared.
    This is essential for connection pool safety — no user context
    leaks between requests sharing the same pooled connection.
    """
    async with async_session_maker() as session:
        try:
            # Inject user context for audit triggers
            await session.execute(
                text("SET LOCAL app.current_user_id = :uid"),
                {"uid": str(current_user.user_id)}
            )

            ip = request.client.host if request.client else "unknown"
            await session.execute(
                text("SET LOCAL app.current_ip = :ip"),
                {"ip": ip}
            )

            ua = (request.headers.get("user-agent") or "")[:500]
            if ua:
                await session.execute(
                    text("SET LOCAL app.current_user_agent = :ua"),
                    {"ua": ua}
                )

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Why a separate dependency instead of modifying `get_session()`?**
- `get_session()` is used by ~50+ endpoints including read-only ones that don't need auth
- Changing its signature would require updating every router
- `get_audited_session()` is opt-in: only write endpoints that need user attribution switch to it
- Read-only endpoints keep using the lightweight `get_session()`

**Fallback for unauthenticated actions:** Some operations (seed data, migrations, system cron) have no user. The trigger handles this gracefully — `current_setting('app.current_user_id', true)` returns NULL when unset (the `true` parameter means "return NULL on missing, don't error").

---

## 5. Restore Mechanism

### 5.1 Restore Types

| Type | Description | Example |
|---|---|---|
| **Soft-restore** | Un-delete a soft-deleted record (set `deleted_at = NULL`) | Admin restores a deleted warehouse |
| **Data-restore** | Revert a record's field values to a previous state captured in `old_data` | Admin reverts an item's name change |
| **Full-restore** | Combination: un-delete AND revert to last known good state | Admin restores a deleted + previously modified item to its original state |

### 5.2 Restore Logic Flow

```
Admin clicks "Restore" on audit entry #42
         │
         ▼
┌─────────────────────────────────────────┐
│  1. VALIDATE                            │
│  - Is audit_id #42 valid?               │
│  - Does the table_name still exist?     │
│  - Does record_id still exist in table? │
│  - Is the requesting user authorised?   │
│     (role = Super Admin or Admin)       │
│  - Is old_data non-NULL? (can't restore │
│    an INSERT — there's no "before")     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  2. BUILD RESTORE PAYLOAD               │
│  - Source: audit_log.old_data (JSONB)   │
│  - Strip non-restorable fields:         │
│    • Primary keys (never overwrite)     │
│    • created_at (immutable)             │
│    • updated_at (auto-managed)          │
│    • password_hash (security)           │
│  - Result: clean dict of restorable     │
│    column → value pairs                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  3. EXECUTE RESTORE                     │
│  - BEGIN TRANSACTION                    │
│  - SET LOCAL app.current_user_id = ?    │
│  - UPDATE <table> SET col1=v1, col2=v2  │
│    WHERE <pk_col> = <record_id>         │
│  - The UPDATE fires the audit trigger → │
│    automatically creates a new audit_log│
│    row with action_id = RESTORE or      │
│    RESTORE_DATA                         │
│  - COMMIT                               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  4. RECORD LINEAGE                      │
│  - The new audit entry's                │
│    restore_source_audit_id = 42         │
│  - Application code sets this after the │
│    trigger fires (UPDATE audit_log SET  │
│    restore_source_audit_id = 42 WHERE   │
│    audit_id = <new_entry>)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  5. RETURN RESULT                       │
│  - 200 OK with restored record data     │
│  - Include new audit_id for reference   │
└─────────────────────────────────────────┘
```

### 5.3 Non-Restorable Fields (Blocklist)

These fields are **never overwritten** during a restore, regardless of what `old_data` contains:

```python
# backend/app/services/audit/restore.py

NON_RESTORABLE_FIELDS = {
    # Primary keys — identity must never change
    "item_id", "warehouse_id", "order_id", "order_detail_id", "user_id",
    "location_id", "inventory_level_id", "platform_id", "seller_id",
    "role_id", "action_id", "audit_id", "history_id",

    # Immutable timestamps
    "created_at",

    # Auto-managed timestamps (triggers handle these)
    "updated_at",

    # Security-sensitive fields (require separate password reset flow)
    "password_hash",

    # Audit metadata (circular dependency prevention)
    "deleted_by",  # Will be set to NULL if restoring from soft-delete
}
```

### 5.4 Table-Specific Restore Configuration

```python
# Maps table_name → (model_class, pk_column, allowed_restore_fields | None)
# If allowed_restore_fields is None, all non-blocklisted fields are restorable

RESTORE_REGISTRY = {
    "items": (Item, "item_id", None),
    "warehouse": (Warehouse, "warehouse_id", None),
    "inventory_location": (InventoryLocation, "location_id", None),
    "inventory_levels": (InventoryLevel, "inventory_level_id", {
        "quantity_available", "quantity_reserved", "quantity_on_order",
        "reorder_point", "safety_stock", "max_stock", "is_active"
    }),
    "orders": (Order, "order_id", None),
    "order_details": (OrderDetail, "order_detail_id", None),
    "users": (User, "user_id", {
        "username", "email", "first_name", "last_name",
        "role_id", "is_active", "is_superuser"
    }),
    "platform": (Platform, "platform_id", None),
    "sellers": (Seller, "seller_id", None),
    "item_type": (ItemType, "item_type_id", None),
    "category": (Category, "category_id", None),
    "brand": (Brand, "brand_id", None),
    "base_uom": (BaseUOM, "uom_id", None),
}
```

### 5.5 Restore Service Implementation

```python
# backend/app/services/audit/restore.py

class RestoreService:
    """
    Service for restoring records to a previous state using audit log data.

    The restore process:
    1. Validates the audit entry and user permissions
    2. Builds a filtered payload from old_data (excluding non-restorable fields)
    3. Applies the update within an audited transaction (triggering a new audit entry)
    4. Links the new audit entry back to the source via restore_source_audit_id
    """

    async def preview_restore(
        self,
        session: AsyncSession,
        audit_id: int,
        requesting_user: User,
    ) -> dict:
        """
        Dry-run: shows what would change without applying.

        Returns:
            Dict with current_values, restore_to_values, fields_to_change, warnings
        """
        audit_entry = await self._validate_audit_entry(session, audit_id, requesting_user)
        config = RESTORE_REGISTRY[audit_entry.table_name]
        model_class, pk_col, allowed_fields = config

        # Build restore payload
        restore_data = self._build_restore_payload(audit_entry.old_data, allowed_fields)

        # Fetch current record state
        record = await self._fetch_record(session, model_class, pk_col, audit_entry.record_id)
        current_values = {field: getattr(record, field) for field in restore_data}

        # Compute diff
        fields_to_change = []
        warnings = []
        for field, old_value in restore_data.items():
            current = current_values.get(field)
            if current != old_value:
                fields_to_change.append({
                    "field": field,
                    "current_value": current,
                    "restore_to_value": old_value,
                })

        # Detect soft-delete restore
        if (audit_entry.old_data.get("deleted_at") is None
                and hasattr(record, "deleted_at")
                and record.deleted_at is not None):
            warnings.append("Record is currently soft-deleted and will be un-deleted")

        return {
            "audit_id": audit_id,
            "table_name": audit_entry.table_name,
            "record_id": audit_entry.record_id,
            "current_values": current_values,
            "restore_to_values": restore_data,
            "fields_to_change": fields_to_change,
            "warnings": warnings,
        }

    async def restore_from_audit(
        self,
        session: AsyncSession,
        audit_id: int,
        requesting_user: User,
        fields_to_restore: Optional[list[str]] = None,
    ) -> dict:
        """
        Restore a record to its state captured in audit_log.old_data.

        Args:
            audit_id: The audit entry whose old_data to restore from
            requesting_user: Must be Admin or Super Admin
            fields_to_restore: Optional subset of fields; if None, restores all

        Returns:
            Dict with restored record data, source_audit_id, new_audit_id,
            and list of fields_restored

        Raises:
            PermissionError: User lacks restore permission
            ValueError: Invalid audit_id, missing old_data, or unknown table
            RecordNotFoundError: Target record no longer exists
        """
        # 1. Validate
        audit_entry = await self._validate_audit_entry(session, audit_id, requesting_user)
        config = RESTORE_REGISTRY[audit_entry.table_name]
        model_class, pk_col, allowed_fields = config

        # 2. Build payload
        restore_data = self._build_restore_payload(
            audit_entry.old_data, allowed_fields, fields_to_restore
        )
        if not restore_data:
            raise ValueError("No restorable fields found in old_data")

        # 3. Fetch and update target record
        record = await self._fetch_record(session, model_class, pk_col, audit_entry.record_id)

        for field, value in restore_data.items():
            setattr(record, field, value)

        # Handle soft-delete restore: clear deleted_at and deleted_by
        if (audit_entry.old_data.get("deleted_at") is None
                and hasattr(record, "deleted_at")
                and record.deleted_at is not None):
            record.deleted_at = None
            if hasattr(record, "deleted_by"):
                record.deleted_by = None

        await session.flush()

        # 4. Link the new audit entry to the source
        new_audit = await session.execute(
            select(AuditLog)
            .where(AuditLog.table_name == audit_entry.table_name)
            .where(AuditLog.record_id == audit_entry.record_id)
            .order_by(AuditLog.audit_id.desc())
            .limit(1)
        )
        new_audit_entry = new_audit.scalar_one_or_none()
        if new_audit_entry and new_audit_entry.audit_id != audit_id:
            new_audit_entry.restore_source_audit_id = audit_id

        return {
            "message": f"Record restored successfully",
            "source_audit_id": audit_id,
            "new_audit_id": new_audit_entry.audit_id if new_audit_entry else None,
            "fields_restored": list(restore_data.keys()),
        }

    # ---- Private helpers ----

    async def _validate_audit_entry(self, session, audit_id, user):
        if user.role.role_name not in ("Super Admin", "Admin"):
            raise PermissionError("Only Admin or Super Admin can restore records")

        audit_entry = await session.get(AuditLog, audit_id)
        if not audit_entry:
            raise ValueError(f"Audit entry #{audit_id} not found")
        if not audit_entry.old_data:
            raise ValueError("No previous state to restore (INSERT entries have no old_data)")
        if audit_entry.table_name not in RESTORE_REGISTRY:
            raise ValueError(f"Table '{audit_entry.table_name}' is not restorable")

        return audit_entry

    def _build_restore_payload(self, old_data, allowed_fields, subset=None):
        restore_data = {}
        for field, value in old_data.items():
            if field in NON_RESTORABLE_FIELDS:
                continue
            if allowed_fields and field not in allowed_fields:
                continue
            if subset and field not in subset:
                continue
            restore_data[field] = value
        return restore_data

    async def _fetch_record(self, session, model_class, pk_col, record_id):
        result = await session.execute(
            select(model_class).where(
                getattr(model_class, pk_col) == int(record_id)
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError(f"Record #{record_id} no longer exists in database")
        return record
```

---

## 6. Backend API Endpoints

### 6.1 New Router: `backend/app/routers/audit.py`

**Prefix:** `/api/v1/audit`
**Auth:** All endpoints require `require_current_user` dependency (JWT)

| Method | Path | Purpose | Auth Level |
|---|---|---|---|
| `GET` | `/logs` | Paginated list of audit entries with filters | Staff+ |
| `GET` | `/logs/{audit_id}` | Single audit entry with full old/new data | Staff+ |
| `GET` | `/logs/record/{table_name}/{record_id}` | All audit entries for a specific record | Staff+ |
| `GET` | `/logs/user/{user_id}` | All changes by a specific user | Manager+ |
| `GET` | `/logs/summary` | Aggregated stats (changes per table, per day) | Manager+ |
| `POST` | `/restore/{audit_id}` | Restore a record from audit entry's old_data | Admin+ |
| `POST` | `/restore/{audit_id}/preview` | Dry-run: show what would change without applying | Admin+ |
| `GET` | `/action-types` | List all action types for filter dropdowns | Staff+ |

### 6.2 Query Parameters for `GET /logs`

```python
class AuditLogQuery(BaseModel):
    """Query parameters for paginated audit log listing."""
    # Pagination
    page: int = 1
    page_size: int = 25

    # Filters
    table_name: Optional[str] = None       # e.g. "items"
    action_name: Optional[str] = None      # e.g. "UPDATE", "SOFT_DELETE"
    record_id: Optional[str] = None        # e.g. "42"
    changed_by_user_id: Optional[int] = None

    # Date range
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    # Field-level filter
    changed_field: Optional[str] = None    # e.g. "item_name" — filters via changed_fields array

    # Search in JSONB
    search: Optional[str] = None           # full-text search across old_data/new_data values

    # Sort
    sort_by: str = "changed_at"
    sort_order: str = "desc"               # "asc" or "desc"
```

### 6.3 Response Schemas

```python
# backend/app/schemas/audit.py

class FieldDiff(BaseModel):
    """Single field change between old and new state."""
    field: str
    old_value: Any
    new_value: Any

class AuditLogResponse(BaseModel):
    """Standard audit log entry response."""
    audit_id: int
    table_name: str
    record_id: Optional[str]
    action_name: str           # Resolved from ActionType join
    action_id: int
    old_data: Optional[dict]
    new_data: Optional[dict]
    changed_fields: Optional[list[str]]
    changed_by_user_id: Optional[int]
    changed_by_username: Optional[str]  # Resolved from User join
    changed_at: datetime
    ip_address: Optional[str]
    restore_source_audit_id: Optional[int]
    is_restorable: bool        # Computed: old_data is not None and table in RESTORE_REGISTRY

class AuditLogDetailResponse(AuditLogResponse):
    """Extended response with diff computation."""
    diff: Optional[list[FieldDiff]]  # Computed field-by-field diff

class RestorePreviewResponse(BaseModel):
    """Preview of what a restore operation would change."""
    audit_id: int
    table_name: str
    record_id: str
    current_values: dict       # What the record looks like NOW
    restore_to_values: dict    # What it will look like AFTER restore
    fields_to_change: list[FieldDiff]
    warnings: list[str]        # e.g. "Record is currently soft-deleted, will be un-deleted"

class RestoreResultResponse(BaseModel):
    """Result of a successful restore operation."""
    message: str
    source_audit_id: int
    new_audit_id: int
    fields_restored: list[str]

class AuditSummaryResponse(BaseModel):
    """Aggregated audit statistics."""
    total_entries: int
    by_table: dict[str, int]
    by_action: dict[str, int]
    by_day: list[dict]         # [{date, count}, ...]
    top_users: list[dict]      # [{user_id, username, count}, ...]
```

---

## 7. Frontend Components

### 7.1 Page Structure

Following the project convention (page-specific files in `frontend/src/pages/<module>/`):

```
frontend/src/pages/audit/
├── AuditLogPage.tsx           # Main page — table + filters + detail drawer
├── AuditLogPage.css           # Styling (Tailwind utilities + custom)
├── AuditFilters.tsx           # Filter bar: table, action, user, date range
├── AuditTable.tsx             # Paginated table of audit entries
├── AuditDetailDrawer.tsx      # Slide-out panel showing full diff for one entry
├── AuditDiffViewer.tsx        # Side-by-side or inline diff of old_data vs new_data
├── RestoreConfirmModal.tsx    # Confirmation dialog before restore
├── RestorePreviewPanel.tsx    # Shows preview of what will change
├── RecordTimeline.tsx         # Timeline view of all changes to a single record
├── audit.types.ts             # TypeScript interfaces
└── audit.utils.ts             # Helpers (diff formatting, field label mapping)
```

### 7.2 Component Details

#### AuditLogPage (Main Entry)

- **Route:** `/audit/logs`
- **Layout:** Full-width with left filter sidebar (collapsible) + main table area
- **Behaviour:**
  - On mount: fetch `/audit/logs?page=1&page_size=25&sort_by=changed_at&sort_order=desc`
  - URL params synced with filters (shareable URLs)
  - Clicking a row opens `AuditDetailDrawer`
  - "View Record History" button navigates to `RecordTimeline` for that record

#### AuditFilters

- **Table selector:** Dropdown of all audited table names (fetched from summary endpoint)
- **Action selector:** Multi-select chips (INSERT, UPDATE, SOFT_DELETE, RESTORE, etc.)
- **User selector:** Searchable dropdown of users
- **Date range:** Two date pickers (from/to) with presets (Today, Last 7 days, Last 30 days)
- **Changed field:** Text input with autocomplete (populated from `changed_fields` array values)
- **Search:** Free-text search across JSONB values
- **Reset button:** Clears all filters

#### AuditTable

- **Columns:** Timestamp | Table | Record ID | Action | Changed By | Changed Fields | Actions
- **Action column:** "View Details" button, "Restore" button (visible only if `is_restorable && user.role in [Admin, Super Admin]`)
- **Action badges:** Color-coded by action type:
  - INSERT → green
  - UPDATE → blue
  - SOFT_DELETE → amber/orange
  - DELETE → red
  - RESTORE → teal
  - RESTORE_DATA → purple
- **Pagination:** Standard with page size selector (10, 25, 50, 100)

#### AuditDiffViewer

- **Mode toggle:** Side-by-side | Inline (like GitHub diff)
- **Display:**
  - For each field in `changed_fields`:
    - Show field label (human-readable via `audit.utils.ts` mapping)
    - Old value (red background) → New value (green background)
  - Unchanged fields: collapsed by default, expandable
  - JSONB nested fields: rendered as formatted JSON with syntax highlighting
- **Special handling:**
  - `password_hash` → shown as `[REDACTED]` (never display hashes)
  - `deleted_at` → shown as "Soft-deleted" / "Active" instead of raw timestamp
  - `variations_data` / `address` → collapsible JSON tree

#### RestoreConfirmModal

- **Trigger:** Click "Restore" on an audit entry
- **Step 1:** Calls `POST /audit/restore/{audit_id}/preview` → shows `RestorePreviewPanel`
- **Step 2:** User reviews the diff (current state vs. restore target)
- **Step 3:** User types "RESTORE" in a confirmation input (prevents accidental clicks)
- **Step 4:** Calls `POST /audit/restore/{audit_id}` → shows success/error toast
- **Step 5:** Refreshes the audit table to show the new RESTORE_DATA entry

#### RecordTimeline

- **Route:** `/audit/logs/record/:tableName/:recordId`
- **Display:** Vertical timeline (newest at top) showing every change to one record
- **Each node:** timestamp, user avatar + name, action badge, expandable diff
- **Visual:** Connected by a vertical line; restore entries shown with a "revert arrow" icon
- **Navigation:** Breadcrumb back to main audit page

### 7.3 Sidebar Navigation

Add under a new "System" section in the sidebar:

```
System
├── Audit Logs       → /audit/logs
└── Settings         → /settings    (existing)
```

### 7.4 API Client

```typescript
// frontend/src/api/base/audit.ts

export const auditApi = {
  getLogs: (params: AuditLogQuery) =>
    client.get<PaginatedResponse<AuditLogResponse>>('/audit/logs', { params }),

  getLogDetail: (auditId: number) =>
    client.get<AuditLogDetailResponse>(`/audit/logs/${auditId}`),

  getRecordHistory: (tableName: string, recordId: string, params?: PaginationParams) =>
    client.get<PaginatedResponse<AuditLogResponse>>(
      `/audit/logs/record/${tableName}/${recordId}`, { params }
    ),

  getUserActivity: (userId: number, params?: PaginationParams) =>
    client.get<PaginatedResponse<AuditLogResponse>>(
      `/audit/logs/user/${userId}`, { params }
    ),

  getSummary: () =>
    client.get<AuditSummaryResponse>('/audit/summary'),

  getActionTypes: () =>
    client.get<ActionType[]>('/audit/action-types'),

  previewRestore: (auditId: number) =>
    client.post<RestorePreviewResponse>(`/audit/restore/${auditId}/preview`),

  executeRestore: (auditId: number, fields?: string[]) =>
    client.post<RestoreResultResponse>(`/audit/restore/${auditId}`, { fields }),
};
```

---

## 8. Migration Strategy

### 8.1 Alembic Migration

**File:** `backend/alembic/versions/20260311_1000_00_h3i4j5k6l7m8_audit_log_enhancement.py`

```python
"""Audit log enhancement: changed_fields, restore_source_audit_id, new action type

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
"""

def upgrade():
    # 1. Add new columns to audit_log
    op.add_column('audit_log', sa.Column('changed_fields', sa.ARRAY(sa.Text()), nullable=True))
    op.add_column('audit_log', sa.Column(
        'restore_source_audit_id', sa.Integer(),
        sa.ForeignKey('audit_log.audit_id'), nullable=True
    ))

    # 2. Add composite index for record history lookups
    op.create_index('idx_audit_table_record', 'audit_log', ['table_name', 'record_id'])
    op.create_index('idx_audit_changed_at_desc', 'audit_log', [sa.text('changed_at DESC')])

    # 3. Insert new action type
    op.execute("""
        INSERT INTO action_type (action_name, description)
        VALUES ('RESTORE_DATA', 'Record data restored from audit log to previous state')
        ON CONFLICT (action_name) DO NOTHING
    """)

def downgrade():
    op.execute("DELETE FROM action_type WHERE action_name = 'RESTORE_DATA'")
    op.drop_index('idx_audit_changed_at_desc', 'audit_log')
    op.drop_index('idx_audit_table_record', 'audit_log')
    op.drop_column('audit_log', 'restore_source_audit_id')
    op.drop_column('audit_log', 'changed_fields')
```

### 8.2 Trigger Deployment

Add the universal audit function + per-table triggers to `backend/app/models/triggers.py` in the `_TRIGGER_SQL` list. They'll be applied idempotently via `apply_triggers()` during `run_migrations()`.

### 8.3 Seed Update

Add `RESTORE_DATA` to `backend/app/models/seed.py` in the ActionType seed section.

---

## 9. Security Considerations

| Concern | Mitigation |
|---|---|
| **Audit log tampering** | Never expose UPDATE/DELETE endpoints for audit_log. The table is append-only from the application's perspective. DB-level: `REVOKE UPDATE, DELETE ON audit_log FROM woms_user` (grant only INSERT + SELECT). |
| **Password hash exposure** | `AuditDiffViewer` redacts `password_hash` to `[REDACTED]`. Backend also strips it in serialisation: the `AuditLogResponse` schema's `old_data`/`new_data` run through a sanitiser that replaces sensitive fields. |
| **Restore permissions** | Only `Admin` and `Super Admin` roles can call restore endpoints. Enforced at both API (dependency check) and frontend (button visibility) levels. |
| **Restore validation** | `NON_RESTORABLE_FIELDS` blocklist prevents restoring PKs, password hashes, or auto-managed timestamps. Per-table `allowed_restore_fields` whitelist further restricts sensitive tables like `users`. |
| **Connection pool leak** | `SET LOCAL` (not `SET`) scopes variables to the transaction. After commit/rollback, variables are cleared. No risk of user context leaking between pooled connections. |
| **Audit log volume** | P2/P3 tables (high-write operational tables) may need a retention policy. Future: add a `retention_days` config per table; a background job purges entries older than threshold. Not in scope for v0.6.0. |
| **JSONB size** | `row_to_json()` captures the full row. For tables with large JSONB fields (e.g. `raw_data` on imports), this could bloat audit_log. Mitigation: skip auditing `order_import_staging` and `platform_raw_imports`. |

---

## 10. Implementation Phases

### Phase 1 — Database Layer (Backend)

| Step | Task | Files |
|---|---|---|
| 1.1 | Add `changed_fields` and `restore_source_audit_id` columns to AuditLog model | `models/users.py` |
| 1.2 | Create Alembic migration for new columns + indexes | `alembic/versions/...` |
| 1.3 | Add `RESTORE_DATA` action type to seed | `models/seed.py` |
| 1.4 | Write universal `audit_log_trigger_fn()` in triggers.py | `models/triggers.py` |
| 1.5 | Attach triggers to P0 tables (items, warehouse, inventory, orders) | `models/triggers.py` |
| 1.6 | Test: INSERT/UPDATE/DELETE on items → verify audit_log populated | Manual SQL or pytest |

### Phase 2 — User Context Propagation (Backend)

| Step | Task | Files |
|---|---|---|
| 2.1 | Create `get_audited_session()` dependency | `dependencies/audit.py` |
| 2.2 | Update write routers to use `get_audited_session` for mutation endpoints | All write routers |
| 2.3 | Test: perform a mutation via API → verify `changed_by_user_id` is populated in audit_log | pytest or manual |

### Phase 3 — Restore Service (Backend)

| Step | Task | Files |
|---|---|---|
| 3.1 | Create `RestoreService` with `restore_from_audit()` and `preview_restore()` methods | `services/audit/restore.py` |
| 3.2 | Create audit schemas (query, response, preview, result) | `schemas/audit.py` |
| 3.3 | Create audit router with all endpoints | `routers/audit.py` |
| 3.4 | Register router in `main.py` | `main.py` |
| 3.5 | Test: restore an item from audit entry → verify record reverted + new audit entry created | pytest or manual |

### Phase 4 — Frontend: Audit Log Viewer

| Step | Task | Files |
|---|---|---|
| 4.1 | Create TypeScript types for audit API | `pages/audit/audit.types.ts` |
| 4.2 | Create API client functions | `api/base/audit.ts` |
| 4.3 | Build `AuditLogPage` with `AuditTable` and `AuditFilters` | `pages/audit/` |
| 4.4 | Build `AuditDetailDrawer` with `AuditDiffViewer` | `pages/audit/` |
| 4.5 | Add sidebar navigation entry | Sidebar component |
| 4.6 | Add routes in `App.tsx` | `App.tsx` |

### Phase 5 — Frontend: Restore UI

| Step | Task | Files |
|---|---|---|
| 5.1 | Build `RestorePreviewPanel` | `pages/audit/` |
| 5.2 | Build `RestoreConfirmModal` with confirmation input | `pages/audit/` |
| 5.3 | Build `RecordTimeline` view | `pages/audit/` |
| 5.4 | Wire restore flow: preview → confirm → execute → refresh | `pages/audit/` |

### Phase 6 — Extend to All Tables

| Step | Task | Files |
|---|---|---|
| 6.1 | Attach audit triggers to P1 tables (users, roles, platforms, sellers) | `models/triggers.py` |
| 6.2 | Attach audit triggers to P2 tables (transactions, movements, alerts, delivery) | `models/triggers.py` |
| 6.3 | Attach audit triggers to P3 tables (reference: item_type, category, brand, base_uom) | `models/triggers.py` |
| 6.4 | Update `RESTORE_REGISTRY` for newly audited tables | `services/audit/restore.py` |

---

## File Summary — All Files to Create/Modify

### New Files

| File | Purpose |
|---|---|
| `backend/app/services/audit/__init__.py` | Service package init |
| `backend/app/services/audit/restore.py` | Restore logic + registry + NON_RESTORABLE_FIELDS |
| `backend/app/schemas/audit.py` | Request/response schemas |
| `backend/app/routers/audit.py` | API endpoints |
| `backend/app/dependencies/audit.py` | `get_audited_session` dependency |
| `backend/alembic/versions/20260311_...` | Alembic migration |
| `frontend/src/pages/audit/AuditLogPage.tsx` | Main page |
| `frontend/src/pages/audit/AuditLogPage.css` | Styles |
| `frontend/src/pages/audit/AuditFilters.tsx` | Filter bar |
| `frontend/src/pages/audit/AuditTable.tsx` | Data table |
| `frontend/src/pages/audit/AuditDetailDrawer.tsx` | Detail panel |
| `frontend/src/pages/audit/AuditDiffViewer.tsx` | Diff viewer |
| `frontend/src/pages/audit/RestoreConfirmModal.tsx` | Restore modal |
| `frontend/src/pages/audit/RestorePreviewPanel.tsx` | Restore preview |
| `frontend/src/pages/audit/RecordTimeline.tsx` | Record timeline |
| `frontend/src/pages/audit/audit.types.ts` | TypeScript types |
| `frontend/src/pages/audit/audit.utils.ts` | Helpers |
| `frontend/src/api/base/audit.ts` | API client |

### Modified Files

| File | Change |
|---|---|
| `backend/app/models/users.py` | Add `changed_fields`, `restore_source_audit_id` to AuditLog |
| `backend/app/models/triggers.py` | Add universal audit trigger function + per-table trigger attachments |
| `backend/app/models/seed.py` | Add `RESTORE_DATA` action type |
| `backend/app/main.py` | Register audit router |
| `frontend/src/App.tsx` | Add audit routes |
| Sidebar component | Add "Audit Logs" nav item |

---

## Open Questions for Discussion

1. **ItemsHistory coexistence:** Should we keep the existing items-specific triggers (`trg_items_history_on_insert/update`) running alongside the new universal trigger? This would mean items changes write to BOTH `items_history` AND `audit_log`. Recommendation: keep both for now (items_history is a useful denormalised view), deprecate items_history in a future version.

2. **Retention policy:** Should we implement a retention policy in v0.6.0 or defer? Recommendation: defer to v0.7.0; the table won't grow significantly during pre-alpha.

3. **Real-time audit feed:** Should the audit page support WebSocket-based live updates? Recommendation: defer; polling with 30s refresh is sufficient for pre-alpha.

4. **Bulk restore:** Should we support restoring multiple records at once (e.g., "undo all changes made by user X in the last hour")? Recommendation: defer; single-record restore first.

5. **`get_session` signature change:** Modifying `get_session()` to accept `Request` changes the dependency signature for ALL routers. Alternative: create a separate `get_audited_session()` dependency used only by write endpoints, leaving `get_session()` untouched for read-only endpoints. Recommendation: use the separate dependency approach to minimise blast radius.
