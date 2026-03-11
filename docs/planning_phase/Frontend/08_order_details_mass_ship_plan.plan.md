# Order Details & Mass Ship UI Plan

**Version:** PRE-ALPHA v0.6.x
**Created:** 2026-03-11
**Status:** Planning

---

## Overview

This plan covers two core pages in the Orders sidebar section:

1. **Order Details** (`/orders/details`) — the central order management hub: browse, search, filter, inspect, and edit orders
2. **Mass Ship** (`/orders/mass-ship`) — bulk fulfillment workflow: select ready orders, assign tracking, batch-update to "shipped"

Both pages consume the existing backend endpoints (`GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}`, `PATCH /orders/{id}/details/{detail_id}`) and the database views (`v_order_fulfillment`, `v_order_line_items`).

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| Backend order models | `models/orders.py` | Complete: Order, OrderDetail, Platform, Seller, PlatformRawImport, PlatformSKU, ListingComponent, CustomerPlatform, CancellationReason, OrderCancellation |
| Backend order ops models | `models/order_operations.py` | Complete: OrderReturn, OrderExchange, OrderModification, OrderPriceAdjustment + lookup tables |
| Backend order router | `routers/orders.py` | 5 endpoints: list (paginated), get, create, update order, update detail |
| Backend delivery router | `routers/delivery.py` | 8 endpoints: drivers CRUD, trips CRUD |
| Backend DB views | `models/views.py` | 7 order views: v_order_fulfillment, v_order_line_items, v_order_returns, v_order_exchanges, v_order_modifications, v_order_price_adjustments, v_order_operations_summary |
| Frontend order types | `api/base_types/orders.ts` | Minimal: ImportRequest, ImportError, ImportResult only |
| Frontend order API | `api/base/orders.ts` | Minimal: importOrders() only |
| Frontend order pages | — | **None exist yet** |
| Nav config | `components/layout/nav.config.tsx` | Routes defined: `/orders/details`, `/orders/mass-ship`, `/orders/cancellation`, `/orders/returns` |

### Backend Data Model Summary (relevant subset)

```
Order
├── order_id (PK)
├── store_id → Seller (shop account)
├── platform_id → Platform (Shopee/Lazada/TikTok)
├── platform_order_id (marketplace order number)
├── assigned_warehouse_id → Warehouse
├── recipient_name, phone_number
├── shipping_address, shipping_postcode, shipping_state, country
├── billing_address (JSONB)
├── platform_raw_data (JSONB)
├── order_status (pending | confirmed | processing | shipped | delivered | completed | cancelled)
├── cancellation_status (none | partial | full | return_pending)
├── order_date, created_at, updated_at
└── details[] → OrderDetail
    ├── detail_id (PK)
    ├── platform_sku_data (JSONB — raw marketplace SKU info)
    ├── resolved_item_id → Item (internal item after SKU translation)
    ├── quantity, paid_amount, shipping_fee, discount
    ├── courier_type, tracking_number, tracking_source
    ├── fulfillment_status (pending | picked | packed | shipped | delivered | cancelled | returned)
    ├── is_cancelled, cancelled_quantity, return_status, returned_quantity
    └── created_at, updated_at
```

### Backend Schemas (response shapes)

```
OrderListItem (lightweight, for tables):
  order_id, store_id, platform_id, platform_order_id,
  assigned_warehouse_id, recipient_name, order_status,
  cancellation_status, order_date, created_at

OrderRead (full, for detail view):
  ...all OrderListItem fields +
  phone_number, shipping_address, shipping_postcode, shipping_state,
  country, billing_address, platform_raw_data, raw_import_id,
  cancelled_at, updated_at, details[] → OrderDetailRead

OrderDetailRead:
  detail_id, order_id, platform_sku_data, resolved_item_id,
  paid_amount, shipping_fee, discount, courier_type,
  tracking_number, tracking_source, quantity,
  fulfillment_status, is_cancelled, cancelled_quantity,
  return_status, returned_quantity, created_at, updated_at
```

---

## Phase 1 — Order Details Page

### 1.1 Route & File Structure

```
frontend/src/pages/orders/
├── OrderDetailsPage.tsx          ← main list page (route: /orders/details)
├── OrderDetailsPage.css          ← styles
├── OrderViewDrawer.tsx           ← slide-out drawer for single order
├── OrderViewDrawer.css
├── OrderLineItemsTable.tsx       ← line items sub-table inside drawer
├── OrderStatusBadge.tsx          ← reusable status chip
├── FulfillmentStatusBadge.tsx    ← line-item fulfillment chip
├── OrderFilters.tsx              ← filter bar component
└── OrderFilters.css
```

### 1.2 OrderDetailsPage (List View)

**Layout:** Full-width page with filter bar + data table

#### Filter Bar (top, horizontal)
| Filter | Type | Mapped API Param |
|--------|------|------------------|
| Search | Text input (debounced 300ms) | `search` (ILIKE on platform_order_id, recipient_name) |
| Platform | Multi-select dropdown (Shopee/Lazada/TikTok/etc.) | `platform_id` |
| Store / Seller | Dropdown (filtered by selected platform) | `store_id` |
| Order Status | Multi-select chips | `order_status` |
| Date Range | Date-range picker (from/to) | `date_from`, `date_to` (need backend param — see §1.6) |
| Warehouse | Dropdown (from WarehouseContext or all) | `assigned_warehouse_id` (need backend param — see §1.6) |

#### Data Table Columns
| # | Column | Source Field | Width | Notes |
|---|--------|-------------|-------|-------|
| 1 | Checkbox | — | 40px | For bulk actions (links to Mass Ship) |
| 2 | Order # | `platform_order_id` | 160px | Clickable → opens drawer |
| 3 | Platform | `platform_id` | 90px | Platform icon/logo badge |
| 4 | Store | `store_id` | 120px | Seller store_name (needs join or lookup) |
| 5 | Recipient | `recipient_name` | 150px | Truncate with tooltip |
| 6 | Items | count of details[] | 60px | Badge: "3 items" |
| 7 | Total | sum of paid_amount | 100px | Formatted currency |
| 8 | Status | `order_status` | 110px | OrderStatusBadge |
| 9 | Date | `order_date` | 110px | Relative or formatted date |
| 10 | Actions | — | 60px | Kebab menu (View, Edit Status, Cancel) |

#### Table Features
- **Pagination:** Server-side, 20 rows/page default, page size selector (20/50/100)
- **Sorting:** Click column header → `sort_by` + `sort_dir` params (need backend — see §1.6)
- **Row click:** Opens OrderViewDrawer
- **Bulk select:** Checkbox column for mass operations → links to Mass Ship flow
- **Empty state:** Illustration + "No orders found" + suggestion to adjust filters
- **Loading:** Skeleton rows (8 rows) while fetching

#### Status Color Map
| Status | Color | Tailwind Class |
|--------|-------|---------------|
| pending | Amber | `bg-amber-100 text-amber-800` |
| confirmed | Blue | `bg-blue-100 text-blue-800` |
| processing | Indigo | `bg-indigo-100 text-indigo-800` |
| shipped | Violet | `bg-violet-100 text-violet-800` |
| delivered | Emerald | `bg-emerald-100 text-emerald-800` |
| completed | Green | `bg-green-100 text-green-800` |
| cancelled | Red | `bg-red-100 text-red-800` |

### 1.3 OrderViewDrawer (Single Order Detail)

**Trigger:** Click any order row or "View" from kebab menu
**Layout:** Right-side slide-out drawer (width: 680px), overlay on list page

#### Drawer Sections (top to bottom)

**A) Header Bar**
- Platform icon + Platform Order ID (large, bold)
- OrderStatusBadge (right side)
- Close (X) button
- "Edit" icon button → toggles inline editing on editable fields

**B) Order Summary Cards (2-column grid)**

| Card | Fields |
|------|--------|
| Customer | recipient_name, phone_number |
| Shipping | shipping_address, shipping_postcode, shipping_state, country |
| Order Info | order_date, store (seller name), warehouse (name), created_at |
| Financials | Total paid, Total shipping, Total discount, Net amount |

**C) Line Items Table (OrderLineItemsTable)**

| Column | Source | Notes |
|--------|--------|-------|
| # | row index | — |
| SKU / Item | platform_sku_data → display name; resolved_item_id → internal SKU | Two lines: platform name on top, internal code below |
| Qty | quantity | — |
| Amount | paid_amount | — |
| Shipping | shipping_fee | — |
| Discount | discount | — |
| Tracking | tracking_number | Chip with courier_type prefix |
| Fulfillment | fulfillment_status | FulfillmentStatusBadge |
| Actions | — | Kebab: Edit tracking, Update status |

**D) Operations Timeline (collapsed by default)**
- Accordion section showing:
  - Cancellations (if any)
  - Returns (if any)
  - Exchanges (if any)
  - Modifications (audit log)
  - Price Adjustments
- Each entry: timestamp + type badge + summary line
- Data from `v_order_operations_summary` view (needs new endpoint — see §1.6)

**E) Raw Platform Data (collapsed by default)**
- JSON viewer for `platform_raw_data` JSONB
- Read-only, collapsible, monospace font
- Useful for debugging / support

#### Inline Editing (when "Edit" toggled)
- Editable fields: `order_status`, `recipient_name`, `phone_number`, `shipping_address`, `shipping_postcode`, `shipping_state`, `assigned_warehouse_id`
- Save → `PATCH /orders/{order_id}`
- Line item editing: tracking_number, fulfillment_status → `PATCH /orders/{order_id}/details/{detail_id}`
- Cancel edits → revert to original values

### 1.4 Platform Badge Component

Small icon-based badge showing platform identity:
- Shopee → orange badge
- Lazada → blue/purple badge
- TikTok → dark/black badge
- Manual → gray badge
- Each shows platform logo (small icon) + abbreviated name

### 1.5 Frontend Types & API Functions Needed

**New types in `api/base_types/orders.ts`:**

```typescript
// Order list item (matches OrderListItem schema)
export interface OrderListItem {
  order_id: number;
  store_id: number;
  platform_id: number;
  platform_order_id: string;
  assigned_warehouse_id: number | null;
  recipient_name: string;
  order_status: string;
  cancellation_status: string;
  order_date: string;
  created_at: string;
}

// Full order detail (matches OrderRead schema)
export interface OrderDetail {
  order_id: number;
  store_id: number;
  platform_id: number;
  platform_order_id: string;
  assigned_warehouse_id: number | null;
  raw_import_id: number | null;
  phone_number: string | null;
  recipient_name: string;
  shipping_address: string;
  shipping_postcode: string;
  shipping_state: string;
  country: string;
  billing_address: Record<string, unknown> | null;
  platform_raw_data: Record<string, unknown> | null;
  order_status: string;
  cancellation_status: string;
  cancelled_at: string | null;
  order_date: string;
  created_at: string;
  updated_at: string | null;
  details: OrderLineItem[];
}

// Line item (matches OrderDetailRead schema)
export interface OrderLineItem {
  detail_id: number;
  order_id: number;
  platform_sku_data: Record<string, unknown> | null;
  resolved_item_id: number | null;
  paid_amount: number;
  shipping_fee: number;
  discount: number;
  courier_type: string | null;
  tracking_number: string | null;
  tracking_source: string | null;
  quantity: number;
  fulfillment_status: string;
  is_cancelled: boolean;
  cancelled_quantity: number;
  return_status: string | null;
  returned_quantity: number;
  created_at: string;
  updated_at: string | null;
}

// Query params for list endpoint
export interface OrderListParams {
  page?: number;
  page_size?: number;
  platform_id?: number;
  store_id?: number;
  order_status?: string;
  search?: string;
  // Future backend additions:
  date_from?: string;
  date_to?: string;
  assigned_warehouse_id?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

// Order update payload
export interface OrderUpdatePayload {
  assigned_warehouse_id?: number;
  phone_number?: string;
  recipient_name?: string;
  shipping_address?: string;
  shipping_postcode?: string;
  shipping_state?: string;
  country?: string;
  order_status?: string;
}

// Line item update payload
export interface OrderDetailUpdatePayload {
  tracking_number?: string;
  tracking_source?: string;
  courier_type?: string;
  fulfillment_status?: string;
  quantity?: number;
}
```

**New functions in `api/base/orders.ts`:**

```typescript
listOrders(params: OrderListParams): Promise<PaginatedResponse<OrderListItem>>
getOrder(orderId: number): Promise<OrderDetail>
updateOrder(orderId: number, payload: OrderUpdatePayload): Promise<OrderDetail>
updateOrderDetail(orderId: number, detailId: number, payload: OrderDetailUpdatePayload): Promise<OrderLineItem>
```

### 1.6 Backend Enhancements Needed

| Enhancement | Priority | Endpoint / Change |
|------------|----------|-------------------|
| Date range filter | High | `GET /orders` — add `date_from`, `date_to` query params, filter on `order_date` |
| Warehouse filter | High | `GET /orders` — add `assigned_warehouse_id` query param |
| Sort params | Medium | `GET /orders` — add `sort_by` (order_date, created_at, order_status), `sort_dir` (asc/desc) |
| Order operations summary | Medium | `GET /orders/{id}/operations` — query `v_order_operations_summary` view |
| Bulk status update | High | `PATCH /orders/bulk-status` — body: `{ order_ids: number[], order_status: string }` for Mass Ship |
| Bulk detail update | High | `PATCH /orders/bulk-details` — body: `{ updates: [{ detail_id, tracking_number, fulfillment_status }] }` |
| Platform/Seller names in list | Medium | Either: (a) JOIN in list query to include platform_name + store_name, or (b) frontend fetches lookup tables on mount |

---

## Phase 2 — Mass Ship Page

### 2.1 Route & File Structure

```
frontend/src/pages/orders/
├── MassShipPage.tsx              ← main mass ship page (route: /orders/mass-ship)
├── MassShipPage.css
├── MassShipSteps.tsx             ← step indicator component
├── ShipmentSelectionStep.tsx     ← Step 1: select orders
├── TrackingAssignmentStep.tsx    ← Step 2: assign tracking
├── ReviewConfirmStep.tsx         ← Step 3: review & confirm
└── MassShipSummary.tsx           ← post-submit result summary
```

### 2.2 Workflow Overview

The Mass Ship page follows a **3-step wizard** pattern:

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  1. SELECT   │───▶│  2. ASSIGN       │───▶│  3. REVIEW &    │
│  ORDERS      │    │  TRACKING        │    │  CONFIRM        │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

### 2.3 Step 1 — Select Orders (ShipmentSelectionStep)

**Purpose:** Pick which orders to ship in this batch

#### Selection Methods (tabs)

**Tab A: Filter & Select**
- Same filter bar as OrderDetailsPage (platform, store, status, warehouse, date range)
- Pre-filtered to `order_status = "processing"` and `fulfillment_status = "packed"` (ready to ship)
- Data table with checkboxes for manual selection
- "Select All (on this page)" / "Select All Matching" buttons
- Selected count badge: "23 orders selected"

**Tab B: Import from File**
- Upload CSV/Excel with columns: `platform_order_id`, `tracking_number`, `courier_type`
- SheetJS preview table (same pattern as items mass upload)
- Auto-matches `platform_order_id` to existing orders
- Validation: highlights unmatched order IDs in red, duplicate tracking in yellow
- "Match All" button → resolves and adds to selection

**Tab C: Scan / Quick Add**
- Single text input for barcode scanner or manual entry
- Type/scan platform_order_id → auto-adds to selection list
- Running list below input showing scanned orders
- Sound feedback (beep on success, error tone on not found)

#### Selected Orders Summary Bar (sticky bottom)
```
┌──────────────────────────────────────────────────────────────┐
│ 23 orders selected  │  Shopee: 12  Lazada: 8  TikTok: 3    │
│                     │  Est. items: 47                        │
│                     │                 [Clear All] [Next →]   │
└──────────────────────────────────────────────────────────────┘
```

### 2.4 Step 2 — Assign Tracking (TrackingAssignmentStep)

**Purpose:** Assign tracking numbers and courier info to each order's line items

#### Layout: Editable Table

| # | Order # | Platform | Recipient | Items | Courier Type | Tracking Number | Status |
|---|---------|----------|-----------|-------|-------------|-----------------|--------|
| 1 | SHP-12345 | Shopee | John | 2 | J&T Express | `[editable input]` | ✓ Valid |
| 2 | LZD-67890 | Lazada | Jane | 1 | Ninja Van | `[editable input]` | ⚠ Missing |
| 3 | TIK-11111 | TikTok | Ahmad | 3 | `[dropdown]` | `[editable input]` | ⚠ Missing |

#### Features
- **Pre-filled tracking:** If orders already have tracking_number from platform import, show them pre-filled
- **Bulk courier assignment:** Dropdown at top: "Set courier for all" → applies courier_type to all rows
- **Tracking validation:**
  - Non-empty check
  - Duplicate detection (warn if same tracking used twice)
  - Format hint based on courier (J&T = starts with "JP", Pos Laju = "ER/EN", etc.)
- **CSV paste:** Paste a column of tracking numbers → auto-fills rows in order
- **Row status indicators:**
  - Green check: tracking assigned and valid
  - Yellow warning: missing tracking or courier
  - Red X: validation error (duplicate, etc.)

#### Summary Bar
```
┌──────────────────────────────────────────────────────────────┐
│ 23 orders  │  ✓ 18 ready  │  ⚠ 5 missing tracking          │
│            │                     [← Back] [Next →]           │
└──────────────────────────────────────────────────────────────┘
```

- "Next" disabled until all orders have tracking assigned (or user explicitly skips with "Ship without tracking" toggle for manual/self-delivery orders)

### 2.5 Step 3 — Review & Confirm (ReviewConfirmStep)

**Purpose:** Final review before committing the bulk update

#### Review Summary Cards
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Total Orders    │  │  Total Items     │  │  Platforms       │
│       23         │  │       47         │  │  SHP: 12         │
│                  │  │                  │  │  LZD: 8          │
│                  │  │                  │  │  TIK: 3          │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  Couriers        │  │  Warehouses      │
│  J&T: 15         │  │  WH-KL: 20      │
│  Ninja: 5        │  │  WH-PG: 3       │
│  PosLaju: 3      │  │                  │
└─────────────────┘  └─────────────────┘
```

#### Collapsible Order List
- Grouped by platform
- Each row: Order #, Recipient, Tracking, Courier, Item count
- Expandable to show line items

#### Confirm Actions
- **Primary:** "Confirm & Ship All (23)" → calls bulk update endpoint
  - Updates `order_status` → "shipped"
  - Updates each detail's `fulfillment_status` → "shipped"
  - Updates `tracking_number` and `courier_type` per detail
- **Secondary:** "Save as Draft" → stores in localStorage for later
- **Tertiary:** "Export Manifest" → downloads CSV with all shipment details

#### Processing State
- Progress bar during API calls
- Per-order status: success ✓ / failed ✗
- On completion → MassShipSummary

### 2.6 MassShipSummary (Post-Submit)

**Layout:** Results page shown after bulk operation completes

```
┌──────────────────────────────────────────────────────┐
│              ✓ Mass Shipment Complete                  │
│                                                        │
│  Successfully shipped: 22 / 23                         │
│  Failed: 1                                            │
│                                                        │
│  ┌ Failed Orders ─────────────────────────────────┐   │
│  │ SHP-99999: "Order already cancelled"            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  [Download Report]  [Back to Orders]  [Ship More]      │
└──────────────────────────────────────────────────────┘
```

---

## Phase 3 — Shared Infrastructure

### 3.1 Platform Lookup Cache

Both pages need platform names/icons and seller store names. Approach:

```typescript
// api/contexts/PlatformContext.tsx
// Fetches GET /platforms and GET /sellers on mount
// Provides: platformMap (id → {name, icon}), sellerMap (id → {store_name, platform_id})
// Cached in context, refreshed on 5-minute interval or manual invalidate
```

### 3.2 Order Status State Machine

```
pending → confirmed → processing → shipped → delivered → completed
                  ↓                    ↓
              cancelled            cancelled (partial)
```

Frontend enforces valid transitions:
- From "pending": can go to "confirmed" or "cancelled"
- From "confirmed": can go to "processing" or "cancelled"
- From "processing": can go to "shipped" (via Mass Ship) or "cancelled"
- From "shipped": can go to "delivered"
- From "delivered": can go to "completed"

The status dropdown in edit mode only shows valid next states.

### 3.3 Fulfillment Status State Machine

```
pending → picked → packed → shipped → delivered
                               ↓
                           cancelled / returned
```

---

## Implementation Sequence

### Sprint 1: Foundation (Order Details List)
1. Create `api/base_types/orders.ts` — full type definitions
2. Create `api/base/orders.ts` — listOrders, getOrder, updateOrder, updateOrderDetail
3. Backend: add date_from, date_to, assigned_warehouse_id, sort_by, sort_dir params to `GET /orders`
4. Backend: add platform_name + store_name to `OrderListItem` response (or separate lookup endpoint)
5. Build `OrderDetailsPage.tsx` — filter bar + data table + pagination
6. Build `OrderStatusBadge.tsx` + `FulfillmentStatusBadge.tsx`
7. Build `OrderFilters.tsx`

### Sprint 2: Order Drawer
8. Build `OrderViewDrawer.tsx` — slide-out with all sections
9. Build `OrderLineItemsTable.tsx` — line items sub-table
10. Implement inline editing (order fields + line item fields)
11. Backend: `GET /orders/{id}/operations` endpoint for operations timeline
12. Build operations timeline section (collapsed accordion)
13. Build raw platform data JSON viewer

### Sprint 3: Mass Ship Wizard
14. Backend: `PATCH /orders/bulk-status` endpoint
15. Backend: `PATCH /orders/bulk-details` endpoint
16. Build `MassShipPage.tsx` — step wizard container
17. Build `ShipmentSelectionStep.tsx` — filter/select tab
18. Build CSV import tab (SheetJS integration)
19. Build `TrackingAssignmentStep.tsx` — editable tracking table
20. Build `ReviewConfirmStep.tsx` — summary + confirm
21. Build `MassShipSummary.tsx` — results page

### Sprint 4: Polish & Integration
22. Build scan/quick-add tab in selection step
23. Add "Export Manifest" CSV download
24. Add "Save as Draft" localStorage persistence
25. Cross-link: Order Details checkbox → "Ship Selected" button → Mass Ship page with pre-selected orders
26. Add keyboard shortcuts (Ctrl+Enter to confirm, Esc to close drawer)
27. Responsive adjustments for smaller screens

---

## Backend Endpoints Needed (Summary)

| Method | Path | Purpose | Priority |
|--------|------|---------|----------|
| GET | `/orders` | Enhanced: +date_from, +date_to, +warehouse_id, +sort_by, +sort_dir | High |
| GET | `/orders/{id}/operations` | Order operations summary (from view) | Medium |
| PATCH | `/orders/bulk-status` | Bulk update order_status for mass ship | High |
| PATCH | `/orders/bulk-details` | Bulk update tracking/fulfillment on details | High |
| GET | `/platforms` | Platform lookup (may already exist) | Medium |
| GET | `/sellers` | Seller lookup (may already exist) | Medium |

---

## Key Design Decisions

1. **Drawer vs. separate page for order detail:** Drawer chosen — keeps list context visible, reduces navigation, matches the pattern used in inventory movements
2. **3-step wizard for mass ship:** Explicit steps prevent errors — users must deliberately assign tracking before shipping; reduces accidental bulk status updates
3. **CSV import in mass ship:** Essential for operations that receive tracking numbers in bulk from couriers — paste or upload a file rather than manual entry
4. **Pre-filter to "processing/packed" in mass ship:** Only orders actually ready to ship appear by default — prevents shipping unconfirmed orders
5. **Status state machine enforcement:** Frontend prevents invalid transitions — no jumping from "pending" to "shipped" without going through "confirmed" → "processing"
6. **Platform lookup cache (context):** Avoids N+1 lookups in the order table — one fetch, cached, used everywhere

---

## Wireframe Sketches

### Order Details Page Layout
```
┌─────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  │  Order Details                              [+ New]   │
│            │───────────────────────────────────────────────────────│
│            │  🔍 Search...  │ Platform ▼ │ Store ▼ │ Status ▼ │   │
│            │  Date: [from] → [to]  │ Warehouse ▼ │  [Clear All]   │
│            │───────────────────────────────────────────────────────│
│            │  □  Order #      Platform  Store  Recipient  Items .. │
│            │  □  SHP-12345    🟠 Shopee  KL-01  John Doe   3   .. │
│            │  □  LZD-67890    🟣 Lazada  PG-02  Jane Lim   1   .. │
│            │  □  TIK-11111    ⬛ TikTok  KL-01  Ahmad B    2   .. │
│            │  ...                                                   │
│            │───────────────────────────────────────────────────────│
│            │  ◀ 1 2 3 ... 12 ▶     20 per page ▼                  │
│            │───────────────────────────────────────────────────────│
│            │  ☑ 3 selected         [Ship Selected →]              │
└─────────────────────────────────────────────────────────────────────┘
```

### Order View Drawer
```
┌──────────────────────────────────────────────────┐
│ 🟠 SHP-12345678              [Shipped] ✎    ✕   │
│──────────────────────────────────────────────────│
│ ┌──────────────┐  ┌──────────────┐               │
│ │ Customer      │  │ Shipping     │               │
│ │ John Doe      │  │ 123 Jln ABC  │               │
│ │ +60111234567  │  │ 50000 KL     │               │
│ └──────────────┘  └──────────────┘               │
│ ┌──────────────┐  ┌──────────────┐               │
│ │ Order Info    │  │ Financials   │               │
│ │ 2026-03-10    │  │ Paid: RM120  │               │
│ │ Store: KL-01  │  │ Ship: RM 8   │               │
│ │ WH: Main      │  │ Disc: -RM10  │               │
│ └──────────────┘  └──────────────┘               │
│──────────────────────────────────────────────────│
│ Line Items                                        │
│ # │ SKU        │ Qty │ Amount │ Track  │ Status   │
│ 1 │ WIDGET-A   │  2  │ RM60   │ JP123  │ Shipped  │
│ 2 │ GADGET-B   │  1  │ RM50   │ JP123  │ Shipped  │
│──────────────────────────────────────────────────│
│ ▸ Operations Timeline (2 events)                  │
│ ▸ Raw Platform Data                               │
└──────────────────────────────────────────────────┘
```

### Mass Ship Wizard
```
Step 1                    Step 2                    Step 3
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ ● Select     │─────────│ ● Tracking   │─────────│ ● Confirm    │
│ ○ Tracking   │         │ ○ Confirm    │         │              │
│ ○ Confirm    │         │              │         │  Summary     │
│              │         │  Editable    │         │  cards +     │
│  Filter +    │         │  tracking    │         │  grouped     │
│  table with  │         │  table with  │         │  order list  │
│  checkboxes  │         │  validation  │         │              │
│              │         │              │         │ [Confirm &   │
│  [Next →]    │         │  [Next →]    │         │  Ship All]   │
└──────────────┘         └──────────────┘         └──────────────┘
```

---

## Risk & Considerations

| Risk | Mitigation |
|------|-----------|
| Bulk update endpoint doesn't exist yet | Build in Sprint 3 before frontend; simple loop with transaction |
| Large order volumes (1000+) may slow list | Server-side pagination already implemented; add index on order_date |
| Tracking number validation varies by courier | Start with non-empty validation; add courier-specific regex later |
| Order status conflicts in concurrent usage | Use `updated_at` optimistic locking — PATCH rejects if stale |
| Platform/seller names missing from list response | Implement lookup cache (PlatformContext) as fallback; enhance backend response as preferred path |
