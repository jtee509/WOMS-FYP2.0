# WOMS Implementation Plan — Inventory & Operations Modules
**Prepared against:** PRE-ALPHA v0.9.1 (frontend) · PostgreSQL 52-table schema  
**Document scope:** Modules 1–6 as specified  
**Last updated:** 2026-03-18

---

## How to Read This Document

Each module section follows the same structure:

1. **DB Mapping** — which existing tables are used, and any schema gaps that require a migration
2. **Backend Improvements** — what must be added or changed in the backend specifically for this module
3. **Frontend Improvements** — what must be added or changed in the frontend specifically for this module
4. **Existing Frontend Leverage** — components/pages that already exist and can be extended
5. **New Files Required** — complete file list following the `src/pages/<module>/` convention
6. **Workflow Breakdown** — step-by-step UX flow with UI states
7. **API Endpoints Needed** — new or extended endpoints required

A consolidated view of all backend and frontend work across all modules follows the module sections.

---

## Module 1 — Stock Location Management

### DB Mapping

| Requirement | Table / Column |
|---|---|
| 6-level location hierarchy | `inventory_location` (section → zone → aisle → bay → level → position) |
| Functional zone type | `inventory_location.inventory_type_id` → `inventory_type` |
| Occupancy tracking | `inventory_location.current_utilization`, `inventory_location.max_capacity` |
| One-to-Many SKU ↔ Location | `location_slots` (item_id, location_id, is_primary, max_quantity, priority) |
| Reserved quantity | `inventory_levels.reserved_qty` *(schema gap — see below)* |
| Live stock per location | `inventory_levels` (location_id, item_id, quantity_available) |

**Schema Gap — `reserved_qty`:**  
The inventory guard service references `reserved_qty` in conflict checks, but the column is not in the current schema definition. Confirm whether it exists in the live DB; if not, add it:

```sql
ALTER TABLE inventory_levels ADD COLUMN reserved_qty INTEGER NOT NULL DEFAULT 0;
```

If it already exists, just add it to the `InventoryLevelRead` Pydantic schema and the `InventoryLevelRead` TypeScript interface.

### Backend Improvements

**Why these improvements are needed:** Without `reserved_qty` the occupancy badge has only two meaningful states (empty / occupied). Without the 5 location slot endpoints there is no way to manage item-to-bin assignments through the UI. Without wiring `FunctionalZoneConfig` to real DB tables, zone definitions vanish on page refresh.

**Schema change:**
```sql
ALTER TABLE inventory_levels ADD COLUMN reserved_qty INTEGER NOT NULL DEFAULT 0;
```

**New Pydantic schemas:**
- Add `reserved_qty: int` to `InventoryLevelRead`
- Add `LocationSlotRead` and `LocationSlotCreate` schemas

**New endpoints (5):**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/warehouse/{id}/locations` | List locations with utilization + reserved_qty |
| `GET` | `/warehouse/locations/{location_id}/slots` | List all slot assignments for a location |
| `POST` | `/warehouse/locations/{location_id}/slots` | Assign an item to a location |
| `PATCH` | `/warehouse/locations/{location_id}/slots/{slot_id}` | Update slot (max_qty, priority, is_primary) |
| `DELETE` | `/warehouse/locations/{location_id}/slots/{slot_id}` | Remove slot assignment |

**What this unlocks:** A proper 4-state occupancy badge (Empty → Reserved → Occupied → Full). Full CRUD on item-to-bin assignments through the UI. Zone definitions that survive a page refresh and drive real allocation logic.

### Frontend Improvements

**Why these improvements are needed:** `FunctionalZoneConfig` saves zone mappings to localStorage only — they have no effect on actual picking or allocation rules. There is no UI at all for viewing or managing location occupancy visually. The `location_slots` table exists in the DB but is completely invisible to users.

**`FunctionalZoneConfig` migration:** Replace localStorage reads/writes with real `inventory_type` and `inventory_location` API calls. The Settings → Inventory tab keeps the UI but now persists via the API.

**`UnifiedStatusBadge` extension:** Add `location_status` domain with four values: `empty`, `reserved`, `occupied`, `full`.

**TypeScript additions** (`base_types/warehouse.ts`):
- Add `reserved_qty: number` to `InventoryLevelRead`
- Add `LocationSlotRead`, `LocationSlotCreate` interfaces

**API client additions** (`api/base/warehouse.ts`):
- `listLocationSlots(locationId)`, `assignLocationSlot(locationId, data)`, `updateLocationSlot(locationId, slotId, data)`, `removeLocationSlot(locationId, slotId)`

### Existing Frontend Leverage

- `AllocationRulePage` + `FunctionalZoneConfig` (v0.7.0) — exist but localStorage-only; wire to DB
- `UnifiedStatusBadge` — extend with `location_status` domain
- Existing location picker components in movement forms — reuse for slot assignment modal

### New Files Required

```
src/pages/warehouse/locations/
  LocationManagementPage.tsx        # Main page: warehouse selector + grid/list toggle
  LocationManagementPage.css
  LocationGridView.tsx              # Visual card grid — each card = one location bin
  LocationGridView.css
  LocationListView.tsx              # Tabular fallback for high-density warehouses
  LocationDetailDrawer.tsx          # Slide-over: occupancy meter, slot assignments, type badge
  LocationDetailDrawer.css
  LocationOccupancyBadge.tsx        # "Empty" / "Occupied" / "Reserved" / "Full" pill
  LocationSlotTable.tsx             # Shows all location_slots rows for this location
  LocationSlotAssignModal.tsx       # Assign/remove item-to-location mapping
  hooks/
    useLocationOccupancy.ts         # Derives status from current_utilization, max_capacity, reserved_qty
```

### Workflow Breakdown

**Main View (LocationManagementPage)**
1. Warehouse selector dropdown (top of page)
2. Filter bar: Zone type (inventory_type), Aisle, Status (Empty/Occupied/Reserved/Full)
3. Toggle: Grid View ↔ List View
4. Grid View: Each location card shows `display_code`, `inventory_type_name` badge, occupancy progress bar `(current_utilization / max_capacity)`, and `LocationOccupancyBadge`
5. Click any card → `LocationDetailDrawer` slides in

**LocationDetailDrawer**
1. Header: `display_code`, `inventory_type` badge, is_active toggle
2. Occupancy meter: numeric `current_utilization / max_capacity` + progress bar
3. Occupancy status badge: computed from utilization + reserved_qty
4. **Slot Assignments tab** (`LocationSlotTable`): lists all `location_slots` rows — columns: Item Name, SKU, Is Primary, Max Qty, Priority, Allocation Source (manual / ml_suggested / ml_auto)
5. "Assign Item" button → `LocationSlotAssignModal` (item search + primary toggle + max qty + priority)
6. Inline remove button on each slot row

**Occupancy Badge Logic** (`useLocationOccupancy.ts`):
```
Empty    → current_utilization === 0 AND reserved_qty === 0
Reserved → current_utilization === 0 AND reserved_qty > 0
Occupied → 0 < current_utilization < max_capacity
Full     → current_utilization >= max_capacity
```
If `max_capacity` is null → badge shows Occupied when utilization > 0, otherwise Empty.

---

## Module 2 — Stock In (Inbound Logistics)

### DB Mapping

| Requirement | Table / Column |
|---|---|
| Session lifecycle | `receiving_sessions` (draft → in_progress → completed / discrepancy) |
| Expected item lines | `receiving_lines` (session_id, item_id, expected_qty, received_qty, discrepancy flag) |
| Document attachments | `receiving_documents` (session_id FK, movement_id FK, file metadata) |
| Customer return source | `order_returns` (return_status, inspection_status, restock_decision) |
| Inventory impact | `inventory_movements` (Receipt type) + `inventory_transactions` |

**Schema Gap — Source Type on ReceivingSession:**

```sql
ALTER TABLE receiving_sessions 
  ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'supplier_shipment',
  ADD COLUMN linked_return_id INTEGER REFERENCES order_returns(id);
```

**Schema Gap — Unexpected Items on ReceivingLine:**

```sql
ALTER TABLE receiving_lines 
  ADD COLUMN is_unexpected BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN unexpected_notes TEXT;
```

### Backend Improvements

**Why these improvements are needed:** The existing `StockInPanel` has no concept of origin — supplier sessions and customer return sessions are structurally identical. If physical counts differ from expected, the API currently allows completion without any explanation. Items arriving outside the packing slip have no structured representation.

**Schema changes:** Both migrations above.

**New business logic service — Discrepancy Gate:**
Called inside `POST /receiving/sessions/{id}/complete`. Queries all lines for the session; if any line has `received_qty ≠ expected_qty` and no `discrepancy_report` row exists, returns `409 Conflict` with a structured error body. This is enforced at the API layer — not just the frontend — so any future client hits the same gate automatically.

**Updated Pydantic schemas:**
- Add `source_type: Literal['supplier_shipment', 'customer_return']` to `ReceivingSessionCreate` and `ReceivingSessionRead`
- Add `linked_return_id: Optional[int]` to both schemas
- Add `is_unexpected: bool` and `unexpected_notes: Optional[str]` to `ReceivingLineRead`
- Add `DiscrepancyReportCreate` schema

**New endpoints (5):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/warehouse/receiving/sessions` | Create session with `source_type` + optional `linked_return_id` |
| `GET` | `/warehouse/receiving/sessions/{id}/lines` | Get lines with expected/received/discrepancy |
| `POST` | `/warehouse/receiving/sessions/{id}/lines/unexpected` | Add unexpected item line |
| `POST` | `/warehouse/receiving/sessions/{id}/discrepancy-report` | Submit adjustment report (required before completion) |
| `POST` | `/warehouse/receiving/sessions/{id}/complete` | Complete — gated by discrepancy service |

**What this unlocks:** Supplier vs customer return flows have correct and separate audit trails. Discrepancy reports are mandatory before stock is finalised — enforced at the API layer, not just the UI. Unexpected item arrivals are captured and trackable.

### Frontend Improvements

**Why these improvements are needed:** `StockInPanel` treats all sessions identically. There is no UI path for linking a session to a customer return record. The completion button has no awareness of count mismatches — staff can finalise a session with unresolved discrepancies. Unexpected items have nowhere to go.

**`StockInPanel.tsx` modifications:**
- Add `StockInSourceSelector` at session creation step
- Route to `SupplierSessionForm` or `CustomerReturnSessionForm` based on selection
- After count entry, compare received vs expected — if any line has a discrepancy, disable "Complete" and show: *"Discrepancy detected. Adjustment Report required before finalising."*
- Add "Add Unexpected Item" row button below the line table

**TypeScript additions** (`base_types/receiving.ts`):
- Add `source_type`, `linked_return_id` to `ReceivingSessionRead`
- Add `is_unexpected`, `unexpected_notes` to `ReceivingLineRead`
- Add `DiscrepancyReportCreate` interface

**API client additions** (`api/base/receiving.ts`):
- `createUnexpectedLine(sessionId, data)`, `submitDiscrepancyReport(sessionId, data)`, `completeSession(sessionId)`

### Existing Frontend Leverage

- `StockInPanel.tsx` (v0.8.1) — extend rather than replace
- `DocumentUploadZone.tsx` (v0.9.1) — reuse in both supplier and return paths
- `QuickStockInForm.tsx` (v0.9.1) — retain for ad-hoc receipts
- `UnifiedStatusBadge` — extend with `receiving` domain statuses

### New Files Required

```
src/pages/warehouse/inventory/movements/
  StockInSourceSelector.tsx         # "Supplier Shipment" vs "Customer Return" toggle/tabs
  SupplierSessionForm.tsx           # Supplier flow: PO ref, supplier name, expected lines
  CustomerReturnSessionForm.tsx     # Return flow: order lookup, return_id link
  DiscrepancyReportModal.tsx        # Forced modal when counts differ — blocks completion
  UnexpectedItemForm.tsx            # Add-row UI for items not on packing slip
  ReceivingLineTable.tsx            # Shared: expected vs received with delta column
```

### Workflow Breakdown

**Supplier Shipment Path**
1. User clicks "+ New Session" → `StockInSourceSelector` appears
2. Selects "Supplier Shipment"
3. `SupplierSessionForm`: fill supplier name, PO/DO reference number, expected arrival, add expected item lines
4. Session created → moves to scan/count phase
5. Staff scans barcodes or manually enters received quantities per line
6. If any line received ≠ expected: "Complete Session" disabled; warning banner appears
7. User clicks "Submit Adjustment Report" → `DiscrepancyReportModal` — requires reason per discrepant line + overall notes; submission re-enables "Complete Session"
8. User can click "Add Unexpected Item" → `UnexpectedItemForm` (item search + qty + reason)
9. Complete → `inventory_movements` Receipt created → stock updated

**Customer Return Path**
1. Selects "Customer Return" in `StockInSourceSelector`
2. `CustomerReturnSessionForm`: search for order number or return reference → resolves to `order_returns` record → shows expected return items
3. Same count/scan workflow as supplier path
4. If received items differ from the return record → `UnexpectedItemForm` captures the difference
5. Discrepancy gate still applies
6. On complete: `order_returns` record updated (`received_at`, `inspection_status → pending`) + inventory received

---

## Module 3 — Inter-Warehouse Transfer

### DB Mapping

| Requirement | Table / Column |
|---|---|
| Transfer Order (TO) entity | `inventory_movements` (Transfer type, `reference_id` for TO number) |
| TO reference number + barcode | `sys_sequence_config` (TRANSFER_ORDER module, barcode_format field) |
| Item list on TO | `inventory_transactions` (paired inbound/outbound per item) |
| Photo/document uploads | `receiving_documents` (movement_id FK) |
| Discrepancy on receipt | `inventory_movements.discrepancy_report` JSONB *(schema gap — see below)* |

**TO lifecycle** maps to existing `inventory_movements.status`:
- Draft/Packing → `pending`
- Dispatched → `in_transit` (stock deducted at this point)
- Received → `completed` (inbound stock added)

**Schema Gap — Transfer-Specific Metadata:**

```sql
ALTER TABLE inventory_movements
  ADD COLUMN source_warehouse_id INTEGER REFERENCES warehouse(id),
  ADD COLUMN dest_warehouse_id INTEGER REFERENCES warehouse(id),
  ADD COLUMN packing_confirmed_by INTEGER REFERENCES users.user_id,
  ADD COLUMN packing_confirmed_at TIMESTAMP,
  ADD COLUMN receiver_notes TEXT,
  ADD COLUMN discrepancy_report JSONB;
```

**`sys_sequence_config` — new row required:**
```sql
INSERT INTO sys_sequence_config (module_name, name, barcode_format, ...)
VALUES ('TRANSFER_ORDER', 'Transfer Order Reference', 'Code-128', ...);
```

### Backend Improvements

**Why these improvements are needed:** `inventory_movements` uses `reference_id` as a plain `VARCHAR` with no semantic knowledge of which warehouses are involved or who confirmed packing. The existing panel can ship and receive transfers but has no packing confirmation step. Receivers have no way to see incoming transfers without the sender manually communicating. There is no structured reference number or barcode for scan-to-receive.

**Updated Pydantic schemas:**
- Add `source_warehouse_id`, `dest_warehouse_id`, `packing_confirmed_by`, `packing_confirmed_at`, `receiver_notes`, `discrepancy_report` to `InventoryMovementRead`

**New endpoints (5):**

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/warehouse/{id}/transfers/schedule` | Incoming `in_transit` TOs for a warehouse |
| `GET` | `/warehouse/transfers/{movement_id}/manifest` | TO item list |
| `PATCH` | `/warehouse/transfers/{movement_id}/packing-confirm` | Confirm packing (sets packing fields) |
| `POST` | `/warehouse/transfers/{movement_id}/discrepancy` | Save discrepancy report |
| `GET` | `/warehouse/transfers/{movement_id}/pdf-data` | All data needed for printable document |

**What this unlocks:** Packing confirmation is timestamped and attributed to a user — full chain of custody. Receivers see a schedule of incoming transfers without relying on the sender. The printable TO document with master barcode enables scan-to-receive at the dock.

### Frontend Improvements

**Why these improvements are needed:** The existing `InterWarehousePanel` has Ship/Receive/Cancel actions but no packing confirmation step and no link to a detailed TO view. `TransferListPage` has no incoming schedule for receivers. There is no printable document and no barcode display anywhere in the transfer flow.

**`InterWarehousePanel.tsx` modifications:**
- Add "View Transfer Order" link on each list row → `TransferOrderDetailPage`
- Add "Confirm Packing" action for `pending` outbound transfers (currently only Ship/Cancel exist)

**TypeScript additions** (`base_types/warehouse.ts` or new `base_types/transfer.ts`):
- Add `source_warehouse_id`, `dest_warehouse_id`, `packing_confirmed_by`, `packing_confirmed_at` to `InventoryMovementRead`

**API client additions** (`api/base/transfer.ts`):
- `getTransferSchedule(warehouseId)`, `getTransferManifest(movementId)`, `confirmTransferPacking(movementId)`, `saveTransferDiscrepancy(movementId, data)`, `getTransferPdfData(movementId)`

**npm dependency:**
```bash
npm install react-barcode
```

### Existing Frontend Leverage

- `InterWarehousePanel.tsx` (v0.7.0/v0.8.1) — extend with packing confirmation and TO detail link
- `TransferListPage.tsx` (v0.6.4) — retain; add incoming schedule tab
- `TransferReceiptPage.tsx` (v0.6.4) — two-phase scan-to-verify already built
- `DocumentUploadZone.tsx` (v0.9.1) — reuse for packing photos

### New Files Required

```
src/pages/warehouse/inventory/operations/transfers/
  TransferOrderDetailPage.tsx       # Full TO detail: header + manifest + status timeline + documents
  TransferOrderDetailPage.css
  TransferPackingChecklistPage.tsx  # Sender's packing confirmation view with photo upload
  TransferSchedulePage.tsx          # Receiver's incoming schedule view (calendar/list)
  TransferPDFView.tsx               # Printable document via window.print() + @media print CSS
  TransferDiscrepancyReport.tsx     # Receipt discrepancy capture (extends TransferReceiptPage)
  components/
    TOManifestTable.tsx             # Expected items table
    TOStatusTimeline.tsx            # Created → Packed → In Transit → Received pipeline
    TOBarcodeDisplay.tsx            # Renders master tracking barcode via react-barcode
```

### Workflow Breakdown

**Sender Side — Initiation & Packing**
1. Operations → Inter-Warehouse → "New Transfer Order"
2. Fill: Source warehouse, Destination warehouse, add item lines (item search + qty)
3. Submit → TO created in `pending` status; `sys_sequence_config` generates reference number + barcode
4. TO appears in `TransferSchedulePage` for the destination warehouse immediately
5. Sender opens TO → `TransferPackingChecklistPage`:
   - Checklist of all items/quantities to pack
   - `DocumentUploadZone` for packing photos (uploaded to `receiving_documents.movement_id`)
   - "Confirm Packing" button → sets `packing_confirmed_by` + `packing_confirmed_at`
6. "Mark as Dispatched" → status: `in_transit` (stock deducted from source)

**Transfer Order Document**
- `TransferOrderDetailPage` renders: header (reference, warehouses, date), manifest table, status timeline, attached documents
- "Print / Download PDF" → opens `TransferPDFView` in a new tab (`window.print()` + `@media print` CSS, barcode at top)

**Receiver Side — Schedule & Receipt**
1. `TransferSchedulePage`: list of all `in_transit` TOs destined for this warehouse; shows ETA, sender, item count
2. Click "Receive" → `TransferReceiptPage` — scan TO barcode → `TOManifestTable` auto-populates — scan/enter each item → real-time expected vs scanned grid
3. Any discrepancy → `TransferDiscrepancyReport` captures it (per-line reasons + notes)
4. "Complete Receipt" → status: `completed`; inbound stock added; discrepancy report saved to JSONB

---

## Module 4 — Remove Stock (Disposal)

### DB Mapping

| Requirement | Table / Column |
|---|---|
| Disposal request entity | `inventory_movements` (Write Off type, `status: pending`) |
| SKU + quantity to dispose | `inventory_transactions` (is_inbound: false, quantity_change) |
| Approval audit trail | `disposal_approvals` (new table — preferred over adding columns to movements) |
| Final disposal status | `inventory_movements.status: completed` |
| System audit trail | `audit_log` + `inventory_movements` reference |

**Schema Gap — `disposal_approvals` table:**

```sql
CREATE TABLE disposal_approvals (
  id SERIAL PRIMARY KEY,
  movement_id INTEGER NOT NULL REFERENCES inventory_movements(id),
  action VARCHAR(20) NOT NULL,  -- 'approved', 'rejected', 'edited'
  performed_by INTEGER NOT NULL REFERENCES users.user_id,
  performed_at TIMESTAMP DEFAULT NOW(),
  notes TEXT,
  edited_items JSONB  -- stores manager-adjusted quantities if changed before approving
);
```

**`sys_sequence_config` — new row required:**
```sql
INSERT INTO sys_sequence_config (module_name, name, ...)
VALUES ('DISPOSAL_REQUEST', 'Disposal Request Reference', ...);
```

### Backend Improvements

**Why these improvements are needed:** The existing `ConditionPanel` Write-Off option creates a `completed` movement immediately on submission — stock is deducted with no review step, no manager approval, no audit trail of who authorised the write-off, and no reference number. An audit of inventory write-offs is currently impossible.

**New `disposal_approvals` table:** Stores every action as an immutable row — who requested, who approved/rejected, what quantities were edited, when.

**New business logic service — Disposal Approval:**
- On `approve`: writes to `disposal_approvals`, then triggers the existing `inventory_movements` lifecycle transition (`pending → completed`), which fires `trg_inventory_transaction` to deduct stock
- Handles the "manager edits quantities" case: updates `inventory_transactions` rows (reduce only) before triggering completion

**New permission scope:** Add `approve_disposal` to `roles.permissions.inventory`. Gate `GET /warehouse/disposals/pending-approval` and `POST /warehouse/disposals/{id}/approve` against this scope.

**Updated Pydantic schemas:**
- Add `DisposalApprovalRead` schema
- Add optional `disposal_ref: str` to `InventoryMovementRead` for Write Off type movements

**New endpoints (6):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/warehouse/disposals` | Create disposal request (Write Off movement, pending) |
| `GET` | `/warehouse/disposals` | List disposals (filter by status, requestor) |
| `GET` | `/warehouse/disposals/pending-approval` | Manager queue — gated by `approve_disposal` permission |
| `POST` | `/warehouse/disposals/{id}/approve` | Approve (with optional qty edits); triggers stock deduction |
| `POST` | `/warehouse/disposals/{id}/reject` | Reject with notes |
| `GET` | `/warehouse/disposals/{id}` | Full disposal detail |

**What this unlocks:** Stock write-offs require explicit manager sign-off — preventing unauthorised inventory loss. Every disposal has an immutable audit trail. Disposal reference numbers make write-offs traceable in financial audits.

### Frontend Improvements

**Why these improvements are needed:** The `ConditionPanel` Write-Off card submits immediately with no approval step. There is no manager queue view, no role-gated routing to separate staff and manager views, and no status tracking beyond the movement's own status field.

**Role-gated routing:**
- `DisposalRequestPage` — accessible to Staff, Manager, Admin
- `DisposalApprovalPage` — accessible to Manager+ only; guard checks `roles.permissions.inventory.approve_disposal`

**`OperationsLandingPage.tsx`:** Add "Remove Stock" card with `DeleteForeverIcon`.

**`UnifiedStatusBadge` extension:** Add `disposal` domain with statuses: `pending_approval`, `approved`, `rejected`, `disposed`.

**TypeScript additions** (`base_types/warehouse.ts`):
- Add `DisposalApprovalRead` interface
- Add `disposal_ref?: string` to `InventoryMovementRead`

**API client additions**:
- `createDisposalRequest(data)`, `listDisposals(params)`, `getPendingDisposals()`, `approveDisposal(id, data)`, `rejectDisposal(id, notes)`, `getDisposal(id)`

### Existing Frontend Leverage

- `ConditionPanel.tsx` (v0.7.0) — the Write-Off card should link to `DisposalRequestForm` instead of creating a movement directly; reference only for visual patterns
- `ApproverPage.tsx` approval pattern (stock check v0.8.0) — reuse the card-based approval UI pattern
- `ConfirmationModal.tsx` (stock check v0.8.0) — reuse for the irreversible approval confirmation (danger variant)

### New Files Required

```
src/pages/warehouse/inventory/operations/disposal/
  DisposalRequestPage.tsx           # Staff view: list of own requests + "New Request" button
  DisposalRequestForm.tsx           # Form: item search, quantities, disposal reason, location, notes
  DisposalApprovalPage.tsx          # Manager view: queue of pending requests
  DisposalApprovalCard.tsx          # Per-request card: edit qty + approve/reject actions
  DisposalDetailDrawer.tsx          # Read-only detail view for any disposal record
  DisposalStatusBadge.tsx           # pending_approval / approved / rejected / disposed
```

### Workflow Breakdown

**Request Phase (Staff)**
1. Operations → Remove Stock → `DisposalRequestPage`
2. "New Disposal Request" → `DisposalRequestForm`: item search, quantity per item, disposal reason (damaged / expired / obsolete / write-off), source location, overall notes
3. Submit → `inventory_movements` created (Write Off, `status: pending`) + `inventory_transactions` (outbound, NOT yet deducted)
4. Request appears with `DisposalStatusBadge: pending_approval`

**Approval Phase (Manager)**
1. Operations → Remove Stock → "Pending Approvals" tab → `DisposalApprovalPage`
2. `DisposalApprovalCard` shows: requestor, date, item list, disposal reasons
3. Manager may edit quantities (reduce only) before approving
4. **Approve** → `disposal_approvals` row written; `inventory_movements.status → completed`; stock deducted via lifecycle hook
5. **Reject** → `disposal_approvals` row written with rejection notes; movement stays `pending`; requestor can revise or cancel
6. Approval confirmation uses `ConfirmationModal` (danger variant): *"This will mark [N] units as disposed and permanently remove them from inventory. This action cannot be undone."*

**Execution (Automatic on Approval)**  
The existing `trg_inventory_transaction` fires when `inventory_movements.status → completed`, decrementing `inventory_levels.quantity_available`. No additional trigger required.

---

## Module 5 — Stock Reconciliation (Cycle Counting)

### DB Mapping

| Requirement | Table / Column |
|---|---|
| Count session | `stock_checks` (V2) — draft → in_progress → pending_review → completed |
| Count lines | `stock_check_lines` (first_count_qty, second_count_qty, final_accepted_qty, is_reconciled) |
| Location-based task generation | filter `inventory_levels` by zone/aisle to generate lines |
| Barcode scanning | `EditorPage.tsx` already implements via `useGlobalBarcodeListener` |
| Approval loop | `stock_check_approvals` (L1/L2/L3) + `StockCheckDetailShell` status machine |
| Audit trail | `stock_check_line_history` |
| Ghost Inventory | schema gap — see below |

**Schema Gap — Ghost Inventory / Found Items:**

```sql
ALTER TABLE stock_check_lines ALTER COLUMN inventory_level_id DROP NOT NULL;

ALTER TABLE stock_check_lines
  ADD COLUMN is_ghost_inventory BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN found_location_id INTEGER REFERENCES inventory_location(id),
  ADD COLUMN found_item_notes TEXT;
```

A ghost line has: `inventory_level_id = NULL`, `is_ghost_inventory = TRUE`, `expected_qty = 0`, `first_count_qty = [physically counted]`.

### Backend Improvements

**Why these improvements are needed:** Every `stock_check_line` currently requires a valid `inventory_level_id` — the schema cannot represent an item that physically exists at a location but has no digital record. If a counter finds an unlisted item, there is no structured place to record it. The reconciliation can close without addressing found items at all.

**Schema change:** Ghost inventory migration above.

**New business logic service — Ghost Inventory Resolution:**
Called from `POST /stock-checks/{id}/lines/{line_id}/resolve-ghost`. Handles three outcomes:
- "Confirm & Create Record" → creates a new `inventory_levels` row at `found_location_id` with `final_accepted_qty`. **Important:** this bypasses `trg_inventory_transaction` (which fires on transactions, not level creation) — the service must manually set `quantity_available`, or a supplementary `AFTER INSERT ON inventory_levels` trigger must be added. Clarify this choice before implementation.
- "Flag for Investigation" → writes notes, no stock change
- "Dispose" → creates a Write Off `inventory_movements` entry and routes to the disposal approval flow

**Reconciliation gate extension:** The existing gate that prevents completion when lines are unresolved must also check that all `is_ghost_inventory = TRUE` lines have a resolution action.

**New permission scope:** Add `inventory.reconcile_stock_check` — required for the ghost inventory resolution endpoint.

**Updated Pydantic schemas:**
- Add `is_ghost_inventory: bool`, `found_location_id: Optional[int]`, `found_item_notes: Optional[str]` to `StockCheckLineRead`

**New endpoints (3):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/warehouse/stock-checks/{id}/lines/ghost` | Add ghost inventory line |
| `GET` | `/warehouse/stock-checks/{id}/lines?ghost=true` | Filter ghost lines only |
| `POST` | `/warehouse/stock-checks/{id}/lines/{line_id}/resolve-ghost` | Submit ghost resolution action |

**What this unlocks:** Found items are formally captured in the cycle count — no more workarounds or side notes. Ghost inventory resolution creates proper `inventory_levels` records. Reconciliation reports include ghost items in variance totals, giving management accurate surplus data.

### Frontend Improvements

**Why these improvements are needed:** `EditorPage` has no "Found Item" action. Ghost lines cannot be visually distinguished from normal lines. `ReconciliationPage` has no ghost item section and can be completed without addressing found items.

**`EditorPage.tsx` modifications:**
- Add "Add Found Item" floating button (below barcode scanner) → opens `GhostItemEntryForm`
- Ghost lines render with amber background row + `GhostItemBanner` label
- Ghost lines counted in `VarianceFooterBar` totals as surplus

**`ReconciliationPage.tsx` modifications:**
- Add `GhostInventoryResolutionPanel` section at bottom when ghost lines exist
- Block "Complete Reconciliation" confirmation until every ghost line has a resolution action

**`StockCheckListPage.tsx` modifications:**
- Add "Found Items" count badge column (count of `is_ghost_inventory = TRUE` lines per session)

**TypeScript additions** (`base_types/warehouse.ts`):
- Add `is_ghost_inventory`, `found_location_id`, `found_item_notes` to `StockCheckLineRead`

**API client additions**:
- `addGhostLine(checkId, data)`, `resolveGhostLine(checkId, lineId, action)`

### Existing Frontend Leverage

- `StockCheckDetailShell.tsx` + `EditorPage.tsx` + `ApproverPage.tsx` + `ReconciliationPage.tsx` (v0.8.0) — comprehensive; extend, do not replace
- `VarianceFooterBar.tsx`, `LineHistoryDrawer.tsx`, `ConfirmationModal.tsx` — reuse unchanged
- `StockCheckListPage.tsx` — extend with ghost count badge column only

### New Files Required (Ghost Inventory Extension Only)

```
src/pages/warehouse/inventory/stock_check/
  editor/
    GhostItemEntryForm.tsx          # Form: item search, location, qty, notes
    GhostItemBanner.tsx             # Amber label shown on ghost lines in EditorPage
  reconciliation/
    GhostInventoryResolutionPanel.tsx  # Section in ReconciliationPage for ghost lines
    GhostItemActionSelect.tsx          # Per-line: "Create record" / "Flag" / "Dispose"
```

### Workflow Breakdown

**Location-Based Task Generation**
1. "New Stock Check" modal (already exists on `StockCheckListPage`)
2. Extend with: Zone filter, Aisle filter, Section filter (maps to `inventory_location` hierarchy)
3. Backend generates `stock_check_lines` for all `inventory_levels` matching the location scope

**Ghost Inventory Recording**
1. Counter is in `EditorPage` scanning/counting
2. Finds an item with no barcode match — not on the count sheet
3. Clicks "Add Found Item" → `GhostItemEntryForm`: item search (by SKU or name), location picker, physical count qty, notes
4. Submits → `stock_check_line` created: `is_ghost_inventory: true`, `inventory_level_id: null`, `expected_qty: 0`
5. Ghost line appears in `EditorPage` with amber "Found Item" badge
6. Ghost lines appear in variance summary as surplus

**Ghost Inventory Approval & Reconciliation**
1. Approver sees ghost lines flagged separately in `ApproverPage`
2. In `ReconciliationPage`, manager resolves each ghost item via `GhostItemActionSelect`:
   - **"Confirm & Create Record"** → creates new `inventory_level` at the found location
   - **"Flag for Investigation"** → notes recorded, no stock change
   - **"Dispose"** → routes to disposal approval flow

---

## Module 6 — Supplementary Modules

### 6A — Exchange Management

#### DB Mapping

| Requirement | Table / Column |
|---|---|
| Exchange record | `order_exchanges` (exchange_type: same_value / different_value / in_place) |
| SKU swap tracking | `order_exchanges.exchanged_item_id` (new item), `original_detail_id` (original) |
| Return linkage | `order_exchanges.return_id` → `order_returns` |
| Value adjustment | `order_exchanges.value_difference`, `order_price_adjustments` |
| Logistics tracking | `order_details.courier_type`, `tracking_number`, `tracking_source` |

#### Backend Improvements

**Why these improvements are needed:** Exchange type (same-SKU vs different-SKU) is not currently surfaced as distinct UI workflows — the form has no branching. Logistics mode (courier-managed vs manual status updates) is not tracked at the data level; there is no record of whether a shipment uses a courier or relies on manual user-driven updates.

**New shared logistics service:**
- Courier Managed mode: writes `tracking_source: 'courier'` and `tracking_number` on the relevant `order_details` row
- Manual Handling mode: creates `tracking_status` entries on each update call (status_id, notes, warehouse_id, status_date)

This is a **shared** service — not duplicated across exchange and manual return routers.

**What this unlocks:** Exchange type distinction means same-SKU swaps skip the replacement item picker. Logistics mode is auditable — every shipment has a declared tracking method.

#### Frontend Improvements

**Why these improvements are needed:** No exchange form currently exists. `ExchangeTypeSelector` must show/hide `ReplacementItemPicker` based on exchange_type to avoid exposing irrelevant fields to staff.

**TypeScript additions** (new `base_types/operations.ts`):
- `ExchangeFormValues`, `LogisticsMode: 'courier' | 'manual'`, `LogisticsUpdatePayload`

**API client additions**:
- `createExchange(data)`, `listExchanges(params)`, `updateLogisticsStatus(entityType, id, payload)`

#### New Files Required

```
src/pages/operations/exchange/
  ExchangeManagementPage.tsx        # List of all exchanges with status filter
  ExchangeFormPage.tsx              # Create/edit exchange form
  ExchangeFormPage.css
  components/
    ExchangeTypeSelector.tsx        # "Same SKU" vs "Different SKU" toggle
    ExchangeItemPicker.tsx          # Original item lookup (order search → line select)
    ReplacementItemPicker.tsx       # New item search (hidden for Same SKU)
    ValueDifferencePanel.tsx        # Shows original_value, new_value, value_difference
```

#### Workflow

1. Operations → Exchange Management → `ExchangeManagementPage`
2. "New Exchange" → `ExchangeFormPage`:
   - Step 1 — **Exchange Type**: "Same SKU" or "Different SKU" (`ExchangeTypeSelector`)
   - Step 2 — **Original Item**: order search → line select (`ExchangeItemPicker`)
   - Step 3 — **Replacement Item** (Different SKU only): item search (`ReplacementItemPicker`)
   - Step 4 — **Value Adjustment**: `ValueDifferencePanel` auto-calculates; user confirms payment/credit/waiver status
   - Step 5 — **Logistics**: `LogisticsToggle` (see 6C)
   - Submit → creates `order_exchanges` + linked `order_returns` (requires_return = true) + optionally `order_price_adjustments`
3. Exchange list shows status badge (requested / approved / processing / shipped / completed)

---

### 6B — Manual Returns

#### DB Mapping

| Requirement | Table / Column |
|---|---|
| Return record | `order_returns` (return_type: `customer_return`) |
| Return reason | `return_reason` lookup table |
| Non-order returns | `order_returns.order_id` nullable for walk-in returns *(schema gap)* |
| Restock decision | `order_returns.restock_decision` |

**Schema Gap — Walk-In Returns Without Order:**

```sql
ALTER TABLE order_returns ALTER COLUMN order_id DROP NOT NULL;
ALTER TABLE order_returns ALTER COLUMN order_detail_id DROP NOT NULL;
ALTER TABLE order_returns ADD COLUMN manual_return_ref VARCHAR(100);
ALTER TABLE order_returns ADD COLUMN walk_in_customer_name VARCHAR(200);
ALTER TABLE order_returns ADD COLUMN walk_in_phone VARCHAR(50);
```

**`sys_sequence_config` — new row required:**
```sql
INSERT INTO sys_sequence_config (module_name, name, ...)
VALUES ('MANUAL_RETURN', 'Manual Return Reference', ...);
```

#### Backend Improvements

**Why these improvements are needed:** `order_returns.order_id` is `NOT NULL` — walk-in returns with no linked order are structurally impossible. No amount of frontend work fixes this; it is a hard schema constraint. `sys_sequence_config` has no entry for manual returns, so return reference numbers cannot be generated.

**Updated Pydantic schemas:**
- Make `order_id` and `order_detail_id` optional on `OrderReturnCreate`
- Add `manual_return_ref`, `walk_in_customer_name`, `walk_in_phone` to `OrderReturnRead`

**What this unlocks:** Walk-in returns with no order are a first-class record. Every manual return gets a traceable reference number.

#### Frontend Improvements

**Why these improvements are needed:** No manual return form currently exists. The order reference field must be optional — if an order is found, items are pre-populated; if not, the user enters them manually.

**TypeScript additions** (`base_types/operations.ts`):
- `ManualReturnCreate`, `ManualReturnRead`

**API client additions**:
- `createManualReturn(data)`, `listManualReturns(params)`

#### New Files Required

```
src/pages/operations/returns/
  ManualReturnPage.tsx              # List of manual returns
  ManualReturnFormPage.tsx          # Walk-in / non-standard return entry form
  ManualReturnFormPage.css
  components/
    ReturnItemEntry.tsx             # Add items being returned (SKU scan or search)
    ReturnInspectionInline.tsx      # Quick inspection result entry (pass/fail/partial)
```

#### Workflow

1. Operations → Manual Returns → `ManualReturnPage`
2. "New Manual Return" → `ManualReturnFormPage`:
   - **Customer info**: Name, phone
   - **Order reference** (optional): if found, auto-populates expected items; if not found, proceed without order link
   - **Items being returned**: `ReturnItemEntry` — item search + qty per line
   - **Return reason**: dropdown from `return_reason` table
   - **Initial inspection**: `ReturnInspectionInline` — pass/fail/partial toggle with notes
   - **Restock decision**: restock / dispose / repair / pending-review
   - **Logistics**: `LogisticsToggle`
3. Submit → creates `order_returns` with `manual_return_ref` auto-generated via `sys_sequence_config`

---

### 6C — Logistics Integration Toggle

This is a **shared component** used in both Exchange (6A) and Manual Return (6B) forms.

#### DB Mapping

| Mode | Columns Used |
|---|---|
| Courier Managed | `order_details.tracking_number` (manually entered), `tracking_source: 'courier'` |
| Manual Handling | `tracking_status` table — user drives each status update |

#### Backend Improvements

The shared logistics service (described in 6A) handles both modes. No additional schema changes are required for the toggle itself.

#### Frontend Improvements

**Why these improvements are needed:** There is no distinction between courier-managed and manually-managed shipments anywhere in the UI. `LogisticsToggle.tsx` and `ManualStatusUpdater.tsx` must live in `src/components/shared/` — not inside any module's page folder — because they are used across two distinct modules. This is required by Ground Rule #7.

**TypeScript additions** (`base_types/operations.ts`):
- `LogisticsMode: 'courier' | 'manual'`
- `LogisticsUpdatePayload: { status: string; notes: string; warehouse_id: number }`

#### New Files Required

```
src/components/shared/
  LogisticsToggle.tsx               # Toggle + conditional form fields
  LogisticsToggle.css
  ManualStatusUpdater.tsx           # Dropdown of delivery_status + notes + "Update Status" button
```

#### Component Specification

```typescript
interface LogisticsToggleProps {
  mode: 'courier' | 'manual';
  onModeChange: (mode: 'courier' | 'manual') => void;
  trackingNumber?: string;
  onTrackingNumberChange?: (value: string) => void;
  currentStatus?: string;
  onStatusUpdate?: (status: string, notes: string) => void;
}
```

**Courier Managed mode:** Shows a "Tracking Number" text input. Label: *"Enter the courier's tracking number. Status updates will be managed by the courier."*

**Manual Handling mode:** Shows `ManualStatusUpdater` — dropdown of `delivery_status` options + notes field + "Update Status" button. Each update writes to `tracking_status`. Displays a last-3-entries history timeline below.

---

## Cross-Module Navigation Updates

### `OperationsLandingPage.tsx` — Add New Cards

| New Card | Icon | Route |
|---|---|---|
| Remove Stock | `DeleteForeverIcon` | `/inventory/operations/disposal` |
| Exchange Management | `SwapHorizIcon` | `/inventory/operations/exchanges` |
| Manual Returns | `AssignmentReturnIcon` | `/inventory/operations/manual-returns` |

### `nav.config.tsx` and `App.tsx` — New Routes

```
/inventory/locations                     → LocationManagementPage
/inventory/operations/disposal           → DisposalRequestPage
/inventory/operations/disposal/approval  → DisposalApprovalPage  (Manager+ role guard)
/inventory/operations/exchanges          → ExchangeManagementPage
/inventory/operations/exchanges/new      → ExchangeFormPage
/inventory/operations/manual-returns     → ManualReturnPage
/inventory/operations/manual-returns/new → ManualReturnFormPage
/inventory/transfers/:id                 → TransferOrderDetailPage
/inventory/transfers/:id/packing         → TransferPackingChecklistPage
/inventory/transfers/schedule            → TransferSchedulePage
```

The `/inventory/operations/disposal/approval` route must be wrapped in a role guard that checks `roles.permissions.inventory.approve_disposal` before rendering.

---

## Consolidated Backend Improvements

### Schema Migrations (Alembic) — 7 total

All migrations must be applied before any module work begins that depends on them.

| Migration file | Change | Blocks |
|---|---|---|
| `add_reserved_qty_to_inventory_levels` | `reserved_qty INTEGER NOT NULL DEFAULT 0` | Module 1 occupancy badge |
| `add_source_type_to_receiving_sessions` | `source_type`, `linked_return_id` | Module 2 supplier/return split |
| `add_unexpected_flag_to_receiving_lines` | `is_unexpected`, `unexpected_notes` | Module 2 unexpected items |
| `add_transfer_metadata_to_movements` | 6 columns on `inventory_movements` | Module 3 packing confirmation + receiver schedule |
| `add_disposal_approvals_table` | `disposal_approvals` new table | Module 4 approval gate |
| `add_ghost_inventory_to_stock_check_lines` | nullable `inventory_level_id`, 3 ghost columns | Module 5 ghost inventory |
| `add_walk_in_fields_to_order_returns` | nullable `order_id`/`order_detail_id`, 3 walk-in columns | Module 6B manual returns |

### `sys_sequence_config` Seeds — 3 new rows

| Module name | Purpose | Example output |
|---|---|---|
| `TRANSFER_ORDER` | TO reference numbers with Code-128 barcode | `IM-2026-0042` |
| `DISPOSAL_REQUEST` | Disposal form reference numbers | `DSP-2026-0018` |
| `MANUAL_RETURN` | Walk-in return reference numbers | `MR-2026-0007` |

### Business Logic Services — 6 new

| Service | Module | Critical behaviour |
|---|---|---|
| Discrepancy gate | 2 | Returns `409` if count mismatch + no report — enforced at API layer, not just UI |
| Disposal approval | 4 | Holds movements in `pending` until manager acts; handles quantity edits before stock deduction |
| Ghost inventory resolution | 5 | Three paths: create level, flag, dispose — reconciliation blocks if any ghost unresolved |
| Transfer schedule query | 3 | Aggregates `in_transit` movements by `dest_warehouse_id` with item counts |
| Manual return ref generator | 6B | Integrates with `sys_sequence_config` for `MANUAL_RETURN` module |
| Logistics toggle handler | 6A/6B | Shared: courier mode writes `tracking_source`; manual mode creates `tracking_status` entries |

### Pydantic Schema Updates — 12 models

| Schema | Fields added |
|---|---|
| `InventoryLevelRead` | `reserved_qty` |
| `InventoryMovementRead` | `source_warehouse_id`, `dest_warehouse_id`, `packing_confirmed_by`, `packing_confirmed_at`, `receiver_notes`, `discrepancy_report`, `disposal_ref` |
| `ReceivingSessionRead` + `Create` | `source_type`, `linked_return_id` |
| `ReceivingLineRead` | `is_unexpected`, `unexpected_notes` |
| `StockCheckLineRead` | `is_ghost_inventory`, `found_location_id`, `found_item_notes` |
| `OrderReturnRead` + `Create` | `manual_return_ref`, `walk_in_customer_name`, `walk_in_phone`; optional `order_id`/`order_detail_id` |
| `LocationSlotRead` + `Create` | new schemas |
| `DisposalApprovalRead` | new schema |
| `DiscrepancyReportCreate` | new schema |

### Role / Permission Scope Additions

| Scope | Where enforced | Default roles |
|---|---|---|
| `inventory.approve_disposal` | `GET .../pending-approval`, `POST .../approve` | Manager, Admin, Super Admin |
| `inventory.reconcile_stock_check` | Ghost inventory resolution endpoint | Manager, Admin, Super Admin |

### DB Trigger Note (Module 5)

The existing `trg_inventory_transaction` fires `AFTER INSERT` on `inventory_transactions` to update `inventory_levels`. Ghost inventory resolution that creates a new `inventory_levels` row bypasses this trigger entirely. The ghost resolution service must manually set `quantity_available` after creating the row, **or** a new `AFTER INSERT ON inventory_levels` trigger must be added. This decision must be made before Module 5 implementation begins.

---

## Consolidated Frontend Improvements

### New Pages and Components — 18 across 6 modules

| Component | Module | Nature |
|---|---|---|
| `LocationManagementPage` + `LocationGridView` + `LocationDetailDrawer` + `LocationSlotAssignModal` | 1 | New pages |
| `StockInSourceSelector` + `SupplierSessionForm` + `CustomerReturnSessionForm` + `DiscrepancyReportModal` + `UnexpectedItemForm` | 2 | New components extending existing panel |
| `TransferOrderDetailPage` + `TransferPackingChecklistPage` + `TransferSchedulePage` + `TransferPDFView` | 3 | New pages |
| `DisposalRequestPage` + `DisposalApprovalPage` + `DisposalApprovalCard` | 4 | New pages |
| `GhostItemEntryForm` + `GhostInventoryResolutionPanel` + `GhostItemBanner` | 5 | New components extending existing pages |
| `ExchangeFormPage` + `ManualReturnFormPage` | 6 | New pages |

### Existing Files That Need Modification — 6 files

| File | Changes |
|---|---|
| `StockInPanel.tsx` | Source selector, discrepancy gate banner, unexpected item button |
| `InterWarehousePanel.tsx` | "View TO" link per row, "Confirm Packing" action for pending outbound |
| `EditorPage.tsx` | Ghost item button, ghost line visual treatment, `VarianceFooterBar` ghost count |
| `ReconciliationPage.tsx` | `GhostInventoryResolutionPanel` section, ghost resolution gate on completion |
| `StockCheckListPage.tsx` | "Found Items" count badge column |
| `OperationsLandingPage.tsx` | Three new operation cards |

### New Shared Components — 4 in `src/components/shared/`

| Component | Used by |
|---|---|
| `LogisticsToggle.tsx` | `ExchangeFormPage`, `ManualReturnFormPage` |
| `ManualStatusUpdater.tsx` | `LogisticsToggle` (child component) |
| `LocationOccupancyBadge.tsx` | `LocationManagementPage`, `LocationDetailDrawer` |
| `DisposalStatusBadge` (as new domain on `UnifiedStatusBadge`) | `DisposalRequestPage`, `DisposalApprovalPage` |

### TypeScript Interface Additions

| File | Additions |
|---|---|
| `base_types/warehouse.ts` | `reserved_qty` on `InventoryLevelRead`; movement metadata fields on `InventoryMovementRead`; `LocationSlotRead`, `LocationSlotCreate`, `DisposalApprovalRead`; ghost fields on `StockCheckLineRead` |
| `base_types/receiving.ts` | `source_type`, `linked_return_id` on session; `is_unexpected`, `unexpected_notes` on line; `DiscrepancyReportCreate` |
| `base_types/operations.ts` (new) | `ManualReturnCreate`, `ManualReturnRead`, `ExchangeFormValues`, `LogisticsMode`, `LogisticsUpdatePayload` |

### API Client Additions — 22 new functions

All new backend endpoints need corresponding client functions. Key additions not currently existing in any form: `listLocationSlots`, `assignLocationSlot`, `removeLocationSlot`, `createUnexpectedLine`, `submitDiscrepancyReport`, `confirmTransferPacking`, `getTransferSchedule`, `createDisposalRequest`, `approveDisposal`, `rejectDisposal`, `addGhostLine`, `resolveGhostLine`, `createManualReturn`, `updateLogisticsStatus`.

---

## What the Improvements Collectively Achieve

Three patterns emerge that improve WOMS as a whole system, not just per-module.

**Data integrity is enforced at the server, not the browser.** Before the improvements, several critical boundaries existed only as UI controls. The discrepancy gate in Stock In, the approval requirement in Disposal, and the ghost item resolution in Reconciliation were things the frontend could enforce on a good day but the API would bypass. After the improvements, each is a server-side service returning structured error codes. Any future client — mobile app, barcode scanner terminal, third-party integration — hits the same gates automatically.

**Every significant warehouse action is attributed and timestamped.** The `disposal_approvals` table records who approved or rejected each write-off. `packing_confirmed_by` and `packing_confirmed_at` on transfer orders records who signed off on each outbound shipment. `manual_return_ref` generated by `sys_sequence_config` gives walk-in returns a traceable reference number. Before these additions, several actions left no human-attributable record — only a status change with an `updated_at` timestamp.

**Schema gaps that made entire workflows structurally impossible are closed.** `order_returns.order_id` being `NOT NULL` made walk-in returns literally unrepresentable — no frontend work could fix that. `inventory_level_id` being `NOT NULL` on `stock_check_lines` made ghost inventory capture impossible at the data layer. `receiving_sessions` having no `source_type` meant supplier and customer return flows shared a single undifferentiated record type. Each was a hard ceiling on what the plan could deliver. Closing them converts the implementation from "mostly works" to "complete."

---

## DB Migration Summary

| Migration | Description | Depends On |
|---|---|---|
| `add_reserved_qty_to_inventory_levels` | `reserved_qty` column | existing warehouse module |
| `add_source_type_to_receiving_sessions` | `source_type`, `linked_return_id` | existing receiving tables |
| `add_unexpected_flag_to_receiving_lines` | `is_unexpected`, `unexpected_notes` | above |
| `add_transfer_metadata_to_movements` | source/dest warehouse, packing fields, discrepancy JSONB | existing movements |
| `add_disposal_approvals_table` | `disposal_approvals` table | existing movements |
| `add_ghost_inventory_to_stock_check_lines` | nullable `inventory_level_id`, 3 ghost columns | existing stock checks V2 |
| `add_walk_in_fields_to_order_returns` | nullable `order_id`/`order_detail_id`, 3 walk-in columns | existing order_returns |

---

## Recommended Build Sequence

| Step | Module | Rationale |
|---|---|---|
| 1 | Module 4 — Disposal | Smallest scope, self-contained, high value; establishes the approval gate pattern reused across other modules |
| 2 | Module 1 — Location Management | No new workflow complexity; pure CRUD + visual layer; the location picker it produces is used by all other modules |
| 3 | Module 2 — Stock In | Extends existing `StockInPanel`; requires receiving_sessions schema migration first |
| 4 | Module 5 — Ghost Inventory | Extends existing comprehensive stock check infrastructure; one schema migration required |
| 5 | Module 3 — Transfer Orders | Extends existing transfer workflow; `react-barcode` install and PDF generation are the only new technical dependencies |
| 6 | Module 6 — Exchange + Returns + Logistics | Standalone forms; build `LogisticsToggle` shared component first, then `ExchangeFormPage` and `ManualReturnFormPage` in parallel |

---

## Technical Dependencies to Install

| Package | Purpose | Module |
|---|---|---|
| `react-barcode` | Render TO master barcode in `TOBarcodeDisplay.tsx` | Module 3 |

**No PDF library needed.** The `TransferPDFView` page renders print-optimised HTML. `window.print()` + `@media print` CSS converts it to PDF via the browser's native print dialog — consistent with how most WMS tools handle printable documents, and avoids adding bundle weight.
