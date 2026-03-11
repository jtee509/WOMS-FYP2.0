---
name: Bundle SKU & Component Inventory Management Plan
overview: >
  Structured plan for implementing Bundle SKU inventory management within WOMS.
  Covers schema extensions (BOM table), atomic stock deduction logic for shared
  component variations, oversell prevention, and the full pick/pack/restock workflow
  for items sold both standalone and as bundle components.
  Target versions: PRE-ALPHA v0.5.17 – v0.5.20
created: 2026-03-03
author: Planning phase document
---

# Bundle SKU & Component Inventory Management Plan

**Target versions:** PRE-ALPHA v0.5.17 – v0.5.20
**Created:** 2026-03-03
**Status:** Phases 1–3 COMPLETE (v0.5.17–v0.5.19, 2026-03-04). Phase 4 (Frontend) pending (v0.5.20).

---

## 1. Current Schema State & Gap Analysis

### 1.1 What exists today

| Table | Relevant columns | Role |
|-------|-----------------|------|
| `items` | `item_id`, `master_sku`, `parent_id`, `has_variation`, `item_type_id` | Holds all products + their variation children |
| `item_type` | `item_type_id`, `item_type_name` | Seeded: Raw Material, Finished Good, Component, Packaging, Consumable — **no "Bundle" type** |
| `platform_sku` | `listing_id`, `platform_sku`, `seller_id` | Platform-facing listing (Lazada/Shopee/TikTok SKU) |
| `listing_component` | `listing_id → item_id`, `quantity` | 1 platform listing → N internal items (kit mapping) |
| `inventory_levels` | `item_id`, `location_id`, `quantity_available`, thresholds | Physical stock per item per bin |
| `inventory_transactions` | `item_id`, `location_id`, `quantity_change`, `is_inbound` | Every stock in/out event |
| `inventory_movements` | `movement_type_id`, `reference_id` | Groups related transactions |

### 1.2 Identified Gaps

| Gap | Impact |
|-----|--------|
| No internal "Bundle" concept at the warehouse layer | Cannot track a bundle as its own SKU without platform involvement |
| `listing_component` is scoped to *platform listings*, not warehouse-level BOM | Bundle definition is repeated per platform, cannot be shared |
| `inventory_levels` has no concept of virtual (computed) bundle stock | Dashboard shows 0 for a bundle because no direct stock row exists |
| No atomic multi-item deduction on sale | Race condition: 2 concurrent orders can oversell a shared component |
| No `reserved_quantity` column | Cannot distinguish "on hand" from "available to promise" |

---

## 2. Proposed Schema Extensions

### 2.1 New `item_type` seed value

Add **"Bundle"** to the `item_type` seed in `backend/app/models/seed.py`:

```python
"Bundle"   # A virtual SKU composed of 2+ component items
```

A Bundle item:
- Has `item_type.item_type_name = "Bundle"`
- Has `has_variation = False` at the bundle level (variations live on components)
- Has **no direct `inventory_levels` rows** — its available stock is computed
- Its `master_sku` is the canonical internal Bundle SKU (e.g., `BNDL-TSHIRT-3PK`)

---

### 2.2 New Table: `item_bundle_components` (BOM)

This is the **Bill of Materials** join table. It links one bundle item to its constituent
component items with explicit quantities.

```python
class ItemBundleComponent(SQLModel, table=True):
    """
    Bill of Materials: maps a Bundle item to its Component items.

    A Bundle SKU (bundle_item_id) expands into 1..N component items
    (component_item_id), each with a required quantity per bundle unit.

    Design decisions:
    - bundle_item_id must be an Item with item_type = "Bundle"
    - component_item_id must be a Variation-level item (leaf node, parent_id set)
      or a standalone item — never another bundle (no nested bundles)
    - quantity = how many units of the component are included per bundle
    - is_substitutable allows an alternative component to be swapped in without
      redefining the bundle (future: substitution logic)
    """
    __tablename__ = "item_bundle_components"
    __table_args__ = (
        # Primary lookup: all components for a given bundle
        Index("idx_bundle_components_bundle", "bundle_item_id"),
        # Reverse lookup: all bundles that use a given component (oversell check)
        Index("idx_bundle_components_component", "component_item_id"),
        # Uniqueness: a component can only appear once per bundle
        UniqueConstraint("bundle_item_id", "component_item_id",
                         name="uq_bundle_component"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # The bundle (virtual SKU)
    bundle_item_id: int = Field(
        foreign_key="items.item_id",
        index=True,
        description="FK → items.item_id where item_type = 'Bundle'"
    )

    # The physical component (real stock is tracked here)
    component_item_id: int = Field(
        foreign_key="items.item_id",
        index=True,
        description="FK → items.item_id — the physical variation or standalone item"
    )

    # How many units of the component are consumed per bundle unit sold
    quantity_per_bundle: int = Field(
        default=1,
        ge=1,
        description="Units of component consumed per 1 bundle unit sold"
    )

    # Soft control — deactivate without deleting BOM rows
    is_active: bool = Field(default=True, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Relationship additions in `items.py`:**

```python
# On Item:
bundle_definitions: List["ItemBundleComponent"] = Relationship(
    back_populates="bundle",
    sa_relationship_kwargs={"foreign_keys": "[ItemBundleComponent.bundle_item_id]"}
)
bundle_memberships: List["ItemBundleComponent"] = Relationship(
    back_populates="component",
    sa_relationship_kwargs={"foreign_keys": "[ItemBundleComponent.component_item_id]"}
)
```

---

### 2.3 Add `reserved_quantity` to `inventory_levels`

`reserved_quantity` holds stock that is allocated to an open order but not yet shipped.
`quantity_available` represents physical on-hand stock.
`quantity_available_to_promise` (ATP) = `quantity_available - reserved_quantity`.

```python
# New column on InventoryLevel:
reserved_quantity: int = Field(
    default=0,
    description="Stock allocated to open orders — not yet shipped"
)
```

**Alembic migration:** `backend/alembic/versions/<timestamp>_add_reserved_quantity.py`

---

### 2.4 Updated `platform_sku` + `listing_component` Usage

After this change, `listing_component` continues to be used **but should point to the
Bundle item** (not the components individually) when the platform sells a bundle:

```
PlatformSKU (Shopee "BUNDLE-TSHIRT-3PK")
  └─ ListingComponent → item_id = BNDL-TSHIRT-3PK (qty=1)

ItemBundleComponent (BOM)
  BNDL-TSHIRT-3PK
    ├─ T-SHIRT-RED-M   qty=1
    ├─ T-SHIRT-BLUE-M  qty=1
    └─ T-SHIRT-WHT-M   qty=1
```

This separates *platform concerns* (which listing maps to which internal SKU)
from *warehouse concerns* (which physical items make up the bundle).

---

## 3. Inventory Logic

### 3.1 Bundle Stock Computation (Virtual ATP)

A bundle's available-to-promise stock is never stored directly — it is always
**computed on demand** from the limiting component:

```
bundle_ATP = MIN(
    FLOOR( component_i_ATP / component_i_quantity_per_bundle )
    for each component_i in BOM
)
```

**Example:**

| Component SKU | On Hand | Reserved | ATP | qty_per_bundle | Bundle ATP contribution |
|---------------|---------|----------|-----|----------------|------------------------|
| T-SHIRT-RED-M | 15 | 2 | 13 | 1 | 13 |
| T-SHIRT-BLUE-M | 8 | 1 | 7 | 1 | 7 |
| T-SHIRT-WHT-M | 20 | 0 | 20 | 1 | 20 |

→ **Bundle ATP = MIN(13, 7, 20) = 7**

This calculation is performed in a service function, never cached to disk,
to avoid stale data problems.

```python
# backend/app/services/bundle/stock.py

async def compute_bundle_atp(bundle_item_id: int, session: AsyncSession) -> int:
    """
    Returns the available-to-promise quantity for a bundle SKU.
    Result is the minimum across all components, weighted by quantity_per_bundle.
    Returns 0 if any component has 0 ATP.
    """
    ...
```

---

### 3.2 Stock Deduction on Sale (Atomic Multi-Component Deduction)

When a bundle order line is fulfilled, stock must be deducted from **all components
simultaneously in a single database transaction**. Partial deduction must never be
committed.

**Service function signature:**

```python
# backend/app/services/bundle/fulfillment.py

async def deduct_bundle_stock(
    bundle_item_id: int,
    bundle_qty_sold: int,
    warehouse_id: int,
    order_reference: str,
    session: AsyncSession,
) -> list[InventoryTransaction]:
    """
    Atomically deducts stock from all component items when a bundle is sold.

    Steps:
    1. Load BOM for bundle_item_id (all active ItemBundleComponent rows).
    2. For each component, select the InventoryLevel rows for this warehouse
       using SELECT ... FOR UPDATE (row-level lock) — prevents concurrent deduction.
    3. Validate total ATP >= (component.quantity_per_bundle * bundle_qty_sold).
       If any component fails validation, rollback the entire transaction.
    4. Apply FIFO deduction across locations for each component.
    5. Write one InventoryTransaction per (component, location) pair.
    6. Create one InventoryMovement grouping all transactions (reference = order_reference).
    7. Update inventory_levels.quantity_available for each affected row.
    8. Trigger alert evaluation for any component that crosses a threshold post-deduction.

    Raises:
        InsufficientStockError: if any component's ATP < required quantity.
        BundleNotFoundError:    if no active BOM components exist.
    """
```

**Key safety rules:**
- All deductions happen inside a single `async with session.begin()` block
- `SELECT ... FOR UPDATE` (via SQLAlchemy `with_for_update()`) on `inventory_levels` rows prevents race conditions
- The transaction is rolled back atomically if any component check fails
- Never deduct from components individually in separate API calls

---

### 3.3 Oversell Prevention for Shared Components

A variation item (e.g., T-SHIRT-RED-M) can be sold:
1. As a standalone item
2. As a component in Bundle A
3. As a component in Bundle B (same variation in two different bundles)

**Problem:** Bundles A and B and the standalone listing all compete for the same
`inventory_levels` row for T-SHIRT-RED-M. Three concurrent orders could each see
ATP = 5, all succeed reservation checks, but only 5 units exist.

**Solution: `reserved_quantity` + row-level locks**

```
Phase 1 — Order Received (Reservation):
  SELECT inventory_levels WHERE item_id = T-SHIRT-RED-M FOR UPDATE
  IF (quantity_available - reserved_quantity) >= required_qty:
      UPDATE reserved_quantity += required_qty   ← pessimistic reservation
      COMMIT
  ELSE:
      RAISE InsufficientStockError

Phase 2 — Fulfillment (Deduction):
  UPDATE quantity_available -= required_qty
  UPDATE reserved_quantity -= required_qty
  INSERT InventoryTransaction (is_inbound=False, quantity_change=required_qty)
  COMMIT

Phase 3 — Cancellation (Release):
  UPDATE reserved_quantity -= required_qty
  COMMIT
```

This pattern means ATP = `quantity_available - reserved_quantity` and both standalone
and bundle fulfillment paths use the same locking routine against the same row.

**Implementation note:** `deduct_bundle_stock()` and the standalone `deduct_stock()`
service function must both use the same underlying `_reserve_inventory()` helper to
ensure consistent locking semantics.

---

### 3.4 Stock Status for Bundles on the Dashboard

`InventoryLevel` rows do not exist for bundle items. The Inventory Levels page
must handle bundles differently:

| Item type | How stock is shown |
|-----------|--------------------|
| Standalone / Variation | Direct `inventory_levels.quantity_available` |
| Bundle | Computed: `compute_bundle_atp()` — shown as "Virtual Stock" |

The `GET /warehouse/{id}/inventory` endpoint will include an optional
`?include_bundles=true` query param that triggers BOM expansion and ATP
computation for all bundle items associated with that warehouse.

A bundle row in the response carries a special `is_bundle: true` flag and a
`bundle_components_summary` array for drill-down.

---

## 4. Variation Independence

### 4.1 Dual-Mode Items

An item variation (e.g., T-SHIRT-RED-M) can exist in two sales modes simultaneously:

| Mode | Platform listing | BOM reference | Stock impact |
|------|-----------------|---------------|--------------|
| Standalone | PlatformSKU → ListingComponent → T-SHIRT-RED-M (qty=1) | None | Direct deduction from `inventory_levels` |
| Bundle Component | PlatformSKU → ListingComponent → BNDL-TSHIRT-3PK (qty=1) | BNDL → T-SHIRT-RED-M (qty=1) | Deduction via `deduct_bundle_stock()` |

The physical stock row in `inventory_levels` is shared. Only the **deduction path** differs.
The variation item itself has no knowledge of whether it is being consumed standalone or
as part of a bundle — all it sees is a stock decrease.

---

### 4.2 Picking Workflow

```
Order received
    │
    ├─ [Standalone SKU]
    │       └─ Pick slip: 1 line — T-SHIRT-RED-M, Qty=2, Location S1-Z2-B4
    │
    └─ [Bundle SKU]
            └─ Pick slip: N lines (one per BOM component)
                   ├─ T-SHIRT-RED-M,  Qty=1, Location S1-Z2-B4
                   ├─ T-SHIRT-BLUE-M, Qty=1, Location S1-Z2-B5
                   └─ T-SHIRT-WHT-M,  Qty=1, Location S1-Z2-B6
               → Pack together in bundle packaging (reference: Bundle SKU barcode)
```

**Pick slip generation rules:**
- A bundle line on an order detail always expands into individual component pick lines
- Each component pick line is linked back to the parent bundle order line via `reference_id`
- Pick lines are sorted by `location_code` to optimise picker routing path (zone → aisle → rack → bin)

---

### 4.3 Packing Workflow

After picking, components are scanned at the pack station:

1. Scan bundle barcode (bundle `master_sku`)
2. System displays the BOM checklist — all component items with tick-boxes
3. Picker scans each component to confirm; system validates against BOM quantities
4. Only when all components are confirmed does the system:
   - Call `deduct_bundle_stock()` to write final `InventoryTransaction` records
   - Release `reserved_quantity` and reduce `quantity_available` for each component
   - Generate shipping label with the bundle SKU as the primary reference

**Anti-substitution rule:** The packing scan must reject a component item that is not
in the BOM. This prevents ad-hoc substitutions that would invalidate the product listing.

---

### 4.4 Restocking Workflow

When receiving inbound stock (e.g., PO arrives), items are always restocked at the
**component level**, never at the bundle level:

```
Inbound PO: 50× T-SHIRT-RED-M
    → POST /warehouse/movements  (movement_type = "Receipt")
    → InventoryTransaction: item_id=T-SHIRT-RED-M, is_inbound=True, qty=50
    → inventory_levels.quantity_available += 50

Bundle ATP is NOT directly restocked — it automatically increases because the
limiting component (T-SHIRT-RED-M) now has more stock.
```

**Reorder alerts for bundles:**
- Alerts fire at the *component level* (existing `InventoryAlert` mechanism unchanged)
- A separate **Bundle Health dashboard widget** aggregates component alerts for a
  given bundle and surfaces them as: "Bundle BNDL-TSHIRT-3PK: limited by T-SHIRT-BLUE-M (ATP=3)"

---

## 5. New Backend Files Required

| File | Purpose |
|------|---------|
| `backend/app/models/items.py` | Add `ItemBundleComponent` model + relationships |
| `backend/app/models/warehouse.py` | Add `reserved_quantity` to `InventoryLevel` |
| `backend/app/models/seed.py` | Add "Bundle" to `item_type` seeds |
| `backend/app/services/bundle/__init__.py` | Bundle service package |
| `backend/app/services/bundle/stock.py` | `compute_bundle_atp()` |
| `backend/app/services/bundle/fulfillment.py` | `deduct_bundle_stock()`, `reserve_inventory()` |
| `backend/app/schemas/items.py` | `BundleComponentRead`, `BundleComponentCreate`, `BundleRead` |
| `backend/app/routers/items.py` | Bundle CRUD endpoints (see §6) |
| `backend/alembic/versions/<ts>_add_bundle_tables.py` | Migration: `item_bundle_components` + `reserved_quantity` |

---

## 6. New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/items/{item_id}/bundle` | Get BOM for a bundle item |
| `POST` | `/items/{item_id}/bundle/components` | Add component to BOM |
| `PUT` | `/items/{item_id}/bundle/components/{component_id}` | Update component quantity |
| `DELETE` | `/items/{item_id}/bundle/components/{component_id}` | Remove component from BOM |
| `GET` | `/items/{item_id}/bundle/atp` | Compute virtual ATP for a bundle |
| `GET` | `/items/{item_id}/bundle/memberships` | List all bundles that contain this item |
| `POST` | `/warehouse/fulfill/bundle` | Atomic bundle stock deduction (on-sale hook) |
| `POST` | `/warehouse/reserve` | Reserve stock (standalone or bundle) for an order |
| `POST` | `/warehouse/release` | Release reservation on cancellation |

---

## 7. Alembic Migration Plan

### Migration: `add_bundle_tables`

```python
def upgrade():
    # 1. item_bundle_components table
    op.create_table(
        "item_bundle_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bundle_item_id", sa.Integer(), sa.ForeignKey("items.item_id"), nullable=False),
        sa.Column("component_item_id", sa.Integer(), sa.ForeignKey("items.item_id"), nullable=False),
        sa.Column("quantity_per_bundle", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_bundle_components_bundle", "item_bundle_components", ["bundle_item_id"])
    op.create_index("idx_bundle_components_component", "item_bundle_components", ["component_item_id"])
    op.create_unique_constraint(
        "uq_bundle_component", "item_bundle_components",
        ["bundle_item_id", "component_item_id"]
    )

    # 2. reserved_quantity on inventory_levels
    op.add_column(
        "inventory_levels",
        sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0")
    )

def downgrade():
    op.drop_column("inventory_levels", "reserved_quantity")
    op.drop_table("item_bundle_components")
```

---

## 8. Frontend Implications

### 8.1 Item Form — Bundle Tab

In `pages/items/ItemFormPage.tsx`, add a conditional **"Bundle Components" tab** that
appears when `item_type = "Bundle"`:

```
┌─────────────────────────────────────────────────────┐
│  General  │  Variations  │  Bundle Components  ←NEW │
├─────────────────────────────────────────────────────┤
│  + Add Component                                    │
│  ┌──────────────────┬──────┬──────────────────────┐ │
│  │ Component SKU    │ Qty  │ Action               │ │
│  ├──────────────────┼──────┼──────────────────────┤ │
│  │ T-SHIRT-RED-M    │  1   │ [Edit qty] [Remove]  │ │
│  │ T-SHIRT-BLUE-M   │  1   │ [Edit qty] [Remove]  │ │
│  │ T-SHIRT-WHT-M    │  1   │ [Edit qty] [Remove]  │ │
│  └──────────────────┴──────┴──────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 8.2 Inventory Levels Page — Bundle Rows

Bundle items appear with:
- A "Bundle" badge (blue)
- ATP computed via `/items/{id}/bundle/atp`
- An expand row showing each component's individual ATP contribution
- `stock_status` derived from the minimum component status

### 8.3 Movement Record Modal — Bundle Awareness

When recording an *Outbound* movement, if the selected item is a Bundle:
- Show a read-only BOM expansion listing which components will be deducted
- Confirm screen summarises: "This will deduct N units from X components"

---

## 9. Implementation Order

### Phase 1 — Schema (v0.5.17)
1. Add `ItemBundleComponent` model to `items.py`
2. Add `reserved_quantity` to `InventoryLevel` in `warehouse.py`
3. Add "Bundle" to `item_type` seed in `seed.py`
4. Write and run Alembic migration `add_bundle_tables`
5. Update `docs/official_documentation/database_structure.md`

### Phase 2 — Bundle Service (v0.5.18)
1. `backend/app/services/bundle/stock.py` — `compute_bundle_atp()`
2. `backend/app/services/bundle/fulfillment.py` — `deduct_bundle_stock()`, `reserve_inventory()`, `release_reservation()`
3. Unit test each service function against `woms_test_db`

### Phase 3 — Bundle API Endpoints (v0.5.19)
1. Add Bundle CRUD endpoints to `backend/app/routers/items.py`
2. Add `POST /warehouse/reserve` + `POST /warehouse/release` + `POST /warehouse/fulfill/bundle`
3. Add `GET /items/{id}/bundle/atp`
4. Document all endpoints in `docs/official_documentation/web-api.md`
5. End-to-end test via Swagger UI

### Phase 4 — Frontend Bundle UI (v0.5.20)
1. Add Bundle Components tab to `ItemFormPage.tsx`
2. Extend Inventory Levels page with bundle ATP row + expand
3. Extend Movement Record modal with bundle awareness
4. Update `docs/official_documentation/frontend-development-progress.md`

---

## 10. Verification Checklist

| # | Test | Expected |
|---|------|---------|
| 1 | Create item with `item_type = "Bundle"` | `item_bundle_components` rows insertable |
| 2 | Add 3 components to bundle BOM | `GET /items/{id}/bundle` returns 3 components |
| 3 | `GET /items/{id}/bundle/atp` | Returns MIN(component ATPs / qty_per_bundle) |
| 4 | Deduct bundle stock (1 unit sold) | All 3 component `inventory_levels.quantity_available` decrease |
| 5 | Concurrent orders, shared component | Second order blocked if ATP < required |
| 6 | Cancel order after reservation | `reserved_quantity` decremented; ATP restored |
| 7 | Standalone order for same component | Succeeds only if ATP (after bundle reservation) > 0 |
| 8 | Inbound restock of a component | Bundle ATP increases automatically |
| 9 | Remove component from BOM | Future orders no longer deduct that item |
| 10 | Bundle row on InventoryLevels page | Shows computed ATP, expand shows components |

---

## 11. Changelog

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-03 | Initial plan created | Define Bundle SKU inventory management strategy aligned to current schema |
