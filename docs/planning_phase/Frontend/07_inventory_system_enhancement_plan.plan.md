# Inventory System Enhancement Plan

**Version:** PRE-ALPHA v0.6.x
**Created:** 2026-03-11
**Status:** Planning

---

## Overview

This plan transforms the existing inventory system from a basic movement recorder into a full lifecycle management platform. Three phases build progressively:

1. **Phase 1** — Multi-Item Movement Flow (invoice-style drawer)
2. **Phase 2** — Enhanced Movements Table (expandable rows, lifecycle status)
3. **Phase 3** — Intelligent Stock Levels & Analytics

---

## Current State Audit

### What Exists

| Component | File | Status |
|-----------|------|--------|
| Inventory Levels page | `pages/warehouse/InventoryLevelsPage.tsx` (216 lines) | Basic: tab-filtered stock table with status badges |
| Inventory Movements page | `pages/warehouse/InventoryMovementsPage.tsx` (407 lines) | Basic: single-item modal + flat movement history |
| Inventory Alerts page | `pages/warehouse/InventoryAlertsPage.tsx` (270 lines) | Working: alert list with resolve modal |
| Backend models | `models/warehouse.py` (535 lines) | Complete: 11 tables incl. StockLot, InventoryLevel, InventoryMovement, InventoryTransaction |
| Backend router | `routers/warehouse.py` (1430 lines) | 39+ endpoints across 8 groups |
| Frontend API | `api/base/warehouse.ts` (235 lines) | Complete: CRUD + movements + alerts + reserve/release |
| Frontend types | `api/base_types/warehouse.ts` (310 lines) | Complete: all warehouse domain types |
| Warehouse context | `api/contexts/WarehouseContext.tsx` | Global warehouse selector persisted in localStorage |

### Backend Schema Relevant to This Plan

```
InventoryMovement (parent)
├── movement_type_id → MovementType (Receipt, Shipment, Transfer, Adjustment, etc.)
├── reference_id (optional, e.g. order number)
├── notes
├── created_at
└── InventoryTransaction[] (children)
    ├── movement_id → InventoryMovement
    ├── item_id → Item
    ├── location_id → InventoryLocation
    ├── lot_id → StockLot (optional, for batch/lot tracking)
    ├── is_inbound: bool
    ├── quantity_change: int
    └── created_at

InventoryLevel
├── item_id → Item
├── location_id → InventoryLocation
├── quantity_available: int
├── reserved_quantity: int  (for allocations)
├── reorder_point: int
├── safety_stock: int
├── max_stock: int
└── stock_status (computed property: OK / LOW / CRITICAL / OUT_OF_STOCK / OVERSTOCK)
    - ATP = quantity_available - reserved_quantity
```

### What's Missing (Gaps to Address)

| Gap | Impact | Phase |
|-----|--------|-------|
| Movement form only supports single-item entry | Users must create separate movements for each item in a multi-item transfer | Phase 1 |
| No movement lifecycle status (Pending → In-Transit → Completed) | All movements are immediately applied; no approval workflow | Phase 2 |
| No expandable rows in movement history | Can't see individual transaction items within a grouped movement | Phase 2 |
| Stock status filters are frontend-only visual badges | No server-side threshold-driven alerting or dynamic filter computation | Phase 3 |
| No analytics/reporting dashboard | No visibility into movement trends, high-velocity items, or daily throughput | Phase 3 |

---

## Phase 1: The Multi-Item Movement Flow

### Goal

Replace the current single-item modal with an "invoice-style" right-side drawer that supports multi-item movements in a single transaction.

### Why a Drawer (Not a Modal)

- Users can reference the background movement history table while entering data
- More horizontal space for the item grid (columns: Product, Batch, Stock, Qty, Action)
- Doesn't obscure the entire screen — feels lighter than a full-page form

### UI Implementation: RecordMovementDrawer

```
┌──────────────────────────────────────┬───────────────────────────────────────┐
│         Movement History Table       │      Record Movement Drawer           │
│         (background, dimmed)         │                                       │
│                                      │  Movement Type: [Transfer ▾]          │
│                                      │  Reference #:   [REF-2026-0045    ]   │
│                                      │                                       │
│                                      │  Source:      [Warehouse A - A01 ▾]   │
│                                      │  Destination: [Warehouse B - B03 ▾]   │
│                                      │                                       │
│                                      │  ┌──────────────────────────────────┐  │
│                                      │  │ Product  │ Batch │ Stock │ Qty  │  │
│                                      │  ├──────────┼───────┼───────┼──────┤  │
│                                      │  │ iPhone15 │ LOT-1 │  42   │ [10] │  │
│                                      │  │ MacBook  │   —   │  18   │ [ 5] │  │
│                                      │  │ AirPods  │ LOT-3 │   7   │ [ 2] │  │
│                                      │  ├──────────┴───────┴───────┴──────┤  │
│                                      │  │         [+ Add Item]            │  │
│                                      │  └──────────────────────────────────┘  │
│                                      │                                       │
│                                      │  Notes: [Optional notes...        ]   │
│                                      │                                       │
│                                      │  [ Cancel ]  [ Confirm Transaction ]  │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

### Component Architecture

```
RecordMovementDrawer/
├── RecordMovementDrawer.tsx      — Main drawer container + form orchestration
├── DrawerHeader.tsx              — Title bar with close button
├── MovementMetaFields.tsx        — Type, Reference #, Source/Destination selects
├── MovementItemGrid.tsx          — Dynamic item rows table
├── MovementItemRow.tsx           — Single row: product autocomplete + qty input
└── types.ts                      — Form types, validation schema
```

### State Management

```typescript
// Form schema (react-hook-form + zod)
interface MovementFormValues {
  movement_type_id: number;
  reference_id?: string;
  notes?: string;
  source_location_id: number;       // Source warehouse/location
  destination_location_id?: number;  // Required for Transfers
  items: MovementItemEntry[];
}

interface MovementItemEntry {
  item_id: number;
  lot_id?: number;          // Optional batch/lot
  quantity: number;          // Must be > 0
  // Read-only display fields (not submitted):
  item_name?: string;
  master_sku?: string;
  current_stock?: number;    // Fetched when item is selected
}
```

### Dynamic Behavior

| Trigger | Action |
|---------|--------|
| User selects Source Location | Fetch available items at that location via `GET /{warehouse_id}/inventory?location_id=X` |
| User selects a Product in a row | Fetch current stock at source location; populate `current_stock` read-only field |
| User types quantity > current_stock | Show inline validation error: "Quantity exceeds available stock (42)" |
| Movement type = "Receipt" | Hide Source field (items coming into warehouse); show only Destination |
| Movement type = "Shipment" | Hide Destination field (items leaving warehouse); show only Source |
| Movement type = "Transfer" | Show both Source and Destination fields |
| Movement type = "Adjustment" | Show Source only; allow negative quantities for write-offs |
| User clicks "+ Add Item" | Append a blank row via `useFieldArray` |
| User clicks row's X button | Remove row via `useFieldArray.remove(index)` |
| Confirm Transaction clicked | Validate all rows → POST `/movements` with the items array |

### Submission Payload

```json
POST /api/v1/warehouse/movements
{
  "movement_type_id": 3,
  "reference_id": "REF-2026-0045",
  "notes": "Monthly stock transfer",
  "transactions": [
    { "item_id": 101, "location_id": 5, "is_inbound": false, "quantity_change": 10 },
    { "item_id": 101, "location_id": 8, "is_inbound": true,  "quantity_change": 10 },
    { "item_id": 202, "location_id": 5, "is_inbound": false, "quantity_change": 5 },
    { "item_id": 202, "location_id": 8, "is_inbound": true,  "quantity_change": 5 }
  ]
}
```

For transfers, each item generates TWO transactions: outbound from source + inbound to destination.

### Backend Changes Required (Phase 1)

| Change | File | Description |
|--------|------|-------------|
| Location-scoped inventory query | `routers/warehouse.py` | Add `location_id` query param to `GET /{warehouse_id}/inventory` to filter stock at specific location |
| Multi-transaction validation | `routers/warehouse.py` | Existing `POST /movements` already supports multiple transactions — verify it handles transfer pairs correctly |
| Stock deduction on submit | `routers/warehouse.py` | Verify `InventoryLevel.quantity_available` is decremented on outbound and incremented on inbound |

### Files to Create

| File | Location | Purpose |
|------|----------|---------|
| `RecordMovementDrawer.tsx` | `pages/warehouse/` | Main drawer component |
| `MovementItemGrid.tsx` | `pages/warehouse/` | Dynamic item rows with useFieldArray |
| `MovementItemRow.tsx` | `pages/warehouse/` | Single product row with autocomplete |
| `movement.types.ts` | `pages/warehouse/` | Form types and zod validation schema |

### Files to Modify

| File | Change |
|------|--------|
| `InventoryMovementsPage.tsx` | Replace modal with drawer trigger; add drawer state |
| `api/base/warehouse.ts` | Add `listInventoryAtLocation(warehouseId, locationId)` if needed |
| `api/base_types/warehouse.ts` | Update `InventoryMovementCreate` if payload shape changes |

---

## Phase 2: Enhancing the Inventory Movements Table

### Goal

Transform the flat movement history table into a lifecycle-aware, expandable list that shows individual items within each grouped movement.

### Backend Changes Required (Phase 2)

#### New: Movement Status

Add a `status` field to the `InventoryMovement` model:

```python
# In models/warehouse.py — InventoryMovement
class MovementStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# New column on InventoryMovement:
status: str = Field(default="pending", max_length=20)
```

#### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `PATCH /movements/{id}/approve` | PATCH | Transition Pending → In-Transit; deduct stock from source |
| `PATCH /movements/{id}/complete` | PATCH | Transition In-Transit → Completed; add stock to destination |
| `PATCH /movements/{id}/cancel` | PATCH | Transition Pending → Cancelled; no stock changes |
| `GET /movements/{id}/items` | GET | Fetch transaction items for a single movement (for expandable row) |

#### Stock Lifecycle Logic

```
PENDING        → Stock NOT yet changed. Draft state.
                 User created the movement, awaiting approval.

IN_TRANSIT     → Stock DEDUCTED from source location.
                 Physically in transit to destination.

COMPLETED      → Stock ADDED to destination location.
                 Full cycle complete.

CANCELLED      → Movement voided. No stock changes.
                 If was IN_TRANSIT, stock is returned to source.
```

#### Alembic Migration

New migration to add `status` column to `inventory_movement` table:
- Default value: `'completed'` (for existing records — they're already applied)
- New movements created via the drawer will start as `'pending'`

### UI Enhancements

#### Expandable Rows

Since a single Movement now contains multiple items, clicking a row expands to show the `InventoryTransaction` children:

```
┌──────────┬──────────┬──────────────┬────────┬──────────┬─────────┐
│ Date     │ Type     │ Reference    │ Status │ Items    │ Actions │
├──────────┼──────────┼──────────────┼────────┼──────────┼─────────┤
│ Mar 11   │ Transfer │ REF-0045     │ 🟡 Pnd │ 3 items  │   ...   │
│  ▼ ──────┴──────────┴──────────────┴────────┴──────────┴─────────│
│  │ iPhone 15 Pro    │ LOT-001 │ A01-Z1-A01 → B03-Z2-A01 │ x10   │
│  │ MacBook Air M3   │    —    │ A01-Z1-A01 → B03-Z2-A01 │ x5    │
│  │ AirPods Pro 2    │ LOT-003 │ A01-Z1-A01 → B03-Z2-A01 │ x2    │
│  └──────────────────┴─────────┴────────────────────────┴────────│
├──────────┼──────────┼──────────────┼────────┼──────────┼─────────┤
│ Mar 10   │ Receipt  │ PO-1234      │ 🟢 Cmp │ 5 items  │   ...   │
└──────────┴──────────┴──────────────┴────────┴──────────┴─────────┘
```

#### Status Column

| Status | Badge | Color | Description |
|--------|-------|-------|-------------|
| Pending | `Pending` | Yellow (`bg-warning-bg text-warning-text`) | Draft; stock not yet changed |
| In-Transit | `In Transit` | Blue (`bg-info-bg text-info-text`) | Stock deducted from source |
| Completed | `Completed` | Green (`bg-success-bg text-success-text`) | Stock at destination |
| Cancelled | `Cancelled` | Gray (`bg-background text-text-secondary`) | Voided movement |

#### Quick Actions Menu (kebab `...`)

| Condition | Actions Available |
|-----------|-------------------|
| Status = Pending | Approve, Cancel |
| Status = In-Transit | Complete, Cancel (returns stock to source) |
| Status = Completed | — (no actions, final state) |
| Status = Cancelled | — (no actions, terminal state) |

### Component Architecture

```
InventoryMovementsPage.tsx (modified)
├── MovementStatusBadge.tsx         — Status pill component
├── MovementExpandedRow.tsx         — Expanded transaction items table
├── MovementActionMenu.tsx          — Kebab menu with lifecycle actions
└── RecordMovementDrawer/           — (from Phase 1)
```

### Files to Create

| File | Location | Purpose |
|------|----------|---------|
| `MovementStatusBadge.tsx` | `pages/warehouse/` | Colored status badge component |
| `MovementExpandedRow.tsx` | `pages/warehouse/` | Expanded row showing transaction items |
| `MovementActionMenu.tsx` | `pages/warehouse/` | Kebab menu with approve/complete/cancel |

### Files to Modify

| File | Change |
|------|--------|
| `InventoryMovementsPage.tsx` | Add expandable rows, status column, action menu |
| `models/warehouse.py` | Add `status` field to `InventoryMovement` |
| `routers/warehouse.py` | Add lifecycle endpoints (approve/complete/cancel) |
| `schemas/warehouse.py` | Add `MovementStatus` enum, update read schema |
| `api/base/warehouse.ts` | Add `approveMovement()`, `completeMovement()`, `cancelMovement()`, `getMovementItems()` |
| `api/base_types/warehouse.ts` | Add `MovementStatus` type, update `InventoryMovementRead` |
| Alembic migration | Add `status` column to `inventory_movement` |

---

## Phase 3: Intelligent Stock Levels & Analytics

### Goal

Make the Inventory Levels page smarter with dynamic threshold filtering and add a new analytics/reporting view for movement insights.

### 3A: Smart Stock Level Filtering

#### Current Behavior

The existing `InventoryLevelsPage` already has status tabs (All / OK / Low / Critical / Out of Stock / Overstock) backed by the `stock_status` property on `InventoryLevel`. This is already **server-side computed**.

#### Enhancements

| Enhancement | Description |
|-------------|-------------|
| Real-time refresh after movements | When a movement hits `Completed` in Phase 2, auto-invalidate the levels query via TanStack Query |
| Color-coded rows | Row background tint based on status (green OK, yellow Low, red Critical, gray OOS) |
| Inline threshold editing | Click reorder_point / safety_stock / max_stock to edit inline; saves via PATCH |
| Bulk threshold update | Select multiple rows → "Set Thresholds" bulk action |

#### Global Inventory Sync Hook

```typescript
// hooks/useInventorySync.ts
// A custom hook that listens for movement lifecycle changes and
// invalidates related queries (levels, alerts, movement history).

function useInventorySync() {
  const queryClient = useQueryClient();

  const invalidateInventory = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['inventory-levels'] });
    queryClient.invalidateQueries({ queryKey: ['inventory-alerts'] });
    queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
  }, [queryClient]);

  return { invalidateInventory };
}
```

This hook is called after:
- Movement created (Phase 1 drawer submit)
- Movement approved/completed/cancelled (Phase 2 lifecycle actions)
- Alert resolved (existing flow)

### 3B: Analytics Dashboard

#### New Page: Inventory Analytics

**Route:** `/inventory/analytics` (add to nav under Inventory section)

```
┌─────────────────────────────────────────────────────────────────┐
│  Inventory Analytics                              [Last 30d ▾]  │
├─────────────────────────────────┬───────────────────────────────┤
│                                 │                               │
│   Daily Movement Volume         │    Movement Type Breakdown     │
│   ┌─────────────────────┐       │    ┌─────────────────────┐    │
│   │ ▌                   │       │    │ Receipt    ████ 45%  │    │
│   │ ▌▌                  │       │    │ Transfer   ██   25%  │    │
│   │ ▌▌  ▌               │       │    │ Shipment   ██   20%  │    │
│   │ ▌▌▌ ▌▌  ▌           │       │    │ Adjustment █    10%  │    │
│   │ ▌▌▌▌▌▌▌ ▌▌          │       │    └─────────────────────┘    │
│   └─────────────────────┘       │                               │
│   Bar chart (d3 or recharts)    │    Donut/pie chart             │
│                                 │                               │
├─────────────────────────────────┼───────────────────────────────┤
│                                 │                               │
│   Top 10 High-Velocity Items    │    Stock Health Summary        │
│   ┌─────────────────────────┐   │    ┌─────────────────────┐    │
│   │ 1. iPhone 15 Pro   342  │   │    │ 🟢 OK         1,245 │    │
│   │ 2. MacBook Air     218  │   │    │ 🟡 Low           87 │    │
│   │ 3. AirPods Pro     195  │   │    │ 🔴 Critical       12│    │
│   │ 4. Galaxy S24      167  │   │    │ ⚫ Out of Stock    3 │    │
│   │ 5. Pixel 9         143  │   │    │ 🔵 Overstock       8 │    │
│   └─────────────────────────┘   │    └─────────────────────┘    │
│   Ranked by total qty moved     │    Pie chart + counts          │
│                                 │                               │
└─────────────────────────────────┴───────────────────────────────┘
```

#### Backend Endpoints Required

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /analytics/movements-per-day` | GET | Daily movement counts for date range; grouped by movement_type |
| `GET /analytics/top-items` | GET | Top N items by total quantity moved in date range |
| `GET /analytics/stock-health` | GET | Count of items per stock_status category |

#### Component Architecture

```
pages/warehouse/InventoryAnalyticsPage.tsx
├── DailyMovementChart.tsx        — Bar chart (d3 or recharts)
├── MovementTypeBreakdown.tsx     — Donut chart
├── TopMovedItemsList.tsx         — Ranked list of high-velocity items
├── StockHealthSummary.tsx        — Pie chart + status counts
└── DateRangeSelector.tsx         — Period picker (7d, 30d, 90d, custom)
```

### Files to Create

| File | Location | Purpose |
|------|----------|---------|
| `InventoryAnalyticsPage.tsx` | `pages/warehouse/` | Analytics dashboard page |
| `DailyMovementChart.tsx` | `pages/warehouse/` | Bar chart component |
| `MovementTypeBreakdown.tsx` | `pages/warehouse/` | Donut/pie chart |
| `TopMovedItemsList.tsx` | `pages/warehouse/` | Top items ranked list |
| `StockHealthSummary.tsx` | `pages/warehouse/` | Stock health pie chart |
| `useInventorySync.ts` | `hooks/` or `pages/warehouse/` | Global refetch hook |

### Files to Modify

| File | Change |
|------|--------|
| `InventoryLevelsPage.tsx` | Add row color coding, inline threshold editing, bulk actions |
| `routers/warehouse.py` | Add analytics endpoints |
| `schemas/warehouse.py` | Add analytics response schemas |
| `api/base/warehouse.ts` | Add analytics API functions |
| `api/base_types/warehouse.ts` | Add analytics types |
| `nav.config.tsx` | Add "Analytics" nav entry under Inventory section |
| `App.tsx` | Add `/inventory/analytics` route |

---

## Component Architecture Summary

| Feature | React Component | State / Library Logic |
|---------|----------------|----------------------|
| Movement Form | `RecordMovementDrawer` | `react-hook-form` + `zod` for cross-row validation. `useFieldArray` for dynamic item rows. |
| Warehouse Stock Check | `MovementItemRow` (inline) | `useQuery` fetched when `item_id` changes in a row — shows current stock at selected location. |
| Item Autocomplete | `MovementItemRow` (inline) | Debounced search against location-scoped inventory endpoint. |
| Lifecycle Table | `InventoryMovementsPage` (enhanced) | DataTable with `expandedRowId` + `renderExpandedRow` pattern (same as ItemsListPage). |
| Status Badges | `MovementStatusBadge` | Pure component: status string → colored pill. |
| Action Menu | `MovementActionMenu` | Kebab dropdown with conditional actions based on `movement.status`. |
| Global State Sync | `useInventorySync` | Custom hook calling `queryClient.invalidateQueries()` after any movement lifecycle change. |
| Analytics Charts | `DailyMovementChart` et al. | `d3` (already in project deps) or `recharts` for chart rendering. Date range param. |

---

## Step-by-Step Implementation Plan

Each step is self-contained and produces a testable deliverable. Steps within a phase are sequential (each builds on the previous). Phases themselves are sequential — Phase 2 requires Phase 1's drawer, Phase 3 requires Phase 2's lifecycle status.

---

### Phase 1: Multi-Item Movement Drawer

#### Step 1.0 — Install Dependencies

**Goal:** Add zod and hookform resolver to the frontend project.

**Actions:**
1. Run `npm install zod @hookform/resolvers` in the `frontend/` directory
2. Verify `package.json` updated with both packages
3. Run `npx tsc --noEmit` to confirm no type conflicts

**Files modified:**
- `frontend/package.json`
- `frontend/package-lock.json`

**Test:** `npm run dev` starts without errors.

---

#### Step 1.1 — Backend: Add `location_id` Filter to Inventory Levels Endpoint

**Goal:** Allow the Command Drawer to fetch items available at a specific location, not just an entire warehouse.

**Actions:**
1. Open `backend/app/routers/warehouse.py` — find the `GET /{warehouse_id}/inventory` endpoint
2. Add an optional `location_id: int | None = Query(None)` parameter
3. When `location_id` is provided, filter the query to `InventoryLevel.location_id == location_id` and `InventoryLevel.quantity_available > 0`
4. Update `backend/app/schemas/warehouse.py` if the response shape needs adjusting (likely not — same `InventoryLevelEnrichedRead`)

**Files modified:**
- `backend/app/routers/warehouse.py` — add query param + filter condition
- `frontend/src/api/base/warehouse.ts` — add `location_id` param to `listInventoryLevels()`
- `frontend/src/api/base_types/warehouse.ts` — update param interface if needed

**Test:** `GET /api/v1/warehouse/1/inventory?location_id=5` returns only items at location 5 with qty > 0.

---

#### Step 1.2 — Frontend: Create Movement Form Types and Validation Schema

**Goal:** Define the TypeScript interfaces and zod schema for the multi-item movement form.

**Actions:**
1. Create `frontend/src/pages/warehouse/movement.types.ts`
2. Define interfaces:
   - `MovementFormValues` — top-level form (movement_type_id, reference_id, notes, source_location_id, destination_location_id, items[])
   - `MovementItemEntry` — per-row (item_id, lot_id?, quantity, item_name?, master_sku?, current_stock?)
3. Define zod schema with cross-row validation:
   - Each item's `quantity > 0` and `quantity <= current_stock`
   - At least one item row required
   - Source != Destination (for transfers)
   - No duplicate `item_id` within the same form
4. Export the `zodResolver` wrapper for react-hook-form

**Files created:**
- `frontend/src/pages/warehouse/movement.types.ts`

**Test:** Import the schema in a scratch file and validate sample data — no TS errors.

---

#### Step 1.3 — Frontend: Build MovementItemRow Component

**Goal:** A single row in the item grid — product autocomplete + quantity input + stock display + remove button.

**Actions:**
1. Create `frontend/src/pages/warehouse/MovementItemRow.tsx`
2. Props: `index`, `control` (from useFormContext), `sourceLocationId`, `warehouseId`, `onRemove`
3. Product field: debounced search input (300ms) → calls `listInventoryLevels(warehouseId, { location_id, search })` → dropdown of matching items
4. When user selects an item:
   - Set `item_id`, `item_name`, `master_sku` in the form
   - Fetch current stock at source location → display as read-only "Available" badge
5. Quantity field: numeric input with min=1, max=current_stock validation (inline error)
6. Remove button: red X icon, calls `onRemove(index)`

**Files created:**
- `frontend/src/pages/warehouse/MovementItemRow.tsx`

**Test:** Render in isolation with mock data — autocomplete triggers search, stock displays correctly, validation fires on qty > stock.

---

#### Step 1.4 — Frontend: Build MovementItemGrid Component

**Goal:** Dynamic table of MovementItemRow components managed by `useFieldArray`.

**Actions:**
1. Create `frontend/src/pages/warehouse/MovementItemGrid.tsx`
2. Uses `useFieldArray({ control, name: 'items' })` from react-hook-form
3. Renders a table header row: Product | Available | Qty | Action
4. Maps `fields` array → `<MovementItemRow>` for each entry
5. "+ Add Item" button at bottom appends a blank row via `append()`
6. Prevents removing the last row (minimum 1 item required)
7. Shows form-level errors (e.g., "Duplicate item" from zod refine)

**Files created:**
- `frontend/src/pages/warehouse/MovementItemGrid.tsx`

**Test:** Add/remove rows works, minimum 1 row enforced, duplicate item_id shows error.

---

#### Step 1.5 — Frontend: Build RecordMovementDrawer Component

**Goal:** The main slide-over drawer that wraps the metadata fields + item grid + submit.

**Actions:**
1. Create `frontend/src/pages/warehouse/RecordMovementDrawer.tsx`
2. Props: `open: boolean`, `onClose: () => void`, `warehouseId: number`, `onSuccess: () => void`
3. Layout structure:
   ```
   Overlay (dark backdrop, click to close)
   └── Drawer panel (right-side, w-[560px], slide animation)
       ├── Header: "Record Movement" + close button
       ├── Metadata section:
       │   ├── Movement Type dropdown (fetched via listMovementTypes())
       │   ├── Reference # text input
       │   ├── Source Location dropdown (fetched via listLocations())
       │   └── Destination Location dropdown (conditional: only for Transfer type)
       ├── Item Grid: <MovementItemGrid />
       ├── Notes textarea
       └── Footer: [Cancel] [Confirm Transaction]
   ```
4. Form orchestration:
   - `useForm<MovementFormValues>` with `zodResolver(movementSchema)`
   - On submit: build transactions array from items (for transfers, generate 2 txn per item)
   - Call `createMovement(payload)` → on success, call `onSuccess()` and close drawer
   - Show loading spinner on submit button while API call is in progress
5. Movement-type-aware field visibility:
   - Receipt: hide Source, show Destination only
   - Shipment: show Source only, hide Destination
   - Transfer: show both, validate Source != Destination
   - Adjustment: show Source only, allow any quantity (positive = add, negative = remove)
6. Animation: slide in from right with `transition-transform duration-300`

**Files created:**
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx`

**Test:** Open drawer, select type, add items, submit — creates movement via API. Transfer generates paired transactions. Validation prevents same source/destination.

---

#### Step 1.6 — Frontend: Integrate Drawer into InventoryMovementsPage

**Goal:** Replace the existing single-item modal with the new drawer.

**Actions:**
1. Open `frontend/src/pages/warehouse/InventoryMovementsPage.tsx`
2. Remove the existing modal state, modal component, and modal-related handlers
3. Add state: `const [drawerOpen, setDrawerOpen] = useState(false)`
4. Wire "+ Record Movement" button to `setDrawerOpen(true)`
5. Render `<RecordMovementDrawer>` at the bottom of the component tree
6. On success callback: refetch the movement history list
7. Keep the existing movement history table as-is (Phase 2 will enhance it)

**Files modified:**
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` — remove modal, add drawer

**Test:** End-to-end: click button → drawer opens → add multiple items → submit → movement appears in history table → drawer closes.

---

#### Step 1.7 — Phase 1 Verification and Documentation

**Actions:**
1. Run `npx tsc --noEmit` — zero errors
2. Manual test: create a Transfer with 3 items between two locations
3. Manual test: create a Receipt with 2 items into a location
4. Manual test: validation — qty exceeds stock, same source/destination, duplicate items
5. Update `docs/official_documentation/version_update.md` with Phase 1 entry
6. Update `docs/official_documentation/frontend-development-progress.md`
7. Update `docs/official_documentation/web-api.md` if endpoint params changed

**Deliverable:** Phase 1 complete. Users can record multi-item movements via the drawer.

---

### Phase 2: Movement Lifecycle and Enhanced Table

#### Step 2.0 — Backend: Add `status` Column to InventoryMovement

**Goal:** Track movement lifecycle (pending → in_transit → completed → cancelled).

**Actions:**
1. Open `backend/app/models/warehouse.py`
2. Add `status` field to `InventoryMovement`:
   ```python
   status: str = Field(default="pending", max_length=20)
   ```
3. Create Alembic migration:
   ```bash
   alembic revision --autogenerate -m "add_status_to_inventory_movement"
   ```
4. Edit migration: set `server_default='completed'` so existing records are treated as already-applied
5. Apply migration: `alembic upgrade head`
6. Update `backend/app/schemas/warehouse.py`:
   - Add `MovementStatus` literal type to `InventoryMovementRead`
   - Add `status` field to read schema

**Files modified:**
- `backend/app/models/warehouse.py` — add field
- `backend/app/schemas/warehouse.py` — add status to read schema
- New Alembic migration file

**Test:** `GET /api/v1/warehouse/1/movements` returns `"status": "completed"` for existing records.

---

#### Step 2.1 — Backend: Update Movement Creation to Set Status = "pending"

**Goal:** New movements created via the drawer start as "pending" (stock not yet deducted).

**Actions:**
1. Open `backend/app/routers/warehouse.py` — find the `POST /movements` endpoint
2. Modify: set `movement.status = "pending"` on creation
3. Remove the immediate stock-level update logic from this endpoint (stock changes move to approve/complete)
4. Keep the transaction row creation (they record what will happen, not what has happened yet)

**Files modified:**
- `backend/app/routers/warehouse.py` — modify POST endpoint

**Test:** Create a movement via the drawer → status = "pending", stock levels unchanged.

---

#### Step 2.2 — Backend: Add Lifecycle Transition Endpoints

**Goal:** Three new endpoints to transition movement status and apply stock changes at the right lifecycle stage.

**Actions:**
1. Add `PATCH /movements/{id}/approve`:
   - Validates: current status must be "pending"
   - Transitions to "in_transit"
   - Deducts stock from source: `InventoryLevel.quantity_available -= qty` for all outbound transactions
   - Creates alerts if source stock falls below thresholds
2. Add `PATCH /movements/{id}/complete`:
   - Validates: current status must be "in_transit"
   - Transitions to "completed"
   - Adds stock to destination: `InventoryLevel.quantity_available += qty` for all inbound transactions
   - Creates alerts if destination stock exceeds max_stock (overstock)
3. Add `PATCH /movements/{id}/cancel`:
   - Validates: current status must be "pending" or "in_transit"
   - Transitions to "cancelled"
   - If was "in_transit": reverse the source deduction (return stock to source)
   - If was "pending": no stock changes needed

**Files modified:**
- `backend/app/routers/warehouse.py` — add 3 endpoints

**Test:**
- Pending → Approve → source stock decreases
- In-Transit → Complete → destination stock increases
- Pending → Cancel → no stock changes
- In-Transit → Cancel → source stock restored
- Completed → Approve → 422 error (invalid transition)

---

#### Step 2.3 — Backend: Add Movement Items Detail Endpoint

**Goal:** Fetch individual transaction items for a specific movement (powers expandable rows).

**Actions:**
1. Add `GET /movements/{id}/items`:
   - Returns list of transactions with enriched item data (item_name, master_sku, location code)
   - Groups outbound/inbound pairs for transfers (show "A01 → B03" in one row)
2. Update `backend/app/schemas/warehouse.py` — add `MovementItemDetailRead` schema

**Files modified:**
- `backend/app/routers/warehouse.py` — add endpoint
- `backend/app/schemas/warehouse.py` — add response schema

**Test:** `GET /api/v1/warehouse/movements/1/items` returns enriched transaction list.

---

#### Step 2.4 — Frontend: Add Lifecycle API Functions and Types

**Goal:** Wire the new backend endpoints into the frontend API layer.

**Actions:**
1. Open `frontend/src/api/base_types/warehouse.ts`:
   - Add `MovementStatus = 'pending' | 'in_transit' | 'completed' | 'cancelled'`
   - Add `status: MovementStatus` to `InventoryMovementRead`
   - Add `MovementItemDetail` interface (item_name, master_sku, location_from, location_to, quantity)
2. Open `frontend/src/api/base/warehouse.ts`:
   - Add `approveMovement(movementId: number)`
   - Add `completeMovement(movementId: number)`
   - Add `cancelMovement(movementId: number)`
   - Add `getMovementItems(movementId: number): Promise<MovementItemDetail[]>`

**Files modified:**
- `frontend/src/api/base_types/warehouse.ts`
- `frontend/src/api/base/warehouse.ts`

**Test:** TypeScript compiles cleanly.

---

#### Step 2.5 — Frontend: Create MovementStatusBadge Component

**Goal:** Reusable colored pill for movement status.

**Actions:**
1. Create `frontend/src/pages/warehouse/MovementStatusBadge.tsx`
2. Props: `status: MovementStatus`
3. Color mapping:
   - `pending` → yellow (`bg-warning-bg text-warning-text`)
   - `in_transit` → blue (`bg-info-bg text-info-text`)
   - `completed` → green (`bg-success-bg text-success-text`)
   - `cancelled` → gray (`bg-background text-text-secondary`)

**Files created:**
- `frontend/src/pages/warehouse/MovementStatusBadge.tsx`

---

#### Step 2.6 — Frontend: Create MovementExpandedRow Component

**Goal:** When a movement row is expanded, show the individual items/transactions.

**Actions:**
1. Create `frontend/src/pages/warehouse/MovementExpandedRow.tsx`
2. Props: `movementId: number`
3. On mount: fetch `getMovementItems(movementId)` → show loading spinner → render table
4. Table columns: Item | SKU | From → To | Quantity
5. For non-transfer types, show only one location (no arrow)

**Files created:**
- `frontend/src/pages/warehouse/MovementExpandedRow.tsx`

---

#### Step 2.7 — Frontend: Create MovementActionMenu Component

**Goal:** Kebab (...) dropdown with lifecycle actions contextual to the movement's current status.

**Actions:**
1. Create `frontend/src/pages/warehouse/MovementActionMenu.tsx`
2. Props: `movement: InventoryMovementRead`, `onAction: () => void` (callback to refetch)
3. Conditional menu items:
   - Status `pending`: "Approve" (→ in_transit), "Cancel" (→ cancelled)
   - Status `in_transit`: "Complete" (→ completed), "Cancel" (→ cancelled, returns stock)
   - Status `completed` or `cancelled`: no actions (show "—" or hide menu)
4. Each action: confirm dialog → API call → onAction() callback → toast/refetch
5. Use the existing `StandardActionMenu` component if it fits, or build a lightweight dropdown

**Files created:**
- `frontend/src/pages/warehouse/MovementActionMenu.tsx`

---

#### Step 2.8 — Frontend: Enhance InventoryMovementsPage with Expandable Rows, Status, and Actions

**Goal:** Integrate the three new components into the movement history table.

**Actions:**
1. Open `frontend/src/pages/warehouse/InventoryMovementsPage.tsx`
2. Add `Status` column using `<MovementStatusBadge>` — positioned before QTY column
3. Add `Items` column showing count (e.g., "3 items") — clickable to expand
4. Add `Actions` column with `<MovementActionMenu>` — positioned as last column
5. Wire expandable row pattern:
   - State: `expandedId: number | null`
   - `onRowClick` → toggles `expandedId`
   - `renderExpandedRow(movement)` → `<MovementExpandedRow movementId={movement.id} />`
6. Add filter tabs or dropdown for status filtering (All / Pending / In Transit / Completed / Cancelled)
7. After any lifecycle action completes, refetch the movement list

**Files modified:**
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx`

**Test:** End-to-end lifecycle:
1. Create movement → appears as "Pending"
2. Expand row → see item details
3. Click ... → Approve → status changes to "In Transit", source stock decreases
4. Click ... → Complete → status changes to "Completed", destination stock increases
5. Create another movement → Cancel → status = "Cancelled", no stock change

---

#### Step 2.9 — Phase 2 Verification and Documentation

**Actions:**
1. Run `npx tsc --noEmit` — zero errors
2. Full lifecycle test: Pending → In-Transit → Completed
3. Cancel from Pending test
4. Cancel from In-Transit test (verify stock returned to source)
5. Verify expandable rows load correctly for movements with 1, 3, 5+ items
6. Update `docs/official_documentation/version_update.md`
7. Update `docs/official_documentation/frontend-development-progress.md`
8. Update `docs/official_documentation/web-api.md` — document all 4 new endpoints
9. Update `docs/official_documentation/database_structure.md` — add `status` column

**Deliverable:** Phase 2 complete. Movements have full lifecycle tracking with expandable details and quick actions.

---

### Phase 3: Intelligent Stock Levels and Analytics

#### Step 3.0 — Frontend: Create useInventorySync Hook

**Goal:** A shared hook that invalidates all inventory-related TanStack Query caches after any mutation.

**Actions:**
1. Create `frontend/src/pages/warehouse/useInventorySync.ts`
2. Implementation:
   ```typescript
   export function useInventorySync() {
     const queryClient = useQueryClient();
     const invalidateAll = useCallback(() => {
       queryClient.invalidateQueries({ queryKey: ['inventory-levels'] });
       queryClient.invalidateQueries({ queryKey: ['inventory-alerts'] });
       queryClient.invalidateQueries({ queryKey: ['inventory-movements'] });
       queryClient.invalidateQueries({ queryKey: ['inventory-analytics'] });
     }, [queryClient]);
     return { invalidateAll };
   }
   ```
3. Integrate into:
   - `RecordMovementDrawer` — call after successful movement creation
   - `MovementActionMenu` — call after approve/complete/cancel
   - `InventoryAlertsPage` — call after alert resolution

**Files created:**
- `frontend/src/pages/warehouse/useInventorySync.ts`

**Files modified:**
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx` — add sync call
- `frontend/src/pages/warehouse/MovementActionMenu.tsx` — add sync call
- `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` — add sync call

**Test:** Complete a movement → switch to Levels tab → data refreshes automatically without manual page reload.

---

#### Step 3.1 — Frontend: Enhance InventoryLevelsPage with Row Colouring and Inline Editing

**Goal:** Visual row tinting by stock status + click-to-edit thresholds.

**Actions:**
1. Open `frontend/src/pages/warehouse/InventoryLevelsPage.tsx`
2. Add row background tint based on `stock_status`:
   - `ok` → no tint (default)
   - `low` → `bg-warning-bg/30` (subtle yellow)
   - `critical` → `bg-error-bg/30` (subtle red)
   - `out_of_stock` → `bg-background` (gray)
   - `overstock` → `bg-info-bg/30` (subtle blue)
3. Make threshold columns (reorder_point, safety_stock, max_stock) editable:
   - Click cell → inline number input
   - On blur or Enter → PATCH update via API
   - Show save indicator (brief green flash on success)
4. Convert from manual `useState` + `useEffect` fetching to TanStack `useQuery` with `queryKey: ['inventory-levels', warehouseId, params]` — enables the sync hook from Step 3.0

**Files modified:**
- `frontend/src/pages/warehouse/InventoryLevelsPage.tsx`

**Test:** Low stock rows show yellow tint. Click reorder_point → edit → blur → value saved. Movement completion auto-refreshes the table.

---

#### Step 3.2 — Backend: Add Analytics Endpoints

**Goal:** Three new endpoints that aggregate movement/inventory data for dashboards.

**Actions:**
1. Add `GET /analytics/movements-per-day`:
   - Query params: `warehouse_id`, `date_from`, `date_to`
   - Returns: `{ date: string, movement_type: string, count: number }[]`
   - SQL: `SELECT DATE(created_at), movement_type_id, COUNT(*) FROM inventory_movement WHERE ... GROUP BY 1, 2`
2. Add `GET /analytics/top-items`:
   - Query params: `warehouse_id`, `date_from`, `date_to`, `limit` (default 10)
   - Returns: `{ item_id: number, item_name: string, master_sku: string, total_qty: number }[]`
   - SQL: `SELECT item_id, SUM(ABS(quantity_change)) FROM inventory_transaction WHERE ... GROUP BY item_id ORDER BY 2 DESC LIMIT N`
3. Add `GET /analytics/stock-health`:
   - Query params: `warehouse_id`
   - Returns: `{ status: string, count: number }[]`
   - SQL: computed from `InventoryLevel` threshold comparison (matches the model's `stock_status` property)
4. Add response schemas to `backend/app/schemas/warehouse.py`
5. Register endpoints in the warehouse router

**Files modified:**
- `backend/app/routers/warehouse.py` — add 3 endpoints
- `backend/app/schemas/warehouse.py` — add analytics response schemas

**Test:**
- `GET /analytics/movements-per-day?warehouse_id=1&date_from=2026-03-01&date_to=2026-03-11` → returns daily counts
- `GET /analytics/top-items?warehouse_id=1&limit=5` → returns top 5 items
- `GET /analytics/stock-health?warehouse_id=1` → returns status distribution

---

#### Step 3.3 — Frontend: Add Analytics API Functions and Types

**Goal:** Frontend API layer for the three analytics endpoints.

**Actions:**
1. Open `frontend/src/api/base_types/warehouse.ts`:
   - Add `MovementPerDay = { date: string; movement_type: string; count: number }`
   - Add `TopMovedItem = { item_id: number; item_name: string; master_sku: string; total_qty: number }`
   - Add `StockHealthEntry = { status: StockStatus; count: number }`
   - Add `AnalyticsDateRange = { date_from: string; date_to: string }`
2. Open `frontend/src/api/base/warehouse.ts`:
   - Add `getMovementsPerDay(warehouseId, dateRange)`
   - Add `getTopItems(warehouseId, dateRange, limit?)`
   - Add `getStockHealth(warehouseId)`

**Files modified:**
- `frontend/src/api/base_types/warehouse.ts`
- `frontend/src/api/base/warehouse.ts`

**Test:** TypeScript compiles. Functions callable from console.

---

#### Step 3.4 — Frontend: Build Analytics Chart Components

**Goal:** Four visualisation components using d3 (already installed).

**Actions:**
1. Create `frontend/src/pages/warehouse/DailyMovementChart.tsx`:
   - Props: `data: MovementPerDay[]`
   - Stacked bar chart: X = date, Y = count, color-coded by movement_type
   - d3 scales + axes + responsive SVG
2. Create `frontend/src/pages/warehouse/MovementTypeBreakdown.tsx`:
   - Props: `data: { type: string; count: number }[]`
   - Donut chart with legend showing percentages
3. Create `frontend/src/pages/warehouse/TopMovedItemsList.tsx`:
   - Props: `data: TopMovedItem[]`
   - Pure Tailwind — ranked list with position number, item name, SKU, total qty bar
   - No chart library needed — progress bar showing relative qty
4. Create `frontend/src/pages/warehouse/StockHealthSummary.tsx`:
   - Props: `data: StockHealthEntry[]`
   - Pie chart + right-side legend with status counts
   - Color palette matches the existing StockStatusBadge colours

**Files created:**
- `frontend/src/pages/warehouse/DailyMovementChart.tsx`
- `frontend/src/pages/warehouse/MovementTypeBreakdown.tsx`
- `frontend/src/pages/warehouse/TopMovedItemsList.tsx`
- `frontend/src/pages/warehouse/StockHealthSummary.tsx`

---

#### Step 3.5 — Frontend: Build InventoryAnalyticsPage

**Goal:** The main analytics dashboard page composing all chart components.

**Actions:**
1. Create `frontend/src/pages/warehouse/InventoryAnalyticsPage.tsx`
2. Layout: 2x2 grid of chart cards with a date range selector at the top
3. Date range presets: Last 7 Days, Last 30 Days, Last 90 Days, Year to Date, Custom
4. Data fetching: 3 parallel `useQuery` calls with `queryKey: ['inventory-analytics', ...]`
5. Loading states: skeleton placeholders for each chart card
6. Empty states: "No movement data for this period" when all counts are zero
7. Uses `WarehouseContext` for the selected warehouse

**Files created:**
- `frontend/src/pages/warehouse/InventoryAnalyticsPage.tsx`

---

#### Step 3.6 — Frontend: Add Analytics to Navigation and Routing

**Goal:** Make the analytics page accessible from the sidebar.

**Actions:**
1. Open `frontend/src/components/layout/nav.config.tsx`:
   - Add "Analytics" entry under the Inventory section (after "Triggers")
   - Icon: `BarChartIcon` (already imported for Dashboard)
   - Path: `/inventory/analytics`
2. Open `frontend/src/App.tsx`:
   - Import `InventoryAnalyticsPage`
   - Add route: `<Route path="/inventory/analytics" element={<InventoryAnalyticsPage />} />`

**Files modified:**
- `frontend/src/components/layout/nav.config.tsx`
- `frontend/src/App.tsx`

**Test:** Click "Analytics" in sidebar → page loads with charts populated from API data.

---

#### Step 3.7 — Phase 3 Verification and Documentation

**Actions:**
1. Run `npx tsc --noEmit` — zero errors
2. Test analytics with date ranges: 7d, 30d, 90d, custom
3. Test auto-refresh: complete a movement → switch to analytics → charts update
4. Test auto-refresh: switch to levels tab → data reflects movement
5. Test inline threshold editing on levels page
6. Test row colouring matches stock status
7. Update `docs/official_documentation/version_update.md`
8. Update `docs/official_documentation/frontend-development-progress.md`
9. Update `docs/official_documentation/web-api.md` — document 3 analytics endpoints
10. Mark all success criteria checkboxes in this plan

**Deliverable:** Phase 3 complete. Full inventory intelligence platform with reactive data flow and analytics.

---

## Dependencies & Prerequisites

| Dependency | Status | Notes |
|------------|--------|-------|
| `react-hook-form` | Installed | Already used in ItemFormPage, BundleFormPage |
| `zod` | **Not installed** | Needed for cross-row validation in movement form (install in Step 1.0) |
| `@hookform/resolvers` | **Not installed** | Bridges zod to react-hook-form (install in Step 1.0) |
| `d3` | Installed | Already in project deps (used in DashboardPage) |
| `recharts` | **Not needed** | Using d3 instead |
| DataTable expandable rows | Implemented | Already used in ItemsListPage (expandedRowId pattern) |
| WarehouseContext | Implemented | All pages depend on selected warehouse |
| TanStack Query | Installed | Used for data fetching + cache invalidation |

### Packages to Install (Step 1.0)

```bash
cd frontend && npm install zod @hookform/resolvers
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Movement status migration on existing data | Medium | Default existing records to `completed` since they're already applied (Step 2.0) |
| Transfer creates 2 transactions per item (outbound + inbound) | Low | Already supported by backend `POST /movements` — frontend generates pairs in Step 1.5 |
| Analytics queries on large datasets | Medium | Add date range filters + DB indexes on `created_at`; paginate top-items (Step 3.2) |
| Drawer width on mobile/small screens | Low | Use responsive breakpoints — full-width on mobile, slide-over on desktop (Step 1.5) |
| Cross-row validation (total qty vs available stock) | Medium | Zod `.refine()` with form-level validation; show summary errors above grid (Step 1.2) |
| Concurrent stock modifications | Medium | Pessimistic validation (re-check stock before submit); DB-level constraint on qty >= 0 (Step 2.2) |
| Phase 2 changes POST /movements behavior | High | Must coordinate: old movements = completed, new movements = pending. Clear migration boundary in Step 2.0–2.1 |

---

## Success Criteria

- [ ] Users can record multi-item movements in a single transaction via the drawer
- [ ] Movement history shows expandable rows with individual items per movement
- [ ] Movement lifecycle (Pending → In-Transit → Completed) is fully tracked
- [ ] Approve/Cancel quick actions work from the movement table
- [ ] Stock levels auto-refresh when movements complete
- [ ] Analytics dashboard shows daily volume, top items, and stock health
- [ ] All forms have comprehensive client-side validation
- [ ] All new endpoints documented in `web-api.md`

---

## Appendix: Architectural Paradigms for High-Density Multi-Item Stock Management and Operational Intelligence

The evolution of modern inventory systems has transitioned from simple record-keeping ledgers to high-performance, reactive environments that prioritize transactional integrity and user-centric data density. The Warehouse Operational Management System (WOMS) architecture represents a significant shift in how inventory movements are processed, moving away from legacy single-entry models toward an integrated, multi-item "invoice-style" framework.

---

### A1. High-Density User Interface Design: The Command Drawer Framework

The central pillar of the WOMS modernization strategy is the implementation of the "Command Drawer," a sophisticated UI component designed to replace traditional modal-based entry forms. The Command Drawer, implemented as a right-side slide-over, addresses the need for contextual awareness by maintaining the visibility of the underlying data layer while the user populates a movement request.

#### A1.1 Contextual Awareness and the Record Movement Trigger

The interface is initiated by the "+ Record Movement" action button. The header section of this drawer is strategically reserved for global transaction metadata. Based on the `InventoryMovement` schema, this section captures the `movement_type_id` (e.g., Transfer, Adjustment) and a `reference_id` for external document linking (such as a PO or Shipment number).

For transfers, the interface must handle logic for both a **Source Location** and a **Destination Location**. The implementation ensures that the `source_location_id` cannot be equivalent to the `destination_location_id`. If a user attempts to select the same location for both parameters, the system dynamically disables the submission mechanism to prevent illogical transactions.

#### A1.2 The Dynamic Grid and Product Autocomplete Logic

The core of the "Invoice Style" interface is the dynamic grid, which allows for the simultaneous entry of multiple line items. In the database, these items are represented as entries in the `InventoryTransaction` table.

| Grid Field | Control Type | Logic / Validation Requirement |
|------------|-------------|-------------------------------|
| Product | Autocomplete Combobox (Headless) | Asynchronous search against the Items table with SKU filtering. Results scoped to items present at the selected source location. |
| Available Quantity | Read-Only Numeric | Dynamic fetch from `InventoryLevel.quantity_available` based on `item_id` and `location_id`. Updated when product selection changes. |
| Move Quantity | Numeric Input | Constraint: `move_qty <= quantity_available`. Maps directly to `InventoryTransaction.quantity_change`. |
| Row Controls | Action Buttons | Ability to append or remove rows via `useFieldArray`. Minimum one row required. |

---

### A2. Stock Level Module: Reactive Health Management

The Inventory Levels view serves as the operational nerve center, mapped directly to the `InventoryLevel` table. It requires a tiered filtering system based on health metrics stored in the schema.

#### A2.1 Status Classification and Threshold Logic

The system derives the "Status" column dynamically by comparing the `quantity_available` against the following threshold fields defined in the `InventoryLevel` table:

| Status | Condition | Visual |
|--------|-----------|--------|
| **Critical** | `quantity_available <= safety_stock` | Red badge |
| **Low** | `safety_stock < quantity_available <= reorder_point` | Yellow badge |
| **OK** | `quantity_available > reorder_point` | Green badge |
| **Out of Stock** | `quantity_available = 0` | Gray badge |
| **Overstock** | `quantity_available > max_stock` | Blue badge |

Priority ordering: Out of Stock > Critical > Low > Overstock > OK (highest severity wins).

#### A2.2 Interactive Filtering and Alert Integration

The UI utilises a multi-tab interface (All, OK, Low, etc.) to update API parameters (e.g., `GET /inventory?status=low`). This view also integrates with the `InventoryAlert` table, which logs automated PostgreSQL triggers when `quantity_available` falls below the `threshold_quantity`.

When a movement transitions to `Completed` (Phase 2 lifecycle), the stock levels view must automatically re-fetch via TanStack Query invalidation to reflect the updated quantities.

---

### A3. Movements Module: Transactional Ledger and Lifecycle

The Inventory Movements view tracks the historical "why" and "when" of inventory changes through the `InventoryMovement` (header) and `InventoryTransaction` (lines) tables.

#### A3.1 The Movement Ledger Table

The primary ledger displays data from the `InventoryMovement` table with the following headers:

| Header | Description | Schema Field |
|--------|-------------|-------------|
| DATE | Timestamp of the transaction creation | `InventoryMovement.created_at` |
| TYPE | Operational classification (from Movement Type table) | `MovementType.movement_name` |
| ITEM | Associated item(s) from the transaction | `InventoryTransaction.item_id` (aggregated) |
| REF | External document reference | `InventoryMovement.reference_id` |
| STATUS | Lifecycle state (Phase 2) | `InventoryMovement.status` |
| QTY | The net change in inventory | `InventoryTransaction.quantity_change` (summed) |

#### A3.2 Transaction Logic for Multi-Item Transfers

A single movement often involves multiple transactions. For instance, a "Transfer" between locations involves an atomic operation creating:

1. **One** `InventoryMovement` record (the parent header).
2. **Two** `InventoryTransaction` records **per item**: one with `is_inbound = false` (deduction from source) and one with `is_inbound = true` (addition to destination).

For a transfer of 3 items, this generates 1 movement header + 6 transaction rows. The frontend must construct this payload from the drawer's flat item grid.

```
User enters in drawer:          Backend receives:
┌────────────┬─────┐            ┌─────────────────────────────────────────┐
│ iPhone 15  │ x10 │  ───────►  │ { item_id:101, loc:5, inbound:false }  │
│            │     │            │ { item_id:101, loc:8, inbound:true  }  │
├────────────┼─────┤            ├─────────────────────────────────────────┤
│ MacBook    │ x5  │  ───────►  │ { item_id:202, loc:5, inbound:false }  │
│            │     │            │ { item_id:202, loc:8, inbound:true  }  │
└────────────┴─────┘            └─────────────────────────────────────────┘
```

---

### A4. Stock Check Module: Discrepancy and Reconciliation

This module handles physical audits, utilising the `InventoryLevel` snapshot as the "System Qty" baseline.

#### A4.1 Discrepancy Reporting

Once the physical count is entered, the system calculates the variance:

```
Discrepancy Rate (%) = |Physical Count - quantity_available| / quantity_available * 100
```

Upon closing the session, the system generates an **Adjustment** movement. This creates an `InventoryTransaction` record where the `quantity_change` reconciles the difference, and the event is logged in `InventoryReplenishmentHistory` if thresholds were adjusted.

#### A4.2 Audit Trail

Every stock check session produces:

| Record | Table | Purpose |
|--------|-------|---------|
| Adjustment movement | `InventoryMovement` | Header with `movement_type = Adjustment` |
| Delta transactions | `InventoryTransaction` | `quantity_change = physical_count - system_qty` per item/location |
| Threshold log | `InventoryReplenishmentHistory` | If reorder_point or safety_stock were updated during reconciliation |
| Alert resolution | `InventoryAlert` | Auto-resolves existing alerts if stock now exceeds thresholds |

---

### A5. Technical Implementation and API Strategy

#### A5.1 Atomic Transactions and Integrity

To prevent "Ghost Inventory," the system ensures that updates to `InventoryLevel` and the creation of `InventoryTransaction` occur within a **single database transaction**. This is critical for `StockLot` tracking (FIFO/FEFO), ensuring that `lot_id` and `quantity_available` stay perfectly synchronised.

The backend uses SQLAlchemy's async session with explicit `flush()` and deferred `commit()`:

```python
async with session.begin():
    # 1. Create movement header
    session.add(movement)
    await session.flush()

    # 2. Create transaction rows
    for txn in transactions:
        session.add(txn)

    # 3. Update inventory levels
    for level_update in level_deltas:
        level.quantity_available += level_update.delta

    # 4. Check for alert triggers
    await check_and_create_alerts(session, affected_levels)

    # commit() is implicit on exit
```

If any step fails, the entire transaction rolls back — no partial stock updates.

#### A5.2 Real-Time Validation and Optimistic Updates

Concurrency is managed by checking `InventoryLevel.quantity_available` via `GET /warehouses/{id}/inventory?item_id=X&location_id=Y` whenever a quantity is modified in the Command Drawer. This provides "just-in-time" verification before final submission.

The frontend uses **optimistic updates** for status toggles and alert resolutions (instant UI feedback, rollback on error), but **pessimistic validation** for stock movements (verify quantities before submission, no optimistic deduction).

#### A5.3 Location-Scoped Queries

The Command Drawer requires inventory data scoped to a specific location, not just a warehouse. This requires extending the existing `GET /{warehouse_id}/inventory` endpoint:

| Current | Enhanced |
|---------|----------|
| `GET /{warehouse_id}/inventory` | `GET /{warehouse_id}/inventory?location_id=5` |
| Returns all items across all locations | Returns only items at location 5 with qty > 0 |

---

### A6. Analytics: Operational Intelligence

The "Reports" section transforms raw transactional data into actionable KPIs:

#### A6.1 Core Metrics

| Metric | Calculation | Data Source |
|--------|------------|-------------|
| **Inventory Turnover Rate** | `SUM(outbound_qty) / AVG(quantity_available)` over period | `InventoryTransaction` (outbound) + `InventoryLevel` snapshots |
| **Discrepancy Rate** | `COUNT(adjustment_movements) / COUNT(all_movements) * 100` | `InventoryMovement` where `movement_type = Adjustment` |
| **Daily Movement Volume** | `COUNT(movements)` grouped by `DATE(created_at)` | `InventoryMovement.created_at` |
| **Top Items by Velocity** | `SUM(ABS(quantity_change))` grouped by `item_id`, ordered DESC | `InventoryTransaction` |
| **Stock Health Distribution** | `COUNT(*)` grouped by computed `stock_status` | `InventoryLevel` with threshold comparison |
| **Average Fulfillment Time** | `AVG(completed_at - created_at)` for completed movements | `InventoryMovement` (requires Phase 2 `status` + timestamps) |

#### A6.2 Visualisation Strategy

| Chart | Library | Data Shape |
|-------|---------|-----------|
| Daily movement bar chart | `d3` (already installed) | `{ date: string, receipts: number, transfers: number, shipments: number }[]` |
| Movement type donut | `d3` | `{ type: string, count: number }[]` |
| Top items ranked list | Pure Tailwind (no chart lib) | `{ item_name: string, sku: string, total_qty: number }[]` |
| Stock health pie chart | `d3` | `{ status: StockStatus, count: number }[]` |

All analytics queries accept a `date_from` and `date_to` parameter with preset shortcuts (7d, 30d, 90d, YTD, Custom range).

---

### A7. Cross-Module Data Flow

The following diagram illustrates how data flows across the inventory modules when a movement is created and completed:

```
User: "+ Record Movement"
        │
        ▼
┌─────────────────────┐
│  Command Drawer      │
│  (Phase 1)           │
│  - Select type       │
│  - Add items         │
│  - Set quantities    │
└────────┬────────────┘
         │ POST /movements
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│ InventoryMovement    │────►│ InventoryTransaction │
│ status: PENDING      │     │ (1 per item+dir)     │
└────────┬────────────┘     └──────────────────────┘
         │
         │ PATCH /movements/{id}/approve
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│ status: IN_TRANSIT   │────►│ InventoryLevel       │
│                      │     │ source.qty -= delta  │
└────────┬────────────┘     └──────────────────────┘
         │
         │ PATCH /movements/{id}/complete
         ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ status: COMPLETED    │────►│ InventoryLevel       │────►│ InventoryAlert   │
│                      │     │ dest.qty += delta    │     │ (if threshold    │
└──────────────────────┘     └──────────────────────┘     │  violated)       │
                                      │                   └──────────────────┘
                                      │ invalidateQueries()
                                      ▼
                             ┌─────────────────────┐
                             │ UI auto-refreshes:   │
                             │ - Levels tab         │
                             │ - Alerts tab         │
                             │ - Analytics charts   │
                             └─────────────────────┘
```
