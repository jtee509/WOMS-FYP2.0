# Frontend Plan: Orders, Mass Ship, Cancellation, Returns & Exchanges

**Version:** PRE-ALPHA v0.6.x
**Created:** 2026-03-14
**Status:** Planning
**Related Backend Models:** `backend/app/models/orders.py`, `backend/app/models/order_operations.py`

---

## 1. Overview

This plan covers the full Orders frontend module, building on the existing `OrderDetailsPage`, `MassShipPage`, and `OrderViewDrawer`. The scope includes:

| Feature | Route | Current State | Priority |
|---------|-------|---------------|----------|
| **A** — Order List (enhance) | `/orders/details` | Built — needs minor polish | Low |
| **B** — Mass Ship (enhance) | `/orders/mass-ship` | Built — needs bulk-ship endpoint | Medium |
| **C** — Order Cancellation | `/orders/cancellation` | Placeholder | High |
| **D** — Returns & Exchanges | `/orders/returns` | Placeholder | High |

All features follow existing patterns: Tailwind CSS v4 utilities, `DataTable` component, drawer/modal overlays, `form-input` class, `pages/orders/` file organisation.

---

## 2. Backend Gaps (Must Be Built First)

The backend **models** exist but **schemas + router endpoints** are missing for operations. These must be created before the frontend can integrate.

### 2.1 New Schemas Required (`backend/app/schemas/orders.py`)

```
CancellationReasonRead     — reason_id, reason_code, reason_name, reason_type, requires_inspection, auto_restock
ReturnReasonRead           — reason_id, reason_code, reason_name, reason_type, requires_inspection
ExchangeReasonRead         — reason_id, reason_code, reason_name, requires_return

OrderCancellationCreate    — order_id, order_detail_id?, reason_id, cancellation_type, cancelled_quantity?, notes?
OrderCancellationRead      — all fields + reason_name (enriched)
OrderCancellationUpdate    — restock_status?, restocked_quantity?, notes?

OrderReturnCreate          — order_id, order_detail_id, return_type, return_reason_id, returned_quantity, notes?
OrderReturnRead            — all fields + reason_name, item_name (enriched)
OrderReturnUpdate          — return_status?, inspection_status?, inspection_notes?, restock_decision?, restocked_quantity?

OrderExchangeCreate        — original_order_id, original_detail_id, exchange_type, exchange_reason_id, exchanged_item_id?, exchanged_quantity, notes?
OrderExchangeRead          — all fields + reason_name, original_item_name, new_item_name (enriched)
OrderExchangeUpdate        — exchange_status?, new_order_id?, new_detail_id?, adjustment_status?, notes?

BulkCancelRequest          — { cancellations: [{ order_id, reason_id, cancellation_type, detail_ids?: number[] }] }
BulkCancelResponse         — { total, succeeded, failed, results[] }
```

### 2.2 New Endpoints Required (`backend/app/routers/orders.py`)

| Method | Path | Purpose |
|--------|------|---------|
| **Reason Lookups** | | |
| GET | `/api/v1/orders/cancellation-reasons` | List active cancellation reasons |
| GET | `/api/v1/orders/return-reasons` | List active return reasons |
| GET | `/api/v1/orders/exchange-reasons` | List active exchange reasons |
| **Cancellations** | | |
| GET | `/api/v1/orders/cancellations` | List cancellations (paginated, filterable) |
| POST | `/api/v1/orders/{order_id}/cancel` | Cancel full order or partial items |
| POST | `/api/v1/orders/bulk-cancel` | Bulk cancel multiple orders |
| PATCH | `/api/v1/orders/cancellations/{id}` | Update restock status / notes |
| **Returns** | | |
| GET | `/api/v1/orders/returns` | List returns (paginated, filterable) |
| POST | `/api/v1/orders/{order_id}/return` | Initiate return for line item(s) |
| PATCH | `/api/v1/orders/returns/{id}` | Update return status / inspection |
| **Exchanges** | | |
| GET | `/api/v1/orders/exchanges` | List exchanges (paginated, filterable) |
| POST | `/api/v1/orders/{order_id}/exchange` | Initiate exchange |
| PATCH | `/api/v1/orders/exchanges/{id}` | Update exchange status |
| **Bulk Ship** | | |
| POST | `/api/v1/orders/bulk-ship` | Process bulk shipments (already in frontend types) |

### 2.3 Seed Data Required

Cancellation, return, and exchange reason tables need seed data in `backend/app/models/seed.py`:

**Cancellation Reasons:**
- `CUST_REQUEST` — Customer requested (customer)
- `OUT_OF_STOCK` — Item out of stock (seller)
- `PLATFORM_CANCEL` — Platform-initiated cancellation (platform)
- `DELIVERY_FAIL` — Delivery failed / RTS (delivery)
- `FRAUD_SUSPECT` — Suspected fraudulent order (system)
- `DUPLICATE_ORDER` — Duplicate order detected (system)
- `PRICING_ERROR` — Pricing error (seller)

**Return Reasons:**
- `WRONG_ITEM` — Wrong item received (quality)
- `DAMAGED` — Item damaged in transit (delivery)
- `DEFECTIVE` — Defective product (quality)
- `NOT_AS_DESC` — Not as described (customer)
- `CHANGE_MIND` — Customer changed mind (customer)
- `DELIVERY_FAIL` — Delivery failed / unclaimed (delivery)
- `PLATFORM_RETURN` — Platform-initiated return (platform)

**Exchange Reasons:**
- `WRONG_SIZE` — Wrong size/variant
- `WRONG_ITEM` — Wrong item sent
- `DEFECTIVE` — Defective — replace same item
- `UPGRADE` — Customer upgrade request
- `DOWNGRADE` — Customer downgrade request

---

## 3. Frontend API Layer Additions

### 3.1 New Types (`frontend/src/api/base_types/orders.ts`)

```typescript
/* ---- Reason Lookups ---- */
export interface CancellationReason {
  reason_id: number;
  reason_code: string;
  reason_name: string;
  reason_type: 'customer' | 'seller' | 'platform' | 'delivery' | 'system';
  requires_inspection: boolean;
  auto_restock: boolean;
}

export interface ReturnReason {
  reason_id: number;
  reason_code: string;
  reason_name: string;
  reason_type: 'customer' | 'platform' | 'delivery' | 'quality';
  requires_inspection: boolean;
}

export interface ExchangeReason {
  reason_id: number;
  reason_code: string;
  reason_name: string;
  requires_return: boolean;
}

/* ---- Cancellation ---- */
export type CancellationType = 'full_order' | 'partial_item' | 'return_to_sender';
export type RestockStatus = 'pending' | 'auto_restocked' | 'pending_inspection'
                          | 'qc_passed' | 'qc_failed' | 'disposed';

export interface OrderCancellationRead {
  id: number;
  order_id: number;
  order_detail_id: number | null;
  reason_id: number;
  reason_name: string;               // enriched
  cancellation_type: CancellationType;
  cancelled_quantity: number | null;
  restock_status: RestockStatus;
  restocked_at: string | null;
  restocked_quantity: number | null;
  platform_reference: string | null;
  platform_refund_amount: number | null;
  cancelled_by_user_id: number | null;
  cancelled_at: string;
  notes: string | null;
  // enriched
  platform_order_id: string | null;
  recipient_name: string | null;
  platform_name: string | null;
  item_name: string | null;
}

export interface CancelOrderPayload {
  reason_id: number;
  cancellation_type: CancellationType;
  detail_ids?: number[];              // for partial — which line items
  cancelled_quantity?: number;        // for partial_item
  notes?: string;
}

export interface BulkCancelRequest {
  cancellations: {
    order_id: number;
    reason_id: number;
    cancellation_type: CancellationType;
    detail_ids?: number[];
  }[];
}

export interface BulkCancelResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: { order_id: number; success: boolean; error?: string }[];
}

/* ---- Returns ---- */
export type ReturnType = 'customer_return' | 'delivery_failed' | 'platform_return' | 'quality_issue';
export type ReturnStatus = 'requested' | 'approved' | 'rejected' | 'in_transit'
                         | 'received' | 'inspecting' | 'completed' | 'cancelled';
export type InspectionStatus = 'pending' | 'passed' | 'failed' | 'partial';
export type RestockDecision = 'restock' | 'dispose' | 'repair' | 'exchange' | 'pending';

export interface OrderReturnRead {
  id: number;
  order_id: number;
  order_detail_id: number;
  return_type: ReturnType;
  return_reason_id: number;
  reason_name: string;               // enriched
  return_status: ReturnStatus;
  returned_quantity: number;
  inspection_status: InspectionStatus;
  inspection_notes: string | null;
  restock_decision: RestockDecision;
  restocked_quantity: number | null;
  platform_return_reference: string | null;
  notes: string | null;
  requested_at: string;
  completed_at: string | null;
  // enriched
  platform_order_id: string | null;
  recipient_name: string | null;
  platform_name: string | null;
  item_name: string | null;
}

export interface CreateReturnPayload {
  order_detail_id: number;
  return_type: ReturnType;
  return_reason_id: number;
  returned_quantity: number;
  notes?: string;
}

export interface UpdateReturnPayload {
  return_status?: ReturnStatus;
  inspection_status?: InspectionStatus;
  inspection_notes?: string;
  restock_decision?: RestockDecision;
  restocked_quantity?: number;
}

/* ---- Exchanges ---- */
export type ExchangeType = 'same_value' | 'different_value' | 'in_place';
export type ExchangeStatus = 'requested' | 'approved' | 'processing'
                           | 'shipped' | 'completed' | 'cancelled';
export type AdjustmentStatus = 'pending' | 'paid' | 'waived' | 'credited' | 'not_applicable';

export interface OrderExchangeRead {
  id: number;
  original_order_id: number;
  original_detail_id: number;
  exchange_type: ExchangeType;
  exchange_reason_id: number;
  reason_name: string;               // enriched
  exchange_status: ExchangeStatus;
  exchanged_item_id: number | null;
  exchanged_quantity: number;
  original_value: number | null;
  new_value: number | null;
  value_difference: number | null;
  adjustment_status: AdjustmentStatus;
  platform_exchange_reference: string | null;
  notes: string | null;
  requested_at: string;
  completed_at: string | null;
  // enriched
  platform_order_id: string | null;
  recipient_name: string | null;
  original_item_name: string | null;
  new_item_name: string | null;
}

export interface CreateExchangePayload {
  original_detail_id: number;
  exchange_type: ExchangeType;
  exchange_reason_id: number;
  exchanged_item_id?: number;
  exchanged_quantity: number;
  notes?: string;
}

export interface UpdateExchangePayload {
  exchange_status?: ExchangeStatus;
  adjustment_status?: AdjustmentStatus;
  notes?: string;
}

/* ---- Cancellation List Params ---- */
export interface CancellationListParams {
  page?: number;
  page_size?: number;
  cancellation_type?: CancellationType;
  restock_status?: RestockStatus;
  reason_type?: string;
  search?: string;                   // platform_order_id or recipient
  date_from?: string;
  date_to?: string;
}

export interface ReturnListParams {
  page?: number;
  page_size?: number;
  return_status?: ReturnStatus;
  return_type?: ReturnType;
  inspection_status?: InspectionStatus;
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface ExchangeListParams {
  page?: number;
  page_size?: number;
  exchange_status?: ExchangeStatus;
  exchange_type?: ExchangeType;
  search?: string;
  date_from?: string;
  date_to?: string;
}
```

### 3.2 New API Functions (`frontend/src/api/base/orders.ts`)

```typescript
/* ---- Reason Lookups ---- */
listCancellationReasons()  → CancellationReason[]
listReturnReasons()        → ReturnReason[]
listExchangeReasons()      → ExchangeReason[]

/* ---- Cancellations ---- */
listCancellations(params)  → PaginatedResponse<OrderCancellationRead>
cancelOrder(orderId, payload: CancelOrderPayload)   → OrderCancellationRead
bulkCancelOrders(payload: BulkCancelRequest)         → BulkCancelResponse
updateCancellation(id, payload)                      → OrderCancellationRead

/* ---- Returns ---- */
listReturns(params)        → PaginatedResponse<OrderReturnRead>
createReturn(orderId, payload: CreateReturnPayload)  → OrderReturnRead
updateReturn(id, payload: UpdateReturnPayload)       → OrderReturnRead

/* ---- Exchanges ---- */
listExchanges(params)      → PaginatedResponse<OrderExchangeRead>
createExchange(orderId, payload: CreateExchangePayload) → OrderExchangeRead
updateExchange(id, payload: UpdateExchangePayload)      → OrderExchangeRead
```

---

## 4. Feature A — Order List Enhancement

### 4.1 Current State

`OrderDetailsPage.tsx` is already functional with:
- Paginated DataTable with columns: Order #, Platform, Store, Recipient, Items, Total, Status, Date, Actions
- OrderFilters: search, platform, store, status, date range, warehouse
- OrderViewDrawer: detail view with inline editing
- Checkbox multi-select → "Mass Ship" CTA
- OrderStatusBadge, PlatformBadge, FulfillmentStatusBadge

### 4.2 Enhancements Needed

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| **Cancellation badge** | Show `CancellationBadge` next to OrderStatusBadge when `cancellation_status !== 'none'` | Small |
| **Quick actions** | Add "Cancel Order" and "Initiate Return" to `StandardActionMenu` kebab | Small |
| **Bulk cancel CTA** | When orders are selected, show "Cancel Selected" button alongside "Mass Ship" | Small |
| **Sort columns** | Enable click-to-sort on Date, Total, Status columns | Medium |
| **Export CSV** | "Export" button → download filtered orders as CSV | Medium |

### 4.3 Updated Actions Menu

```
StandardActionMenu items:
  - View Details        (opens OrderViewDrawer)
  - Ship Order          (navigates to MassShipPage with single order)
  - Cancel Order        (opens CancelOrderModal)
  - Initiate Return     (opens ReturnModal)
  - Request Exchange    (opens ExchangeModal)
  ─────────────────
  - View Raw Data       (opens JSON viewer in drawer)
```

---

## 5. Feature B — Mass Ship Enhancement

### 5.1 Current State

`MassShipPage.tsx` is a 3-step wizard:
1. **Select Orders** — `ShipmentSelectionStep` (reuses order list with checkboxes)
2. **Assign Tracking** — `TrackingAssignmentStep` (tracking number + courier per order)
3. **Review & Confirm** — `ReviewConfirmStep` (summary + submit)

### 5.2 Enhancements Needed

| Enhancement | Description | Effort |
|-------------|-------------|--------|
| **Backend endpoint** | `POST /api/v1/orders/bulk-ship` must be implemented (types exist, endpoint doesn't) | Backend |
| **CSV import tracking** | Step 2: "Import CSV" button to bulk-fill tracking numbers from a CSV mapping file (platform_order_id → tracking_number, courier) | Medium |
| **Per-line tracking** | Allow different tracking numbers per line item within one order (some platforms ship items separately) | Medium |
| **Partial ship** | Checkbox per line item to ship only selected items, leaving others pending | Medium |
| **Result detail** | Step 3 "done" state: show failed orders with error messages + "Retry Failed" button | Small |

### 5.3 CSV Import Format (Step 2)

```csv
platform_order_id,tracking_number,courier_type
240301ABCXYZ,MY123456789,J&T Express
240301DEFUVW,MY987654321,Pos Laju
```

SheetJS parses → matches against selected orders → auto-fills tracking rows.

---

## 6. Feature C — Order Cancellation Page

### 6.1 Page: `CancellationPage.tsx`

**Route:** `/orders/cancellation`
**Purpose:** View all cancellations, process new cancellations, manage restock workflow.

### 6.2 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Page Header: "Order Cancellations"              [+ Cancel Order]  │
├─────────────────────────────────────────────────────────────────────┤
│  Summary Cards Row                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Pending  │ │ Restocked│ │ QC Pend. │ │ Disposed │              │
│  │   12     │ │   45     │ │    3     │ │    2     │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│  Filters: [Search] [Cancel Type ▾] [Restock Status ▾] [Date Range]│
├─────────────────────────────────────────────────────────────────────┤
│  DataTable                                                          │
│  ┌─────────┬──────────┬──────┬──────┬──────┬────────┬─────┬──────┐│
│  │Order #  │Recipient │Type  │Reason│Qty   │Restock │Date │Action││
│  ├─────────┼──────────┼──────┼──────┼──────┼────────┼─────┼──────┤│
│  │SHP-123  │John Doe  │Full  │Cust. │  --  │Pending │12/03│ ⋮   ││
│  │LAZ-456  │Jane S.   │Part. │OOS   │  2   │Auto    │11/03│ ⋮   ││
│  └─────────┴──────────┴──────┴──────┴──────┴────────┴─────┴──────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Components

| File | Purpose |
|------|---------|
| `CancellationPage.tsx` | Main page: summary cards + filters + DataTable |
| `CancellationFilters.tsx` | Filter bar component |
| `CancelOrderModal.tsx` | Modal for creating a new cancellation |
| `CancellationDetailDrawer.tsx` | Drawer for viewing/editing cancellation details + restock |
| `CancellationStatusBadge.tsx` | Badge for restock_status |
| `CancellationPage.css` | Page-specific styles |

### 6.4 Cancel Order Modal (`CancelOrderModal.tsx`)

**Trigger:** "Cancel Order" from Actions menu OR "+ Cancel Order" button.

```
┌───────────────────────────────────────────┐
│  Cancel Order                         [×] │
├───────────────────────────────────────────┤
│                                           │
│  Order: SHP-240301ABCXYZ                  │
│  Recipient: John Doe                      │
│  Items: 3 line items                      │
│                                           │
│  Cancellation Type:                       │
│  ○ Full Order Cancel                      │
│  ○ Partial Item Cancel                    │
│  ○ Return to Sender (RTS)                 │
│                                           │
│  ── If Partial ──────────────────────     │
│  ☑ Item A — SKU-001 (qty: 3)  Cancel: [2]│
│  ☐ Item B — SKU-002 (qty: 1)             │
│  ☑ Item C — SKU-003 (qty: 5)  Cancel: [5]│
│  ─────────────────────────────────────    │
│                                           │
│  Reason: [Select reason        ▾]        │
│                                           │
│  Platform Reference: [____________]       │
│  Notes:                                   │
│  [                                   ]    │
│  [                                   ]    │
│                                           │
│        [Cancel]  [Confirm Cancellation]   │
└───────────────────────────────────────────┘
```

**Validation:**
- Reason is required
- For partial: at least one line item must be selected
- Cancel quantity must be ≥ 1 and ≤ item's `effective_quantity`
- Cannot cancel already-cancelled items
- Cannot cancel shipped/delivered orders (must use Return instead)

### 6.5 Cancellation Detail Drawer (`CancellationDetailDrawer.tsx`)

Shows full cancellation record with:
- Order info header (platform, store, recipient)
- Cancellation details (type, reason, quantity, date, cancelled by)
- **Restock workflow section:**
  - Current restock status badge
  - If `requires_inspection`: inspection form (pass/fail/partial)
  - Restock quantity input + "Mark Restocked" button
  - Or "Mark Disposed" for failed QC
- Platform reference & refund amount
- Notes (editable)
- Timeline of status changes

### 6.6 Bulk Cancel Flow

When multiple orders are selected on `OrderDetailsPage`:
1. "Cancel Selected" button appears
2. Opens `BulkCancelModal.tsx` — simplified version:
   - All selected orders listed (order #, recipient, item count)
   - Single reason selector (applies to all)
   - Cancellation type: Full Order only (partial not supported in bulk)
   - Confirm → `POST /api/v1/orders/bulk-cancel`
   - Results page: succeeded / failed with error messages

---

## 7. Feature D — Returns & Exchanges Page

### 7.1 Page: `ReturnsExchangesPage.tsx`

**Route:** `/orders/returns`
**Purpose:** Unified page for managing returns and exchanges with tab navigation.

### 7.2 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Page Header: "Returns & Exchanges"          [+ New Return/Exchange]│
├─────────────────────────────────────────────────────────────────────┤
│  Tab Bar:  [Returns (24)]  [Exchanges (8)]                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ── RETURNS TAB ──                                                  │
│                                                                     │
│  Summary Cards Row                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │Requested │ │In Transit│ │Inspecting│ │Completed │              │
│  │    5     │ │    8     │ │    3     │ │   156    │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  Filters: [Search] [Status ▾] [Type ▾] [Inspection ▾] [Date Range]│
│                                                                     │
│  DataTable                                                          │
│  ┌────────┬─────────┬──────┬──────┬───┬──────────┬──────┬────────┐│
│  │Order # │Item     │Type  │Reason│Qty│Status    │Insp. │Action  ││
│  ├────────┼─────────┼──────┼──────┼───┼──────────┼──────┼────────┤│
│  │SHP-123 │Widget A │Cust. │Defect│ 1 │In Transit│Pend. │  ⋮    ││
│  │TIK-789 │Gadget B │Deliv.│Fail  │ 2 │Received  │Pass  │  ⋮    ││
│  └────────┴─────────┴──────┴──────┴───┴──────────┴──────┴────────┘│
│                                                                     │
│  ── EXCHANGES TAB ──                                                │
│                                                                     │
│  Summary Cards Row                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │Requested │ │Processing│ │ Shipped  │ │Completed │              │
│  │    2     │ │    3     │ │    1     │ │   42     │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  Filters: [Search] [Status ▾] [Type ▾] [Date Range]               │
│                                                                     │
│  DataTable                                                          │
│  ┌────────┬─────────┬──────────┬──────┬───┬───────┬──────┬───────┐│
│  │Order # │Original │New Item  │Type  │Qty│Diff   │Status│Action ││
│  ├────────┼─────────┼──────────┼──────┼───┼───────┼──────┼───────┤│
│  │SHP-123 │Widget A │Widget B  │Diff. │ 1 │+RM5.00│Apprvd│  ⋮   ││
│  └────────┴─────────┴──────────┴──────┴───┴───────┴──────┴───────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### 7.3 Components

| File | Purpose |
|------|---------|
| `ReturnsExchangesPage.tsx` | Main page with tab navigation (Returns / Exchanges) |
| `ReturnsTab.tsx` | Returns list: summary cards + filters + DataTable |
| `ExchangesTab.tsx` | Exchanges list: summary cards + filters + DataTable |
| `ReturnFilters.tsx` | Filter bar for returns |
| `ExchangeFilters.tsx` | Filter bar for exchanges |
| `InitiateReturnModal.tsx` | Modal for creating a new return |
| `InitiateExchangeModal.tsx` | Modal for creating a new exchange |
| `ReturnDetailDrawer.tsx` | Drawer: full return lifecycle management |
| `ExchangeDetailDrawer.tsx` | Drawer: full exchange lifecycle management |
| `ReturnStatusBadge.tsx` | Badge component for return_status |
| `ExchangeStatusBadge.tsx` | Badge component for exchange_status |
| `InspectionStatusBadge.tsx` | Badge component for inspection_status |
| `ReturnsExchangesPage.css` | Page-specific styles |

### 7.4 Initiate Return Modal (`InitiateReturnModal.tsx`)

**Trigger:** "Initiate Return" from order Actions menu OR "+ New Return/Exchange" button.

```
┌───────────────────────────────────────────┐
│  Initiate Return                      [×] │
├───────────────────────────────────────────┤
│                                           │
│  Order: [Search order by ID...     ]     │
│  (auto-populates when opened from order)  │
│                                           │
│  Order: SHP-240301ABCXYZ                  │
│  ┌───────────────────────────────────┐    │
│  │ Line Items:                       │    │
│  │ ○ Item A — SKU-001 (qty: 3)      │    │
│  │ ● Item B — SKU-002 (qty: 1)  ✓   │    │
│  │ ○ Item C — SKU-003 (qty: 5)      │    │
│  └───────────────────────────────────┘    │
│                                           │
│  Return Quantity: [1]                     │
│                                           │
│  Return Type:                             │
│  [Customer Return          ▾]            │
│                                           │
│  Reason: [Select reason    ▾]            │
│                                           │
│  Notes:                                   │
│  [                                   ]    │
│                                           │
│        [Cancel]  [Initiate Return]        │
└───────────────────────────────────────────┘
```

**Validation:**
- Order must be in shipped/delivered/completed status
- Line item must be selected
- Return quantity ≥ 1 and ≤ item's effective_quantity minus already-returned
- Reason is required
- Cannot return already-fully-returned items

### 7.5 Initiate Exchange Modal (`InitiateExchangeModal.tsx`)

```
┌───────────────────────────────────────────┐
│  Request Exchange                     [×] │
├───────────────────────────────────────────┤
│                                           │
│  Order: SHP-240301ABCXYZ                  │
│                                           │
│  Original Item:                           │
│  ○ Item A — SKU-001 (qty: 3, RM 25.00)   │
│  ● Item B — SKU-002 (qty: 1, RM 45.00) ✓ │
│                                           │
│  Exchange Type:                           │
│  ○ Same Value (swap for equivalent)       │
│  ● Different Value (swap for different)   │
│  ○ In-Place (replace same item — defect)  │
│                                           │
│  ── If Different Value ──                 │
│  New Item: [Search items...         ]    │
│  Selected: Widget B — SKU-005 (RM 50.00)  │
│  Value Difference: +RM 5.00               │
│  ──────────────────────────               │
│                                           │
│  Exchange Quantity: [1]                   │
│  Reason: [Select reason        ▾]        │
│                                           │
│  Notes:                                   │
│  [                                   ]    │
│                                           │
│        [Cancel]  [Request Exchange]       │
└───────────────────────────────────────────┘
```

**Validation:**
- Order must exist and be modifiable or in shipped/delivered state
- Original line item required
- Exchange quantity ≥ 1 and ≤ effective_quantity
- For "different_value": new item must be selected, value difference auto-calculated
- Reason is required

### 7.6 Return Detail Drawer (`ReturnDetailDrawer.tsx`)

Full return lifecycle management:

```
┌──────────────────────────────────────┐
│  Return #RTN-0042                [×] │
├──────────────────────────────────────┤
│  Status Pipeline:                    │
│  [Req] → [Appr] → [Transit] →       │
│  [Recv] → [Inspect] → [Complete]    │
│  ════════════●═══════════════════    │
│                                      │
│  Order: SHP-240301ABCXYZ             │
│  Item: Widget B — SKU-002            │
│  Qty Returned: 1                     │
│  Return Type: Customer Return        │
│  Reason: Defective product           │
│                                      │
│  ── Status Actions ──                │
│  Current: Received                   │
│  [Mark as Inspecting ▸]             │
│                                      │
│  ── Inspection Section ──            │
│  (visible when status ≥ received)    │
│  Inspection: [Pass ▾]              │
│  Notes: [___________________________]│
│  [Save Inspection]                   │
│                                      │
│  ── Restock Decision ──              │
│  (visible after inspection)          │
│  Decision: ○ Restock ○ Dispose       │
│            ○ Repair  ○ Exchange      │
│  Restock Qty: [1]                    │
│  [Confirm Decision]                  │
│                                      │
│  ── Timeline ──                      │
│  • 12 Mar — Return requested by admin│
│  • 12 Mar — Approved                 │
│  • 13 Mar — Marked in transit        │
│  • 14 Mar — Received at warehouse    │
└──────────────────────────────────────┘
```

### 7.7 Exchange Detail Drawer (`ExchangeDetailDrawer.tsx`)

```
┌──────────────────────────────────────┐
│  Exchange #EXC-0015              [×] │
├──────────────────────────────────────┤
│  Status Pipeline:                    │
│  [Req] → [Appr] → [Proc] →          │
│  [Ship] → [Complete]                 │
│  ══●══════════════════════           │
│                                      │
│  Original Order: SHP-240301ABCXYZ    │
│  Original Item: Widget A (RM 25.00)  │
│  New Item: Widget B (RM 50.00)       │
│  Qty: 1                              │
│  Value Diff: +RM 25.00               │
│                                      │
│  Exchange Type: Different Value      │
│  Reason: Customer upgrade request    │
│  Adjustment: Pending                 │
│                                      │
│  ── Status Actions ──                │
│  Current: Approved                   │
│  [Mark as Processing ▸]             │
│                                      │
│  ── Value Adjustment ──              │
│  (visible for different_value type)  │
│  Status: [Paid ▾]                   │
│  [Update Adjustment]                 │
│                                      │
│  ── Linked Return ──                 │
│  (if exchange requires return)       │
│  Return #RTN-0042: In Transit        │
│  [View Return →]                     │
│                                      │
│  ── Timeline ──                      │
│  • 12 Mar — Exchange requested       │
│  • 13 Mar — Approved by admin        │
└──────────────────────────────────────┘
```

---

## 8. Shared Components & Patterns

### 8.1 Status Badge Components

All badges follow the same pattern — a colored chip with the status label:

```typescript
// Color mapping convention:
const STATUS_COLORS = {
  // Lifecycle (warm → cool progression)
  pending:    'bg-amber-50 text-amber-700 border-amber-200',
  approved:   'bg-blue-50 text-blue-700 border-blue-200',
  processing: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  shipped:    'bg-cyan-50 text-cyan-700 border-cyan-200',
  completed:  'bg-emerald-50 text-emerald-700 border-emerald-200',
  cancelled:  'bg-gray-50 text-gray-500 border-gray-200',
  // Negative
  rejected:   'bg-red-50 text-red-700 border-red-200',
  failed:     'bg-red-50 text-red-700 border-red-200',
  disposed:   'bg-gray-100 text-gray-500 border-gray-300',
  // Inspection
  passed:     'bg-emerald-50 text-emerald-700 border-emerald-200',
  partial:    'bg-orange-50 text-orange-700 border-orange-200',
};
```

### 8.2 Order Lookup Component

Shared "search order" input used in Return and Exchange modals:

```typescript
interface OrderLookupProps {
  value: OrderRead | null;
  onChange: (order: OrderRead | null) => void;
  filterStatuses?: OrderStatus[];  // e.g., only shipped/delivered
}
```

- Debounced search by platform_order_id
- Shows order summary card when selected
- Displays line items for selection

### 8.3 Item Search Component

Reuse existing pattern from `ComponentSearch.tsx` (Bundles module) for exchange item selection.

### 8.4 Status Pipeline Visualiser

Horizontal step indicator showing the lifecycle:

```typescript
interface StatusPipelineProps {
  steps: string[];           // ['Requested', 'Approved', 'In Transit', ...]
  currentStep: string;
  variant?: 'return' | 'exchange' | 'cancellation';
}
```

Renders as connected dots/segments with the current step highlighted.

---

## 9. Integration with OrderViewDrawer

The existing `OrderViewDrawer.tsx` needs a new "Operations" tab/section that shows:

```
┌──────────────────────────────────────┐
│  ── Order Operations ──              │
│                                      │
│  Cancellations (1)                   │
│  ┌──────────────────────────────┐    │
│  │ Partial cancel — 2× SKU-001 │    │
│  │ Reason: Out of stock         │    │
│  │ Restock: Auto-restocked      │    │
│  │ 12 Mar 2026                  │    │
│  └──────────────────────────────┘    │
│                                      │
│  Returns (1)                         │
│  ┌──────────────────────────────┐    │
│  │ Customer return — 1× SKU-002│    │
│  │ Status: Inspecting           │    │
│  │ Reason: Defective            │    │
│  │ [View Details →]             │    │
│  └──────────────────────────────┘    │
│                                      │
│  Exchanges (0)                       │
│  No exchanges for this order.        │
└──────────────────────────────────────┘
```

This requires the `GET /api/v1/orders/{order_id}` response to include `cancellations[]`, `returns[]`, `exchanges[]` — or a separate endpoint like `GET /api/v1/orders/{order_id}/operations`.

---

## 10. Route & Navigation Updates

### 10.1 Routes (`App.tsx`)

```tsx
{/* Orders */}
<Route path="/orders/details" element={<OrderDetailsPage />} />
<Route path="/orders/mass-ship" element={<MassShipPage />} />
<Route path="/orders/cancellation" element={<CancellationPage />} />          {/* NEW */}
<Route path="/orders/returns" element={<ReturnsExchangesPage />} />           {/* NEW */}
```

### 10.2 Sidebar (`nav.config.tsx`)

No changes needed — the sidebar already has entries for:
- Order Details → `/orders/details`
- Mass Ship → `/orders/mass-ship`
- Cancellation → `/orders/cancellation`
- Returns & Exchanges → `/orders/returns`

---

## 11. Implementation Phases

### Phase 1: Backend API (Pre-requisite)

**Estimated scope:** ~400–500 lines of schemas + ~600–800 lines of router endpoints

1. Add schemas for CancellationReason, ReturnReason, ExchangeReason (Read only)
2. Add schemas for OrderCancellation (Create, Read, Update)
3. Add schemas for OrderReturn (Create, Read, Update)
4. Add schemas for OrderExchange (Create, Read, Update)
5. Add BulkCancel request/response schemas
6. Implement reason lookup endpoints (3 GETs)
7. Implement cancellation CRUD endpoints (list, create, update)
8. Implement bulk cancel endpoint
9. Implement return CRUD endpoints (list, create, update)
10. Implement exchange CRUD endpoints (list, create, update)
11. Implement bulk-ship endpoint (already typed in frontend)
12. Extend `GET /orders/{id}` to include operations in response (or add `/orders/{id}/operations`)
13. Seed cancellation, return, and exchange reasons

### Phase 2: Frontend — Order List Enhancement

1. Add "Cancel Order" and "Initiate Return" to order actions menu
2. Add bulk cancel CTA to OrderDetailsPage
3. Show CancellationBadge in order list
4. Wire up OrderViewDrawer operations section

### Phase 3: Frontend — Cancellation Page

1. Create `CancellationPage.tsx` with summary cards + DataTable
2. Create `CancelOrderModal.tsx` with full/partial cancel flow
3. Create `CancellationDetailDrawer.tsx` with restock workflow
4. Create `BulkCancelModal.tsx`
5. Create badge + filter components
6. Wire up API calls and test

### Phase 4: Frontend — Returns & Exchanges Page

1. Create `ReturnsExchangesPage.tsx` with tab navigation
2. Create `ReturnsTab.tsx` + `ReturnFilters.tsx`
3. Create `InitiateReturnModal.tsx`
4. Create `ReturnDetailDrawer.tsx` with inspection + restock workflow
5. Create `ExchangesTab.tsx` + `ExchangeFilters.tsx`
6. Create `InitiateExchangeModal.tsx`
7. Create `ExchangeDetailDrawer.tsx` with value adjustment workflow
8. Create shared components (StatusPipeline, OrderLookup, badges)
9. Wire up API calls and test

### Phase 5: Mass Ship Enhancement

1. Implement `POST /api/v1/orders/bulk-ship` (backend)
2. Add CSV import to TrackingAssignmentStep
3. Add per-line tracking support
4. Add partial ship support
5. Improve result/error display

---

## 12. File Structure (Final)

```
frontend/src/pages/orders/
├── OrderDetailsPage.tsx          (existing — enhanced)
├── OrderDetailsPage.css          (existing)
├── OrderViewDrawer.tsx           (existing — enhanced with operations)
├── OrderViewDrawer.css           (existing)
├── OrderFilters.tsx              (existing)
├── OrderFilters.css              (existing)
├── OrderLineItemsTable.tsx       (existing)
├── OrderTimeline.tsx             (existing)
├── OrderTimeline.css             (existing)
├── OrderStatusBadge.tsx          (existing)
├── FulfillmentStatusBadge.tsx    (existing)
├── PlatformBadge.tsx             (existing)
│
├── MassShipPage.tsx              (existing — enhanced)
├── MassShipPage.css              (existing)
├── ShipmentSelectionStep.tsx     (existing)
├── TrackingAssignmentStep.tsx    (existing — enhanced with CSV import)
├── ReviewConfirmStep.tsx         (existing)
│
├── CancellationPage.tsx          ★ NEW
├── CancellationPage.css          ★ NEW
├── CancellationFilters.tsx       ★ NEW
├── CancelOrderModal.tsx          ★ NEW
├── BulkCancelModal.tsx           ★ NEW
├── CancellationDetailDrawer.tsx  ★ NEW
├── CancellationStatusBadge.tsx   ★ NEW
│
├── ReturnsExchangesPage.tsx      ★ NEW
├── ReturnsExchangesPage.css      ★ NEW
├── ReturnsTab.tsx                ★ NEW
├── ReturnFilters.tsx             ★ NEW
├── InitiateReturnModal.tsx       ★ NEW
├── ReturnDetailDrawer.tsx        ★ NEW
├── ReturnStatusBadge.tsx         ★ NEW
├── InspectionStatusBadge.tsx     ★ NEW
├── ExchangesTab.tsx              ★ NEW
├── ExchangeFilters.tsx           ★ NEW
├── InitiateExchangeModal.tsx     ★ NEW
├── ExchangeDetailDrawer.tsx      ★ NEW
├── ExchangeStatusBadge.tsx       ★ NEW
│
├── shared/
│   ├── OrderLookup.tsx           ★ NEW (search order input)
│   └── StatusPipeline.tsx        ★ NEW (horizontal step indicator)
```

---

## 13. Open Questions

1. **Refund tracking:** Should the cancellation/return flow track refund amounts and payment status? The `platform_refund_amount` field exists on OrderCancellation but there's no dedicated refund entity.

2. **Automatic status transitions:** Should certain status changes cascade? E.g., when all return items are inspected and restocked, auto-complete the return? Or always require manual confirmation?

3. **Exchange new order creation:** When an exchange is approved, should the system auto-create a new Order + OrderDetail for the replacement item? Or is this handled manually?

4. **Platform sync:** Should cancellations/returns sync back to the e-commerce platform (Shopee/Lazada/TikTok) via their APIs? This would be a future enhancement but affects the data model.

5. **Permissions:** Should cancellation/return/exchange creation be restricted to certain user roles? The backend has `cancelled_by_user_id` / `initiated_by_user_id` fields suggesting audit trails.

---

## 14. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Backend cancellation/return/exchange schemas | Not started | Must be built in Phase 1 |
| Backend operation endpoints | Not started | Must be built in Phase 1 |
| Backend bulk-ship endpoint | Not started | Types exist in frontend |
| Seed data for reason tables | Not started | Required for dropdown options |
| DataTable component | Available | Existing shared component |
| StandardActionMenu | Available | Existing shared component |
| ComponentSearch pattern | Available | Reusable for item search in exchanges |