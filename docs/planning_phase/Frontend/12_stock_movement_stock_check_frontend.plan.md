# Frontend Plan: Stock Movement Enhancement & Stock Check UI

**Version:** PRE-ALPHA v0.6.x
**Created:** 2026-03-14
**Status:** Planning
**Related Backend Plan:** `docs/planning_phase/Backend/11_stock_movement_stock_check.plan.md`

---

## 1. Overview

This plan covers the frontend implementation for two features:

- **Feature A** — Multi-item Record Movement Drawer (replaces current single-item modal)
- **Feature B** — Stock Check (Cycle Count) pages — list, create, count, review, reconcile

Both features follow existing UI patterns: Tailwind CSS v4 utilities, `DataTable` component, `useWarehouse()` context, `form-input` class, modal overlay pattern, and the `pages/<domain>/` file organisation rule.

---

## 2. Feature A: Record Movement Drawer

### 2A.1 Why a Drawer (Not a Modal)

The current modal (`InventoryMovementsPage.tsx` lines 249-403) works for single-item entry but becomes cramped with multiple items. A right-side drawer:
- Gives more vertical space for the item grid
- Lets staff reference the movement history table in the background
- Feels lighter than a full-page form

### 2A.2 New Components

All new files go in `frontend/src/pages/warehouse/` per the file organisation rule (page-specific components stay with their page).

#### `RecordMovementDrawer.tsx`

**Props:**
```typescript
interface RecordMovementDrawerProps {
  open: boolean;
  onClose: () => void;
  warehouseId: number;
  onSuccess: () => void;  // Refresh movement list after submit
}
```

**Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│  Background (movement history table, dimmed)                 │
│                          ┌──────────────────────────────────┐│
│                          │  Record Movement           [✕]  ││
│                          │                                  ││
│                          │  Movement Type  [Receipt ▾]      ││
│                          │  Reference #    [PO-2026-001  ]  ││
│                          │                                  ││
│                          │  Destination    [A01-DRY-A01 ▾]  ││
│                          │                                  ││
│                          │  ┌────────────────────────────┐  ││
│                          │  │ Item     │ Avail │ Qty │ ✕ │  ││
│                          │  ├──────────┼───────┼─────┼───┤  ││
│                          │  │ [search] │  42   │[10] │ ✕ │  ││
│                          │  │ [search] │  18   │[ 5] │ ✕ │  ││
│                          │  ├──────────┴───────┴─────┴───┤  ││
│                          │  │       [+ Add Item]         │  ││
│                          │  └────────────────────────────┘  ││
│                          │                                  ││
│                          │  Notes  [Optional notes...    ]  ││
│                          │                                  ││
│                          │  [Cancel]  [Submit Movement]     ││
│                          └──────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

**Styling:**
- Overlay: `fixed inset-0 z-50 bg-black/40`
- Panel: `fixed inset-y-0 right-0 w-[520px] bg-surface shadow-card` with slide-in transition
- Header: `flex items-center justify-between px-6 py-4 border-b border-divider`
- Body: `px-6 py-5 space-y-4 overflow-y-auto` (scrollable for many items)
- Footer: `flex items-center justify-end gap-3 px-6 py-4 border-t border-divider`

**Dynamic behavior based on movement type:**

| Movement Type | Source Field | Destination Field | Direction |
|--------------|-------------|-------------------|-----------|
| Receipt | Hidden | Shown (required) | All inbound |
| Shipment | Shown (required) | Hidden | All outbound |
| Transfer | Shown (required) | Shown (required) | Out from source, In to dest |
| Adjustment | Shown (required) | Hidden | Based on correction |
| Return | Hidden | Shown (required) | All inbound |

**State management:**
```typescript
// Local state (no external state library needed)
const [movementTypeId, setMovementTypeId] = useState<number | ''>('');
const [sourceLocationId, setSourceLocationId] = useState<number | ''>('');
const [destLocationId, setDestLocationId] = useState<number | ''>('');
const [items, setItems] = useState<MovementItemEntry[]>([emptyItem()]);
const [referenceNumber, setReferenceNumber] = useState('');
const [notes, setNotes] = useState('');
const [saving, setSaving] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**Validation before submit:**
- Movement type selected
- Required location(s) filled based on type
- At least 1 item row with item selected and quantity > 0
- For outbound: quantity <= available stock (client-side check)
- No duplicate items in the grid

**Submit payload → `POST /warehouse/movements/v2`:**
```typescript
const payload: MultiItemMovementCreate = {
  warehouse_id: warehouseId,
  movement_type_id: Number(movementTypeId),
  source_location_id: sourceLocationId ? Number(sourceLocationId) : undefined,
  destination_location_id: destLocationId ? Number(destLocationId) : undefined,
  items: items.map(i => ({ item_id: i.item_id!, quantity: i.quantity })),
  reference_number: referenceNumber.trim() || undefined,
  notes: notes.trim() || undefined,
};
```

#### `MovementItemGrid.tsx`

**Props:**
```typescript
interface MovementItemGridProps {
  items: MovementItemEntry[];
  onUpdate: (index: number, patch: Partial<MovementItemEntry>) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  warehouseId: number;
  sourceLocationId?: number;  // For fetching available stock
}
```

Renders a table header + `MovementItemRow` for each entry + "Add Item" button.

#### `MovementItemRow.tsx`

**Props:**
```typescript
interface MovementItemRowProps {
  index: number;
  entry: MovementItemEntry;
  onUpdate: (patch: Partial<MovementItemEntry>) => void;
  onRemove: () => void;
  warehouseId: number;
  sourceLocationId?: number;
  canRemove: boolean;  // false if only 1 row (minimum 1)
}
```

**Item autocomplete pattern** (reuse existing pattern from `InventoryMovementsPage.tsx` lines 94-103):
- Debounced search input (300ms)
- When source location is set, search against `listInventoryLevels(warehouseId, { location_id: sourceLocationId, search })` to show only items at that location
- When no source location (e.g., Receipt), search against `listItems({ search })`
- Dropdown shows item name + SKU + available quantity
- On select: populate `item_id`, `item_name`, `master_sku`, `available_stock`

**Available stock display:**
- Read-only badge next to quantity input showing "Avail: 42"
- For outbound: if quantity > available, show red inline error

### 2A.3 Modified Files

#### `InventoryMovementsPage.tsx`

Changes:
1. Remove modal state variables (`showModal`, `formTypeId`, `formItemId`, etc.) — lines 50-61
2. Remove modal JSX — lines 249-403
3. Add drawer state: `const [showDrawer, setShowDrawer] = useState(false)`
4. Replace "Record Movement" button `onClick` from `openRecord` to `() => setShowDrawer(true)`
5. Add drawer component:
   ```tsx
   <RecordMovementDrawer
     open={showDrawer}
     onClose={() => setShowDrawer(false)}
     warehouseId={warehouseId!}
     onSuccess={() => { setShowDrawer(false); fetchMovements(); }}
   />
   ```

### 2A.4 Types & API

**`frontend/src/api/base_types/warehouse.ts` — additions:**
```typescript
export interface MovementLineItem {
  item_id: number;
  quantity: number;
}

export interface MultiItemMovementCreate {
  warehouse_id: number;
  movement_type_id: number;
  source_location_id?: number;
  destination_location_id?: number;
  items: MovementLineItem[];
  reference_number?: string;
  notes?: string;
}

// Internal form state (not sent to API)
export interface MovementItemEntry {
  item_id: number | null;
  item_name: string;
  master_sku: string;
  quantity: number;
  available_stock: number;  // Read-only, fetched on item select
}
```

**`frontend/src/api/base/warehouse.ts` — additions:**
```typescript
export async function createMovementV2(data: MultiItemMovementCreate) {
  const res = await client.post('/warehouse/movements/v2', data);
  return res.data;
}

// Update existing listInventoryLevels to accept location_id param:
export async function listInventoryLevels(warehouseId: number, params?: {
  page?: number;
  page_size?: number;
  search?: string;
  stock_status?: string;
  location_id?: number;  // <-- NEW
}) { ... }
```

---

## 3. Feature B: Stock Check (Cycle Count) UI

### 3B.1 File Structure

```
frontend/src/pages/warehouse/stock_check/
├── StockCheckListPage.tsx         — List all checks with filters
├── StockCheckCreateModal.tsx      — Create new check with scope selection
├── StockCheckDetailPage.tsx       — Main detail view (content varies by status)
├── CountingGrid.tsx               — Counting interface with inline inputs
├── VarianceReviewPanel.tsx        — Review + reconcile variances
└── StockCheckStatusBadge.tsx      — Status badge component
```

### 3B.2 Routing

**`App.tsx` — update routes:**
```tsx
// Replace PlaceholderPage with real pages
<Route path="/inventory/stock-check" element={<StockCheckListPage />} />
<Route path="/inventory/stock-check/:id" element={<StockCheckDetailPage />} />
```

**`nav.config.tsx`** — "Stock Check" entry already exists (pointing to `/inventory/stock-check`). No change needed.

### 3B.3 StockCheckListPage.tsx

**Route:** `/inventory/stock-check`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Stock Check                              [+ New Stock Check]   │
├─────────────────────────────────────────────────────────────────┤
│  [All] [Draft] [In Progress] [Pending Review] [Completed]       │
├─────────────────────────────────────────────────────────────────┤
│  Title          │ Status     │ Progress  │ Variances │ Created  │
│  ────────────── │ ────────── │ ───────── │ ───────── │ ──────── │
│  Section A Mar  │ 🔵 Active  │ 23/47     │    5      │ Mar 14   │
│  Full Count Feb │ 🟢 Done    │ 120/120   │   12      │ Feb 28   │
│  Spot Check B3  │ ⚪ Draft   │ —         │    —      │ Mar 13   │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Warehouse-scoped via `useWarehouse()` — shows "Select a warehouse" empty state if none selected
- Filter tabs: All / Draft / In Progress / Pending Review / Completed / Cancelled
- DataTable with columns: Title, Status (badge), Progress (counted/total or "—"), Variances (count), Created (date), Actions (view/cancel kebab)
- Click row → navigate to `/inventory/stock-check/:id`
- "New Stock Check" button → opens `StockCheckCreateModal`
- Pagination with page size selector

**State:**
```typescript
const { selectedWarehouseId } = useWarehouse();
const [checks, setChecks] = useState<StockCheckRead[]>([]);
const [total, setTotal] = useState(0);
const [page, setPage] = useState(1);
const [pageSize, setPageSize] = useState(20);
const [statusFilter, setStatusFilter] = useState<string>('all');
const [showCreateModal, setShowCreateModal] = useState(false);
```

### 3B.4 StockCheckCreateModal.tsx

**Modal for creating a new stock check.**

```
┌──────────────────────────────────────────────┐
│  New Stock Check                       [✕]   │
├──────────────────────────────────────────────┤
│                                              │
│  Title *                                     │
│  [Section A Monthly Count - March 2026   ]   │
│                                              │
│  Notes                                       │
│  [Optional notes about this check...     ]   │
│                                              │
│  Scope                                       │
│  ┌────────────────────────────────────────┐  │
│  │ Section  [A        ▾]                  │  │
│  │ Zone     [All zones ▾]                 │  │
│  │ Aisle    [All aisles▾]                 │  │
│  │ Bay      [All bays  ▾]                 │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Scope preview: "Section A, all zones"       │
│  Estimated locations: ~24                    │
│                                              │
│              [Cancel]  [Create Check]        │
└──────────────────────────────────────────────┘
```

**Scope selection:**
- Hierarchical dropdowns populated from location data: Section → Zone → Aisle → Bay
- Each level defaults to "All" (no filter at that level)
- When Section is selected, Zone dropdown populates with zones in that section
- When Zone is selected, Aisle dropdown populates with aisles in that zone
- Scope preview text below shows human-readable description
- Optional: show estimated location count by querying location list with filters

**Data flow:**
1. User fills in Title (required), Notes (optional), selects scope
2. Click "Create Check" → `POST /stock-check/` with `scope_filters` JSONB
3. On success → navigate to `/inventory/stock-check/:id` (the new check's detail page)

**Fetch location hierarchy for dropdowns:**
```typescript
// Reuse existing listLocations API to get available values
const locations = await listLocations(warehouseId, { page_size: 9999 });
const sections = [...new Set(locations.items.map(l => l.warehouse_section).filter(Boolean))];
// When section selected, filter zones from same data
const zones = [...new Set(locations.items
  .filter(l => l.warehouse_section === selectedSection)
  .map(l => l.zone)
  .filter(Boolean))];
```

### 3B.5 StockCheckDetailPage.tsx

**Route:** `/inventory/stock-check/:id`

This page renders different content based on the check's `status`. It's the main working interface for warehouse staff.

**Common header (all statuses):**
```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Stock Checks                                        │
│                                                                 │
│  Section A Monthly Count - March 2026          🔵 In Progress   │
│  Scope: Section A, all zones | 47 items at 12 locations         │
│  Started: Mar 14, 2026 10:30 AM                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Status-specific content below]                                │
└─────────────────────────────────────────────────────────────────┘
```

**Status-specific content:**

#### Status = DRAFT

```
┌─────────────────────────────────────────────────────────────────┐
│  This stock check hasn't started yet. When you start, the       │
│  system will snapshot current stock quantities and generate      │
│  counting lines for all items at scoped locations.               │
│                                                                 │
│  Scope: Section A, all zones                                    │
│                                                                 │
│              [Cancel Check]  [Start Counting]                   │
└─────────────────────────────────────────────────────────────────┘
```

- "Start Counting" → `PATCH /stock-check/{id}/start` → refreshes page (now IN_PROGRESS)
- "Cancel Check" → confirm dialog → `PATCH /stock-check/{id}/cancel`

#### Status = IN_PROGRESS

```
┌─────────────────────────────────────────────────────────────────┐
│  Progress: ████████████░░░░░░░░  23 of 47 lines counted        │
│                                                                 │
│  [All] [Uncounted (24)] [Counted (23)] [With Variance (5)]     │
│  Search: [Search by item name or SKU...              ]          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📍 A01-DRY-A01-B1                                              │
│  ┌──────────────┬──────────┬────────┬─────────┬─────────┬──────┐│
│  │ Item         │ SKU      │ System │ Count   │Variance │Notes ││
│  ├──────────────┼──────────┼────────┼─────────┼─────────┼──────┤│
│  │ iPhone 15    │ IPH15-BK │   42   │ [ 40  ] │   -2    │ [📝] ││
│  │ MacBook Air  │ MBA-M3   │   18   │ [ 18  ] │    0    │      ││
│  │ AirPods Pro  │ APP2-WH  │    7   │ [     ] │    —    │      ││
│  └──────────────┴──────────┴────────┴─────────┴─────────┴──────┘│
│                                                                 │
│  📍 A01-DRY-A01-B2                                              │
│  ┌──────────────┬──────────┬────────┬─────────┬─────────┬──────┐│
│  │ Widget X     │ WGT-X01  │   25   │ [ 27  ] │   +2    │ [📝] ││
│  └──────────────┴──────────┴────────┴─────────┴─────────┴──────┘│
│                                                                 │
│                           [Cancel Check]  [Submit for Review]   │
└─────────────────────────────────────────────────────────────────┘
```

This renders the `CountingGrid` component (see below).

#### Status = PENDING_REVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│  Variance Summary                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Total lines: 47  │ With variance: 5  │ Net adjustment: -3│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Lines with Variance                                            │
│  ┌────┬──────────────┬──────────┬────────┬───────┬─────────┬──┐│
│  │ ☑  │ Item         │ Location │ System │ Count │Variance │  ││
│  ├────┼──────────────┼──────────┼────────┼───────┼─────────┼──┤│
│  │ [✓]│ iPhone 15    │ A01-B1   │   42   │  40   │   -2    │  ││
│  │ [✓]│ Widget X     │ A01-B2   │   25   │  27   │   +2    │  ││
│  │ [ ]│ Galaxy S24   │ A01-B3   │   10   │   8   │   -2    │  ││
│  │ [✓]│ Pixel 9      │ A02-B1   │   15   │  16   │   +1    │  ││
│  └────┴──────────────┴──────────┴────────┴───────┴─────────┴──┘│
│                                                                 │
│  Accepted: 3 variances (net: -1)                                │
│  Rejected: 1 variance (Galaxy S24 at A01-B3)                   │
│                                                                 │
│            [Cancel Check]  [Reconcile & Complete]               │
└─────────────────────────────────────────────────────────────────┘
```

This renders the `VarianceReviewPanel` component (see below).

#### Status = COMPLETED

```
┌─────────────────────────────────────────────────────────────────┐
│  Completed: Mar 14, 2026 3:45 PM                                │
│  Reconciliation Movement: SC-42 (Cycle Count)                   │
│                                                                 │
│  Summary                                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Total lines: 47  │ Variances: 5  │ Adjusted: 3 │ Net: -1│  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  All Lines (read-only)                                          │
│  ┌──────────────┬──────────┬────────┬───────┬─────────┬───────┐│
│  │ Item         │ Location │ System │ Count │Variance │ Status││
│  ├──────────────┼──────────┼────────┼───────┼─────────┼───────┤│
│  │ iPhone 15    │ A01-B1   │   42   │  40   │   -2    │ Adj'd ││
│  │ MacBook Air  │ A01-B1   │   18   │  18   │    0    │ Match ││
│  │ Galaxy S24   │ A01-B3   │   10   │   8   │   -2    │ Skip'd││
│  └──────────────┴──────────┴────────┴───────┴─────────┴───────┘│
└─────────────────────────────────────────────────────────────────┘
```

Read-only view with all lines, marking which variances were adjusted vs skipped.

#### Status = CANCELLED

Simple read-only view with "This stock check was cancelled" message and the check metadata.

### 3B.6 CountingGrid.tsx

**The most critical UX component.** Optimized for warehouse staff speed.

**Props:**
```typescript
interface CountingGridProps {
  lines: StockCheckLineRead[];
  onCountSubmit: (counts: StockCheckLineCount[]) => Promise<void>;
  filter: 'all' | 'uncounted' | 'counted' | 'variance';
  searchQuery: string;
}
```

**Key UX decisions:**

1. **Location grouping:** Lines grouped by `location_code`. Each group has a collapsible header showing the location prominently (like the existing LocationManagementSection accordion pattern).

2. **Inline editable count inputs:**
   - Each line's "Count" column is a `<input type="number" min="0">` with `form-input` class
   - **Tab navigation:** Pressing Tab moves to the next count input (standard browser behavior, no custom handler needed)
   - Inputs show placeholder "—" when empty (not yet counted)

3. **Auto-save on blur:**
   - When user tabs away from or clicks out of a count input, the value is queued for save
   - Debounced batch save (500ms): collects all changed inputs since last save and sends one `POST /{id}/count` request
   - Small checkmark icon appears briefly next to saved inputs
   - If save fails, show inline error on the affected input

4. **Variance display:**
   - Computed client-side: `counted - system`
   - Color coding:
     - Variance = 0: `text-success-text` (green)
     - Variance < 0 (shortage): `text-error-text` (red), prefixed with "-"
     - Variance > 0 (surplus): `text-info-text` (blue), prefixed with "+"
     - Not yet counted: `text-text-secondary` showing "—"
   - Row background tint for non-zero variance: `bg-warning-bg/30`

5. **Filter buttons:** "All", "Uncounted (N)", "Counted (N)", "With Variance (N)" — client-side filter on the fetched lines

6. **Search:** Debounced (400ms), filters by item_name or master_sku (client-side)

7. **Notes:** Small pencil icon per row. On click → inline textarea expands below the row. Saved with the next count batch.

8. **Progress bar:** At the top of the grid. Uses Tailwind: `bg-primary` for filled, `bg-background` for empty. Shows "X of Y lines counted".

### 3B.7 VarianceReviewPanel.tsx

**Props:**
```typescript
interface VarianceReviewPanelProps {
  lines: StockCheckLineRead[];  // Only lines with variance != 0
  onReconcile: (acceptances: LineAcceptance[]) => Promise<void>;
  onCancel: () => void;
}
```

**Features:**
- Shows ONLY lines where `variance != 0`
- Each line has a checkbox (default: checked = accepted)
- Summary stats update live: "Accepted: N variances (net: X)"
- "Reconcile & Complete" button → sends `POST /{id}/reconcile` with acceptances
- Confirm dialog before reconciliation: "This will create adjustment transactions for N items. Stock levels will be updated. This cannot be undone."

### 3B.8 StockCheckStatusBadge.tsx

```typescript
const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  draft:          { label: 'Draft',          classes: 'bg-background text-text-secondary' },
  in_progress:    { label: 'In Progress',    classes: 'bg-info-bg text-info-text' },
  pending_review: { label: 'Pending Review', classes: 'bg-warning-bg text-warning-text' },
  completed:      { label: 'Completed',      classes: 'bg-success-bg text-success-text' },
  cancelled:      { label: 'Cancelled',      classes: 'bg-background text-text-secondary' },
};
```

### 3B.9 API Layer

**New file: `frontend/src/api/base/stockCheck.ts`**

```typescript
import client from '../client';
import type {
  StockCheckRead,
  StockCheckDetailRead,
  StockCheckCreate,
  StockCheckBatchCount,
  StockCheckReconcileRequest,
} from '../base_types/stockCheck';
import type { PaginatedResponse } from '../base_types/common';

export async function listStockChecks(
  warehouseId: number,
  params?: { status?: string; page?: number; page_size?: number }
): Promise<PaginatedResponse<StockCheckRead>> {
  const res = await client.get('/stock-check', {
    params: { warehouse_id: warehouseId, ...params },
  });
  return res.data;
}

export async function createStockCheck(data: StockCheckCreate): Promise<StockCheckRead> {
  const res = await client.post('/stock-check', data);
  return res.data;
}

export async function getStockCheck(id: number): Promise<StockCheckDetailRead> {
  const res = await client.get(`/stock-check/${id}`);
  return res.data;
}

export async function startStockCheck(id: number): Promise<StockCheckDetailRead> {
  const res = await client.patch(`/stock-check/${id}/start`);
  return res.data;
}

export async function submitCounts(
  id: number,
  data: StockCheckBatchCount
): Promise<StockCheckDetailRead> {
  const res = await client.post(`/stock-check/${id}/count`, data);
  return res.data;
}

export async function reviewStockCheck(id: number): Promise<StockCheckDetailRead> {
  const res = await client.patch(`/stock-check/${id}/review`);
  return res.data;
}

export async function reconcileStockCheck(
  id: number,
  data?: StockCheckReconcileRequest
): Promise<StockCheckRead> {
  const res = await client.post(`/stock-check/${id}/reconcile`, data ?? {});
  return res.data;
}

export async function cancelStockCheck(id: number): Promise<StockCheckRead> {
  const res = await client.patch(`/stock-check/${id}/cancel`);
  return res.data;
}
```

**New file: `frontend/src/api/base_types/stockCheck.ts`**

```typescript
export type StockCheckStatus =
  | 'draft'
  | 'in_progress'
  | 'pending_review'
  | 'completed'
  | 'cancelled';

export interface StockCheckCreate {
  warehouse_id: number;
  title: string;
  notes?: string;
  scope_filters?: Record<string, string>;
}

export interface StockCheckRead {
  id: number;
  warehouse_id: number;
  title: string;
  notes: string | null;
  status: StockCheckStatus;
  scope_filters: Record<string, string> | null;
  total_lines: number;
  lines_counted: number;
  lines_with_variance: number;
  adjustment_movement_id: number | null;
  created_by: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface StockCheckLineRead {
  id: number;
  item_id: number;
  item_name: string;
  master_sku: string;
  location_id: number;
  location_code: string;
  system_quantity: number;
  counted_quantity: number | null;
  variance: number | null;
  notes: string | null;
  is_accepted: boolean;
  counted_at: string | null;
}

export interface StockCheckDetailRead extends StockCheckRead {
  lines: StockCheckLineRead[];
}

export interface StockCheckLineCount {
  line_id: number;
  counted_quantity: number;
  notes?: string;
}

export interface StockCheckBatchCount {
  counts: StockCheckLineCount[];
}

export interface LineAcceptance {
  line_id: number;
  is_accepted: boolean;
}

export interface StockCheckReconcileRequest {
  line_acceptances?: LineAcceptance[];
}
```

---

## 4. Files Summary

### New Files

| File | Purpose |
|------|---------|
| `pages/warehouse/RecordMovementDrawer.tsx` | Multi-item movement drawer |
| `pages/warehouse/MovementItemGrid.tsx` | Dynamic item rows table |
| `pages/warehouse/MovementItemRow.tsx` | Item autocomplete + qty input row |
| `pages/warehouse/stock_check/StockCheckListPage.tsx` | List all stock checks |
| `pages/warehouse/stock_check/StockCheckCreateModal.tsx` | Create new check with scope |
| `pages/warehouse/stock_check/StockCheckDetailPage.tsx` | Detail view (varies by status) |
| `pages/warehouse/stock_check/CountingGrid.tsx` | Counting interface with inline inputs |
| `pages/warehouse/stock_check/VarianceReviewPanel.tsx` | Variance accept/reject + reconcile |
| `pages/warehouse/stock_check/StockCheckStatusBadge.tsx` | Status badge component |
| `api/base/stockCheck.ts` | Stock check API functions |
| `api/base_types/stockCheck.ts` | Stock check TypeScript types |

### Modified Files

| File | Change |
|------|--------|
| `pages/warehouse/InventoryMovementsPage.tsx` | Remove modal (lines 50-61, 249-403), add drawer |
| `api/base/warehouse.ts` | Add `createMovementV2()`, add `location_id` to `listInventoryLevels()` |
| `api/base_types/warehouse.ts` | Add `MovementLineItem`, `MultiItemMovementCreate`, `MovementItemEntry` |
| `App.tsx` | Update `/inventory/stock-check` route, add `/:id` route |

### No Change Needed

| File | Reason |
|------|--------|
| `nav.config.tsx` | "Stock Check" entry already exists at `/inventory/stock-check` |
| `WarehouseContext.tsx` | Already provides `selectedWarehouseId` |
| `StockStatusBadge.tsx` | Reused as-is for inventory level display |
| `DataTable.tsx` | Reused for list pages |

---

## 5. Documentation Updates

After implementation, update:
- `docs/official_documentation/web-api.md` — Add `/movements/v2` and `/stock-check/` endpoints
- `docs/official_documentation/frontend-development-progress.md` — Add Stock Movement drawer + Stock Check pages
- `docs/official_documentation/version_update.md` — Version entries for each step
- `docs/official_documentation/database_structure.md` — Add `stock_checks` and `stock_check_lines` tables

---

## 6. Implementation Sequence

| Step | Task | Depends On |
|------|------|-----------|
| **3** | RecordMovementDrawer + MovementItemGrid + MovementItemRow | Backend Step 2 |
| **4** | Update InventoryMovementsPage (swap modal → drawer) | Step 3 |
| **7** | StockCheckListPage + StockCheckCreateModal | Backend Step 6 |
| **8** | StockCheckDetailPage + CountingGrid + VarianceReviewPanel | Step 7 |
| **9** | Route updates + documentation | Step 8 |

(Step numbers align with the combined backend+frontend implementation order in the main plan)
