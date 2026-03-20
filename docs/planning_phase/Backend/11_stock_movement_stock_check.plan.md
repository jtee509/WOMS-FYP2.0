# Backend Plan: Stock Movement Enhancement & Stock Check System

**Version:** PRE-ALPHA v0.6.x
**Created:** 2026-03-14
**Status:** Planning
**Related Frontend Plan:** `docs/planning_phase/Frontend/12_stock_movement_stock_check_frontend.plan.md`

---

## 1. Overview

This plan covers two backend features:

- **Feature A** — Multi-item inventory movement endpoint (upgrade from single-item)
- **Feature B** — Stock Check (cycle count) system with new models, migration, and router

Both features reuse the existing `InventoryMovement` / `InventoryTransaction` / `InventoryLevel` infrastructure and the DB trigger `update_inventory_on_transaction` that auto-updates stock levels on transaction INSERT.

**Key Decision:** Movements are immediately applied on submit (no Pending/Approved lifecycle). The existing DB trigger fires on INSERT to `inventory_transactions`, so stock updates are instant. Stock Check provides a structured review workflow where approval matters most.

---

## 2. Current State

### Existing Models (`backend/app/models/warehouse.py`)

| Model | Table | Key Fields | Role |
|-------|-------|------------|------|
| `InventoryMovement` | `inventory_movements` | id, movement_type_id (FK), reference_id, created_at | Groups transactions under a single operation |
| `InventoryTransaction` | `inventory_transactions` | id, item_id, location_id, movement_id, is_inbound, quantity_change, created_at | Individual stock change record |
| `InventoryLevel` | `inventory_levels` | id, location_id, item_id, lot_id, quantity_available, reserved_quantity, thresholds | Current stock state per item+location |
| `MovementType` | `movement_type` | id, movement_name | Seed: Receipt, Shipment, Transfer, Adjustment, Return, Cycle Count, Write Off |
| `StockLot` | `stock_lots` | id, item_id, batch_number, serial_number, expiry_date | Batch/lot tracking |
| `InventoryAlert` | `inventory_alerts` | id, inventory_level_id, alert_type, current_quantity, threshold_quantity, is_resolved | Auto-triggered alerts |

### Existing Triggers (`backend/app/models/triggers.py`)

| Trigger | Table | Fires | Action |
|---------|-------|-------|--------|
| `update_inventory_on_transaction` | `inventory_transactions` | AFTER INSERT | Creates/updates InventoryLevel: inbound adds qty, outbound subtracts qty |
| `check_inventory_threshold` | `inventory_levels` | BEFORE UPDATE | Creates InventoryAlert on threshold breach |
| `auto_resolve_inventory_alerts` | `inventory_levels` | AFTER UPDATE | Auto-resolves alerts when stock recovers |

### Existing Endpoints (`backend/app/routers/warehouse.py`, 1430 lines)

| Method | Path | Current Behavior |
|--------|------|-----------------|
| `POST /warehouse/movements` | Creates movement with transactions tied to single `item_id` | **Limitation: one item per movement** |
| `GET /warehouse/movements` | Lists movements (paginated) |
| `GET /warehouse/{wh_id}/inventory` | Lists InventoryLevel records | **Missing: `location_id` filter** |
| `POST /warehouse/reserve` | Reserve stock for orders |
| `POST /warehouse/release` | Release reserved stock |

### Current Schema Limitation (`backend/app/schemas/warehouse.py`)

```python
class InventoryMovementCreate(BaseModel):
    warehouse_id: int
    movement_type_id: int
    item_id: int                        # <-- Single item only
    transactions: list[InventoryTransactionCreate]
    reference_number: str | None = None
    notes: str | None = None
```

The `item_id` is at the movement level, meaning all transactions in one movement must be for the same item. Multi-item operations (e.g., receiving a shipment of 10 different products) require 10 separate API calls.

---

## 3. Feature A: Multi-Item Movement Endpoint

### 3A.1 New Schemas (`backend/app/schemas/warehouse.py`)

```python
class MovementLineItem(BaseModel):
    """One item line in a multi-item movement."""
    item_id: int
    quantity: int = Field(..., gt=0, description="Quantity to move (always positive)")

class MultiItemMovementCreate(BaseModel):
    """
    POST /warehouse/movements/v2 — Multi-item movement.

    The movement type determines which location fields are required
    and how transactions are generated:
    - Receipt:    destination_location_id required, all inbound
    - Shipment:   source_location_id required, all outbound (validates stock)
    - Transfer:   both required, 2 transactions per item (out from source, in to dest)
    - Adjustment: source_location_id required, inbound for positive, outbound for negative
    - Return:     destination_location_id required, all inbound
    """
    warehouse_id: int
    movement_type_id: int
    source_location_id: int | None = None
    destination_location_id: int | None = None
    items: list[MovementLineItem] = Field(..., min_length=1, max_length=100)
    reference_number: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=500)
```

### 3A.2 New Endpoint (`backend/app/routers/warehouse.py`)

**`POST /warehouse/movements/v2`**

Logic:
1. Validate `movement_type_id` exists
2. Look up movement type name to determine source/destination requirements
3. Validate location fields based on type:
   - Receipt: `destination_location_id` required, `source_location_id` ignored
   - Shipment: `source_location_id` required, validates each item's quantity <= available stock at source
   - Transfer: both required, source != destination
   - Adjustment: `source_location_id` required
   - Return: `destination_location_id` required
4. Create one `InventoryMovement` record
5. For each item in `items`:
   - **Receipt/Return**: Create 1 `InventoryTransaction(location_id=destination, is_inbound=True, quantity_change=qty)`
   - **Shipment**: Create 1 `InventoryTransaction(location_id=source, is_inbound=False, quantity_change=qty)`
   - **Transfer**: Create 2 transactions — outbound from source + inbound to destination
   - **Adjustment**: Create 1 transaction — outbound if negative correction, inbound if positive
6. DB trigger auto-updates `InventoryLevel` for each transaction
7. Return the created movement with enriched response

**Stock validation for outbound:**
```python
# For Shipment/Transfer, verify sufficient stock at source
for line_item in body.items:
    level = await session.exec(
        select(InventoryLevel)
        .where(InventoryLevel.item_id == line_item.item_id)
        .where(InventoryLevel.location_id == body.source_location_id)
    ).first()
    available = (level.quantity_available - level.reserved_quantity) if level else 0
    if line_item.quantity > available:
        raise HTTPException(400, f"Insufficient stock for item {line_item.item_id}: requested {line_item.quantity}, available {available}")
```

### 3A.3 Add `location_id` Filter to Inventory Endpoint

**`GET /warehouse/{warehouse_id}/inventory`** — add optional query param:

```python
@router.get("/{warehouse_id}/inventory")
async def list_inventory_levels(
    warehouse_id: int,
    location_id: int | None = Query(None),  # <-- NEW
    # ... existing params ...
):
    query = select(InventoryLevel).where(...)
    if location_id is not None:
        query = query.where(InventoryLevel.location_id == location_id)
        query = query.where(InventoryLevel.quantity_available > 0)
    # ... rest of existing logic
```

### 3A.4 Movement Type Rules Summary

| MovementType.movement_name | source_location_id | destination_location_id | Transactions per item | Direction |
|----------------------------|-------------------|------------------------|----------------------|-----------|
| Receipt | Ignored | Required | 1 | Inbound |
| Shipment | Required | Ignored | 1 | Outbound (validates stock) |
| Transfer | Required | Required (must differ) | 2 | Out from source + In to dest |
| Adjustment | Required | Ignored | 1 | In or Out (based on correction) |
| Return | Ignored | Required | 1 | Inbound |
| Cycle Count | — | — | Used by Stock Check reconciliation only |
| Write Off | Required | Ignored | 1 | Outbound |

### 3A.5 Backward Compatibility

The existing `POST /warehouse/movements` endpoint is **unchanged**. The new `/movements/v2` endpoint runs alongside it. The old endpoint can be deprecated in a future version once the frontend fully migrates.

---

## 4. Feature B: Stock Check (Cycle Count) System

### 4B.1 Why a New Model?

Stock checks are fundamentally different from ad-hoc movements:
- They have a **lifecycle** (draft → counting → review → reconcile)
- They target a **scope** (specific locations/sections, not just one item)
- They compare **system vs physical** quantities with variance tracking
- They require **review/approval** before stock adjustments are applied
- They produce **audit records** linking back to the adjustment movement

The existing `InventoryMovement` model cannot represent this workflow — it has no status, no scope concept, no variance tracking, and no line-level accept/reject.

### 4B.2 New Model (`backend/app/models/stock_check.py`)

```python
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text, Index
from sqlalchemy.dialects.postgresql import JSONB


class StockCheck(SQLModel, table=True):
    """
    A stock check (cycle count) session.

    Lifecycle: DRAFT -> IN_PROGRESS -> PENDING_REVIEW -> COMPLETED / CANCELLED

    WHY this lifecycle:
    - DRAFT: User defines scope but hasn't started counting. System quantities
      are NOT yet snapshotted — stock may still be moving.
    - IN_PROGRESS: System quantities are snapshotted at start time. Staff enters
      physical counts. Multiple staff can count different locations.
    - PENDING_REVIEW: All lines counted. Manager reviews variances, can accept
      or reject individual lines before reconciliation.
    - COMPLETED: Accepted variances generate a "Cycle Count" InventoryMovement.
      Stock levels are adjusted. Irreversible.
    - CANCELLED: Check abandoned. No stock changes. Preserved for audit.
    """
    __tablename__ = "stock_checks"
    __table_args__ = (
        Index("idx_stock_checks_warehouse", "warehouse_id"),
        Index("idx_stock_checks_status", "status"),
        Index("idx_stock_checks_warehouse_status", "warehouse_id", "status"),
        Index("idx_stock_checks_created", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouse_site.id")

    # Human-readable title, e.g. "Section A Monthly Count - March 2026"
    title: str = Field(max_length=200)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Lifecycle status
    status: str = Field(default="draft", max_length=20)
    # Valid values: draft, in_progress, pending_review, completed, cancelled

    # Scope: which locations were targeted
    # Example: {"warehouse_section": "A", "zone": "DRY"}
    # Or: {"warehouse_section": "A", "aisle": "A01"}
    # Or: {} for full warehouse
    scope_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB)
    )

    # Summary stats (updated as counting progresses)
    total_lines: int = Field(default=0)
    lines_counted: int = Field(default=0)
    lines_with_variance: int = Field(default=0)

    # Link to the reconciliation movement (set on completion)
    adjustment_movement_id: Optional[int] = Field(
        default=None,
        foreign_key="inventory_movements.id"
    )

    # Audit fields
    created_by: int = Field(foreign_key="users.user_id")
    completed_by: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Relationships
    lines: List["StockCheckLine"] = Relationship(back_populates="stock_check")


class StockCheckLine(SQLModel, table=True):
    """
    One line in a stock check: one item at one location.

    WHY system_quantity is snapshotted at start (not at count time):
    - Provides a consistent baseline for all lines in the check
    - If stock moves during counting, the variance reflects the
      discrepancy at the point-in-time the check began
    - Prevents confusion from shifting baselines mid-count
    """
    __tablename__ = "stock_check_lines"
    __table_args__ = (
        Index("idx_scl_check", "stock_check_id"),
        Index("idx_scl_item", "item_id"),
        Index("idx_scl_location", "location_id"),
        Index(
            "uq_check_item_location",
            "stock_check_id", "item_id", "location_id",
            unique=True
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_check_id: int = Field(foreign_key="stock_checks.id")

    item_id: int = Field(foreign_key="items.item_id")
    location_id: int = Field(foreign_key="inventory_location.id")

    # System quantity at time of check start (snapshot)
    system_quantity: int = Field(default=0)

    # Physical count entered by staff (NULL = not yet counted)
    counted_quantity: Optional[int] = Field(default=None)

    # Variance = counted_quantity - system_quantity
    # Positive = surplus (physical > system)
    # Negative = shortage (physical < system)
    variance: Optional[int] = Field(default=None)

    # Per-line notes (e.g. "3 units damaged", "wrong item in bin")
    notes: Optional[str] = Field(default=None, max_length=500)

    # Whether this line's variance is accepted for reconciliation
    # Default True — manager can reject specific lines during review
    is_accepted: bool = Field(default=True)

    # Timestamp when count was entered
    counted_at: Optional[datetime] = Field(default=None)

    # Relationships
    stock_check: Optional[StockCheck] = Relationship(back_populates="lines")
```

### 4B.3 Alembic Migration

**File:** `backend/alembic/versions/20260314_0000_00_l7m8n9o0p1q2_add_stock_check_tables.py`

Creates:
- `stock_checks` table with all columns, indexes, and foreign keys
- `stock_check_lines` table with unique constraint `uq_check_item_location`
- All FK indexes listed in `__table_args__`

**Naming convention** follows existing pattern: `YYYYMMDD_HHMM_SS_hash_description.py`

### 4B.4 Schemas (`backend/app/schemas/stock_check.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Create ──────────────────────────────────────────────

class StockCheckCreate(BaseModel):
    """Create a new stock check session."""
    warehouse_id: int
    title: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None
    scope_filters: Optional[dict] = None
    # Example scope_filters:
    #   {"warehouse_section": "A"}                    → all locations in Section A
    #   {"warehouse_section": "A", "zone": "DRY"}    → Section A, DRY zone only
    #   {"warehouse_section": "A", "aisle": "A01"}   → Section A, Aisle A01 only
    #   {} or None                                    → all locations in warehouse


# ── Count Submission ────────────────────────────────────

class StockCheckLineCount(BaseModel):
    """Physical count for one line."""
    line_id: int
    counted_quantity: int = Field(..., ge=0)
    notes: Optional[str] = Field(None, max_length=500)

class StockCheckBatchCount(BaseModel):
    """Submit physical counts for multiple lines at once."""
    counts: list[StockCheckLineCount] = Field(..., min_length=1)


# ── Reconciliation ─────────────────────────────────────

class LineAcceptance(BaseModel):
    """Accept or reject a single variance line."""
    line_id: int
    is_accepted: bool

class StockCheckReconcileRequest(BaseModel):
    """
    Optional: specify which variances to accept/reject.
    If omitted, all variances are accepted.
    """
    line_acceptances: Optional[list[LineAcceptance]] = None


# ── Read Responses ─────────────────────────────────────

class StockCheckLineRead(BaseModel):
    id: int
    item_id: int
    item_name: str              # Enriched from Item join
    master_sku: str             # Enriched from Item join
    location_id: int
    location_code: str          # Enriched from InventoryLocation.display_code
    system_quantity: int
    counted_quantity: Optional[int]
    variance: Optional[int]
    notes: Optional[str]
    is_accepted: bool
    counted_at: Optional[datetime]

class StockCheckRead(BaseModel):
    id: int
    warehouse_id: int
    title: str
    notes: Optional[str]
    status: str
    scope_filters: Optional[dict]
    total_lines: int
    lines_counted: int
    lines_with_variance: int
    adjustment_movement_id: Optional[int]
    created_by: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class StockCheckDetailRead(StockCheckRead):
    """Full detail view including all lines."""
    lines: list[StockCheckLineRead]
```

### 4B.5 Router (`backend/app/routers/stock_check.py`)

**Registered in `main.py`:**
```python
from app.routers.stock_check import router as stock_check_router
app.include_router(stock_check_router, prefix="/api/v1/stock-check", tags=["Stock Check"])
```

**Endpoints:**

| # | Method | Path | Purpose | Status Transition |
|---|--------|------|---------|-------------------|
| 1 | `POST /` | Create stock check | → draft |
| 2 | `GET /` | List stock checks (paginated) | — |
| 3 | `GET /{id}` | Get check with all lines (enriched) | — |
| 4 | `PATCH /{id}/start` | Snapshot system quantities, populate lines | draft → in_progress |
| 5 | `POST /{id}/count` | Submit batch physical counts | (in_progress only) |
| 6 | `PATCH /{id}/review` | Compute variance stats | in_progress → pending_review |
| 7 | `POST /{id}/reconcile` | Apply accepted variances as Cycle Count movement | pending_review → completed |
| 8 | `PATCH /{id}/cancel` | Cancel the check | draft/in_progress/pending_review → cancelled |

### 4B.6 Endpoint Details

#### Endpoint 1: `POST /` — Create Stock Check

```python
@router.post("/", response_model=StockCheckRead, status_code=201)
async def create_stock_check(
    body: StockCheckCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    # Validate warehouse exists and is active
    # Create StockCheck with status="draft"
    # Do NOT populate lines yet (that happens on start)
    # Return the created check
```

#### Endpoint 4: `PATCH /{id}/start` — Start Stock Check

This is the most complex endpoint. On start:

1. Validate status == "draft"
2. Query `InventoryLocation` records matching `scope_filters`:
   ```python
   query = select(InventoryLocation).where(
       InventoryLocation.warehouse_id == check.warehouse_id,
       InventoryLocation.deleted_at.is_(None),
       InventoryLocation.is_active == True,
   )
   if scope_filters:
       if "warehouse_section" in scope_filters:
           query = query.where(InventoryLocation.warehouse_section == scope_filters["warehouse_section"])
       if "zone" in scope_filters:
           query = query.where(InventoryLocation.zone == scope_filters["zone"])
       if "aisle" in scope_filters:
           query = query.where(InventoryLocation.aisle == scope_filters["aisle"])
       if "bay" in scope_filters:
           query = query.where(InventoryLocation.bay == scope_filters["bay"])
   ```
3. For each matching location, query `InventoryLevel` records with `quantity_available > 0`
4. Create one `StockCheckLine` per (item_id, location_id) pair, snapshotting `system_quantity = level.quantity_available`
5. Update `total_lines` count
6. Set `status = "in_progress"`, `started_at = utcnow()`

**Edge case:** If no inventory exists at scoped locations, return 400 with "No inventory found at scoped locations."

#### Endpoint 5: `POST /{id}/count` — Submit Counts

```python
@router.post("/{id}/count", response_model=StockCheckDetailRead)
async def submit_counts(
    id: int,
    body: StockCheckBatchCount,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    # Validate status == "in_progress"
    # For each count in body.counts:
    #   - Find StockCheckLine by line_id (validate belongs to this check)
    #   - Set counted_quantity, compute variance = counted - system
    #   - Set notes if provided
    #   - Set counted_at = utcnow()
    # Update lines_counted and lines_with_variance stats
    # Return updated check with all lines
```

#### Endpoint 7: `POST /{id}/reconcile` — Reconcile Variances

**This is the critical business logic:**

```python
@router.post("/{id}/reconcile", response_model=StockCheckRead)
async def reconcile_stock_check(
    id: int,
    body: StockCheckReconcileRequest | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_current_user),
):
    # 1. Validate status == "pending_review"

    # 2. Apply line acceptances if provided
    if body and body.line_acceptances:
        for acceptance in body.line_acceptances:
            line = get_line(acceptance.line_id)
            line.is_accepted = acceptance.is_accepted

    # 3. Collect accepted lines with non-zero variance
    variance_lines = [
        line for line in check.lines
        if line.is_accepted and line.variance and line.variance != 0
    ]

    # 4. If no variances to reconcile, just complete
    if not variance_lines:
        check.status = "completed"
        check.completed_at = utcnow()
        check.completed_by = current_user.user_id
        return check

    # 5. Create reconciliation InventoryMovement
    cycle_count_type = await session.exec(
        select(MovementType).where(MovementType.movement_name == "Cycle Count")
    ).first()

    movement = InventoryMovement(
        movement_type_id=cycle_count_type.id,
        reference_id=f"SC-{check.id}",
    )
    session.add(movement)
    await session.flush()  # Get movement.id

    # 6. Create transactions for each variance
    for line in variance_lines:
        if line.variance > 0:
            # Surplus: physical > system → add stock (inbound)
            tx = InventoryTransaction(
                item_id=line.item_id,
                location_id=line.location_id,
                movement_id=movement.id,
                is_inbound=True,
                quantity_change=line.variance,
            )
        else:
            # Shortage: physical < system → remove stock (outbound)
            tx = InventoryTransaction(
                item_id=line.item_id,
                location_id=line.location_id,
                movement_id=movement.id,
                is_inbound=False,
                quantity_change=abs(line.variance),
            )
        session.add(tx)

    # 7. DB trigger `update_inventory_on_transaction` fires for each INSERT,
    #    auto-updating InventoryLevel.quantity_available

    # 8. Update stock check
    check.adjustment_movement_id = movement.id
    check.status = "completed"
    check.completed_at = utcnow()
    check.completed_by = current_user.user_id

    await session.commit()
    return check
```

### 4B.7 Lifecycle Diagram

```
                    ┌─────────┐
                    │  DRAFT  │
                    └────┬────┘
                         │ PATCH /{id}/start
                         │ (snapshot system qty, populate lines)
                         ▼
                  ┌──────────────┐
                  │ IN_PROGRESS  │◄── POST /{id}/count (repeatable)
                  └──────┬───────┘
                         │ PATCH /{id}/review
                         │ (compute variance stats)
                         ▼
               ┌──────────────────┐
               │ PENDING_REVIEW   │
               └────────┬─────────┘
                        │ POST /{id}/reconcile
                        │ (create Cycle Count movement for accepted variances)
                        ▼
                  ┌───────────┐
                  │ COMPLETED │
                  └───────────┘

  Any non-terminal status ──PATCH /{id}/cancel──▶ CANCELLED
```

### 4B.8 Model Registration

Add to `backend/app/models/__init__.py` (if exists) or import in `backend/app/main.py` startup:

```python
from app.models.stock_check import StockCheck, StockCheckLine
```

Ensure SQLModel metadata includes the new tables for Alembic autogenerate.

---

## 5. Files Summary

### New Files

| File | Purpose |
|------|---------|
| `backend/app/models/stock_check.py` | StockCheck + StockCheckLine models |
| `backend/app/schemas/stock_check.py` | Request/response schemas |
| `backend/app/routers/stock_check.py` | 8 endpoints + reconciliation logic |
| `backend/alembic/versions/20260314_..._add_stock_check_tables.py` | Migration for 2 new tables |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/routers/warehouse.py` | Add `POST /movements/v2` endpoint; add `location_id` param to `GET /{wh_id}/inventory` |
| `backend/app/schemas/warehouse.py` | Add `MovementLineItem` and `MultiItemMovementCreate` schemas |
| `backend/app/main.py` | Register `stock_check_router` with prefix `/api/v1/stock-check` |

### Unchanged (reused as-is)

| File | What's Reused |
|------|---------------|
| `backend/app/models/warehouse.py` | InventoryMovement, InventoryTransaction, MovementType, InventoryLevel |
| `backend/app/models/triggers.py` | `update_inventory_on_transaction` trigger (auto-updates stock on reconciliation) |
| `backend/app/services/inventory_guard.py` | Stock-aware deletion guard (no changes needed) |

---

## 6. Database Changes Summary

### New Tables

```
stock_checks
├── id (PK)
├── warehouse_id (FK → warehouse_site.id)
├── title (VARCHAR 200)
├── notes (TEXT, nullable)
├── status (VARCHAR 20, default 'draft')
├── scope_filters (JSONB, nullable)
├── total_lines (INT, default 0)
├── lines_counted (INT, default 0)
├── lines_with_variance (INT, default 0)
├── adjustment_movement_id (FK → inventory_movements.id, nullable)
├── created_by (FK → users.user_id)
├── completed_by (FK → users.user_id, nullable)
├── created_at (TIMESTAMP)
├── started_at (TIMESTAMP, nullable)
└── completed_at (TIMESTAMP, nullable)

stock_check_lines
├── id (PK)
├── stock_check_id (FK → stock_checks.id)
├── item_id (FK → items.item_id)
├── location_id (FK → inventory_location.id)
├── system_quantity (INT, default 0)
├── counted_quantity (INT, nullable)
├── variance (INT, nullable)
├── notes (VARCHAR 500, nullable)
├── is_accepted (BOOL, default true)
├── counted_at (TIMESTAMP, nullable)
└── UNIQUE(stock_check_id, item_id, location_id)
```

### Indexes

| Index | Table | Columns | Type |
|-------|-------|---------|------|
| `idx_stock_checks_warehouse` | stock_checks | warehouse_id | B-tree |
| `idx_stock_checks_status` | stock_checks | status | B-tree |
| `idx_stock_checks_warehouse_status` | stock_checks | warehouse_id, status | Composite |
| `idx_stock_checks_created` | stock_checks | created_at | B-tree |
| `idx_scl_check` | stock_check_lines | stock_check_id | B-tree |
| `idx_scl_item` | stock_check_lines | item_id | B-tree |
| `idx_scl_location` | stock_check_lines | location_id | B-tree |
| `uq_check_item_location` | stock_check_lines | stock_check_id, item_id, location_id | Unique |

---

## 7. API Endpoints Summary

### Movement (additions to existing `/api/v1/warehouse/`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/warehouse/movements/v2` | Create multi-item movement |
| `GET` | `/warehouse/{wh_id}/inventory?location_id=X` | Filter inventory by location (new param) |

### Stock Check (new `/api/v1/stock-check/`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/stock-check/` | Create stock check (draft) |
| `GET` | `/stock-check/?warehouse_id=X&status=Y` | List stock checks (paginated) |
| `GET` | `/stock-check/{id}` | Get check with lines |
| `PATCH` | `/stock-check/{id}/start` | Start counting session |
| `POST` | `/stock-check/{id}/count` | Submit batch counts |
| `PATCH` | `/stock-check/{id}/review` | Submit for review |
| `POST` | `/stock-check/{id}/reconcile` | Reconcile and complete |
| `PATCH` | `/stock-check/{id}/cancel` | Cancel check |

---

## 8. Testing Checklist

- [ ] `POST /movements/v2` with Receipt (3 items) → verify 3 InventoryLevel records created/updated
- [ ] `POST /movements/v2` with Transfer → verify 2 transactions per item, source decremented, destination incremented
- [ ] `POST /movements/v2` with Shipment exceeding stock → verify 400 error
- [ ] `POST /movements/v2` with Transfer where source == destination → verify 400 error
- [ ] `POST /stock-check/` → verify draft created
- [ ] `PATCH /stock-check/{id}/start` with scope → verify lines populated with correct system quantities
- [ ] `POST /stock-check/{id}/count` → verify variance computed correctly
- [ ] `POST /stock-check/{id}/reconcile` → verify Cycle Count movement created with correct transactions
- [ ] After reconciliation → verify InventoryLevel quantities match physical counts
- [ ] After reconciliation causing low stock → verify InventoryAlert auto-created by trigger
- [ ] `PATCH /stock-check/{id}/cancel` from each status → verify no stock changes
