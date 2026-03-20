# Plan: Stock Check Enhancement — Barcode Scanning + Section-Based Manual Entry

**Module:** Inventory → Stock Check Detail Page
**Status:** COMPLETED
**Version:** PRE-ALPHA v0.6.3
**Date Planned:** 2026-03-15
**Date Completed:** 2026-03-15
**Author:** James (via Claude Code)
**Related Plan:** `docs/planning_phase/Frontend/12_stock_movement_stock_check_frontend.plan.md`

---

## 1. Overview & Rationale

The stock check detail page (implemented in v0.6.x) provides a full lifecycle UI: create → start → count → review → reconcile. However, the counting phase has two usability gaps:

1. **No barcode scanning** — warehouse staff using handheld scanners cannot quickly locate an item's line; they must visually search a flat table of potentially hundreds of lines
2. **No location filtering** — staff counting section-by-section must scroll through all lines with no way to focus on one area at a time

### What this enhancement provides

- **Barcode/SKU scanning input** — type or scan a barcode, instantly locate and focus the matching line's count input; supports physical barcode scanners (which send characters + Enter)
- **Section-based cascading filters** — filter the lines table by warehouse_section → zone → aisle → bay, showing only items in the selected area
- **Section progress chips** — at-a-glance completion indicators per section with click-to-filter shortcut
- **Backend enrichment** — each stock check line now includes `barcode`, `warehouse_section`, `zone`, `aisle`, `bay` fields for client-side matching and filtering (no new endpoints needed)

---

## 2. Backend Changes

### 2.1 Schema: `StockCheckLineRead` — 5 new fields

**File:** `backend/app/schemas/stock_check.py`

```python
class StockCheckLineRead(BaseModel):
    # ... existing fields ...
    barcode: Optional[str] = None           # NEW — from Item.barcode
    warehouse_section: Optional[str] = None  # NEW — from InventoryLocation
    zone: Optional[str] = None               # NEW
    aisle: Optional[str] = None              # NEW
    bay: Optional[str] = None                # NEW
```

### 2.2 Router: `_build_line_read` helper updated

**File:** `backend/app/routers/stock_check.py`

The helper already fetches `Item` and `InventoryLocation` per line. Added extraction of:
- `barcode` from `item.barcode`
- `warehouse_section`, `zone`, `aisle`, `bay` from `loc.*`

Passed into the `StockCheckLineRead` constructor. No new endpoints needed — all data returned in existing `GET /stock-check/{id}` detail response.

### 2.3 Why no new endpoints

The stock check detail response already returns all lines (no pagination on lines). Adding the 5 fields to each line means:
- Barcode matching: instant `Array.find()` client-side
- Section filtering: instant `Array.filter()` client-side
- No additional network round-trips

---

## 3. Frontend Changes

### 3.1 TypeScript types updated

**File:** `frontend/src/api/base_types/warehouse.ts`

Added to `StockCheckLineRead` interface:
```typescript
barcode: string | null;
warehouse_section: string | null;
zone: string | null;
aisle: string | null;
bay: string | null;
```

### 3.2 New component: `BarcodeScanner.tsx`

**File:** `frontend/src/pages/warehouse/inventory/BarcodeScanner.tsx`

**Features:**
- `forwardRef<HTMLInputElement>` — parent can call `.focus()` to return focus after counting
- Input with `QrCodeScannerIcon` prefix, placeholder "Scan or type barcode / SKU..."
- Physical scanner support: Enter key triggers search
- "Search" button for mouse users
- Error display with dismiss button (red banner below input)
- Auto-focus on mount when stock check is `in_progress`
- Auto-clears input after each scan

**Props:**
```typescript
onScan: (value: string) => void;   // Called with trimmed barcode/SKU string
disabled?: boolean;
error: string | null;
onClearError: () => void;
autoFocus?: boolean;
```

### 3.3 New component: `SectionFilterBar.tsx`

**File:** `frontend/src/pages/warehouse/inventory/SectionFilterBar.tsx`

**Features:**
- Four cascading `<select>` dropdowns: Section → Zone → Aisle → Bay
- Options derived from loaded stock check lines (no separate API call)
- Cascading logic: selecting Section limits Zone options to zones within that section, etc.
- Clearing a parent filter clears all child filters
- "Clear" button to reset all filters
- Section progress chips: one per unique `warehouse_section` showing `counted/total` with mini progress bar
- Click a progress chip to activate that section filter
- Green background when section is fully counted

**Props:**
```typescript
lines: StockCheckLineRead[];
filterSection / filterZone / filterAisle / filterBay: string;
onFilterSection / onFilterZone / onFilterAisle / onFilterBay: (v: string) => void;
onClear: () => void;
editCounts: Record<number, string>;  // For progress calculation from unsaved edits
```

### 3.4 Enhanced: `StockCheckDetailPage.tsx`

**File:** `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.tsx`

**New state:**
```typescript
// Barcode scanning
const [barcodeError, setBarcodeError] = useState<string | null>(null);
const [highlightedLineId, setHighlightedLineId] = useState<number | null>(null);
const barcodeInputRef = useRef<HTMLInputElement>(null);

// Section filtering
const [filterSection, setFilterSection] = useState('');
const [filterZone, setFilterZone] = useState('');
const [filterAisle, setFilterAisle] = useState('');
const [filterBay, setFilterBay] = useState('');
```

**New computed values:**
- `filteredLines` — lines filtered by active section/zone/aisle/bay
- `isFiltered` — boolean indicating if any filter is active
- `uncountedInView` — uncounted lines in the filtered view
- `editCountsMap` — map of line_id → counted_quantity string for SectionFilterBar progress

**Barcode scan handler (`handleBarcodeScan`):**
1. Search `check.lines` for matching `barcode` (case-insensitive) or `master_sku` as fallback
2. If no match → show error: `No item with barcode or SKU "XYZ" found in this stock check.`
3. If multiple matches → prefer first uncounted line
4. If matched line is hidden by filters → clear all filters first
5. Set `highlightedLineId` → auto-clear after 3 seconds
6. Scroll to row via `document.getElementById('sc-line-${id}')?.scrollIntoView()`
7. Focus the `data-count-input` within that row

**Table changes:**
- Renders `filteredLines` instead of `check.lines`
- Each `<tr>` has `id={`sc-line-${line.id}`}` for scroll targeting
- Highlighted row gets `ring-2 ring-inset ring-primary bg-blue-50/70` classes
- Count inputs have `data-count-input` attribute for barcode scan focus
- After entering count + Enter on a count input → focus returns to barcode scanner input
- Item cell shows barcode below SKU when available (`BC: ...`)
- "Showing X of Y lines" text when filtered
- Empty state message changes when filtered: "No lines match the current filters."

**Uncounted notice enhancement:**
When filtered, shows both view count and total: "3 lines uncounted in current view (7 total uncounted)."

**Component placement (between Info Panel and Lines Table):**
1. BarcodeScanner — visible only when `status === 'in_progress'`
2. SectionFilterBar — visible when `status === 'in_progress'` or `'pending_review'`
3. Filtered count notice — visible when any filter is active

---

## 4. UX Flow

### Barcode Scanning Flow
1. Staff opens stock check detail (in_progress status)
2. Barcode input is auto-focused
3. Staff scans item barcode → scanner sends characters + Enter
4. Matching row highlights (blue ring), scrolls into view, count input focused
5. Staff types physical count → presses Enter
6. Focus returns to barcode input → ready for next scan
7. If barcode not found → error banner shown, input ready for retry

### Section-Based Manual Entry Flow
1. Staff opens stock check detail (in_progress status)
2. Clicks section progress chip "W1" (or selects from dropdown)
3. Table filters to show only items in section W1
4. Staff counts items in section, entering quantities line by line (Tab to move between inputs)
5. Progress chip updates in real-time as counts are entered
6. When section complete → click next section chip
7. "Clear" button returns to full view

---

## 5. Files Summary

### New Files (2)

| File | Purpose |
|------|---------|
| `frontend/src/pages/warehouse/inventory/BarcodeScanner.tsx` | Barcode/SKU input with scan support |
| `frontend/src/pages/warehouse/inventory/SectionFilterBar.tsx` | Cascading location filters + progress chips |

### Modified Files (3)

| File | Change |
|------|--------|
| `backend/app/schemas/stock_check.py` | Added 5 fields to `StockCheckLineRead` |
| `backend/app/routers/stock_check.py` | Updated `_build_line_read` to populate new fields |
| `frontend/src/api/base_types/warehouse.ts` | Added 5 fields to `StockCheckLineRead` interface |
| `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.tsx` | Integrated barcode scanner, section filters, filtered rendering, highlight/scroll |

---

## 6. Verification

1. **Backend:** `GET /api/v1/stock-check/{id}` response includes `barcode`, `warehouse_section`, `zone`, `aisle`, `bay` on each line ✓
2. **Barcode scanning:** Type known SKU + Enter → row highlights, count input focused ✓
3. **Unknown barcode:** Error message displayed, no crash ✓
4. **Section filtering:** Select section → only matching lines shown ✓
5. **Cascading filters:** Selecting section limits zone dropdown options ✓
6. **Progress chips:** Show counted/total per section, click to filter ✓
7. **Clear filters:** Returns to full view ✓
8. **TypeScript:** `npx tsc --noEmit` passes with no errors ✓
9. **Full workflow:** count → review → reconcile still works unchanged ✓

---

## 7. Edge Cases

| Scenario | Behavior |
|----------|----------|
| Item has no barcode | Barcode search won't match; staff uses section filter + manual scroll |
| Barcode matches master_sku | Fallback: searches SKU if barcode doesn't match |
| Multiple lines with same barcode (different locations) | Prefers first uncounted match |
| Scanned item hidden by active filter | Filters auto-cleared before highlighting |
| All items in one section | Section filter has one option + "All"; progress chips show single section |
| Zero lines after start | Filter controls hidden; empty state message shown |

---

*Phase 1 completed — v0.6.3 Stock Check Barcode + Section Filter enhancement fully implemented 2026-03-15.*

---
---

# Phase 2: Scan-to-Verify — Inter-Warehouse Transfers + Focus Mode

**Status:** COMPLETED
**Version:** PRE-ALPHA v0.6.4
**Date Planned:** 2026-03-15
**Date Completed:** 2026-03-15
**Author:** James (via Claude Code)

---

## 1. Overview & Rationale

Two major gaps remained after Phase 1:

1. **No inter-warehouse transfer workflow** — the existing "Transfer" movement type is intra-warehouse only. There was no way to ship stock between warehouses, generate a manifest, and verify receipt with discrepancy detection.
2. **No Focus Mode** — warehouse staff doing rapid barcode scanning lacked a distraction-free, full-screen interface with audio feedback and auto-sorting.

### What Phase 2 provides

- **Inter-Warehouse Transfer lifecycle** — `DRAFT → SHIPPED → RECEIVED → COMPLETED / CANCELLED` with barcode-scannable manifests
- **Transfer Receipt Page (Scan-to-Verify)** — scan transfer reference to load manifest, then scan items for real-time expected-vs-scanned comparison
- **Transfer List Page** — dashboard of outgoing/incoming transfers with status-based actions
- **RecordMovementDrawer enhancement** — "Inter-Warehouse Transfer" type creates a draft transfer (two-step: draft in drawer, ship from list page)
- **Focus Mode** — distraction-free scanning UI with dark theme, hidden sidebar, audio feedback, and dynamic re-sorting
- **Audio feedback** — Web Audio API tones for success/error/confirm events

---

## 2. Backend Changes

### 2.1 New Model: `backend/app/models/transfer.py`

**`WarehouseTransfer`** (table: `warehouse_transfers`)
| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| reference_number | str, unique, indexed | Generated via sequence engine |
| source_warehouse_id | int FK → warehouse_site | |
| destination_warehouse_id | int FK → warehouse_site | |
| status | str | `draft` → `shipped` → `received` → `completed` / `cancelled` |
| notes / discrepancy_notes | str? | |
| source_movement_id / destination_movement_id | int? FK → inventory_movements | |
| created_by / shipped_by / received_by | int FK → users | |
| created_at / shipped_at / received_at / completed_at | datetime | |

**`TransferLine`** (table: `warehouse_transfer_lines`)
| Field | Type | Notes |
|-------|------|-------|
| id | int PK | |
| transfer_id | int FK → warehouse_transfers | |
| item_id | int FK → items | |
| source_location_id | int FK → inventory_location | |
| expected_quantity / received_quantity | int | |
| status | str | `pending` / `matched` / `short` / `over` / `missing` |
| Unique | (transfer_id, item_id, source_location_id) | |

**Design rationale**: Separate model from InventoryMovement because transfers span two warehouses, have multi-step verification lifecycle, and track manifest-vs-scanned discrepancies.

### 2.2 Schemas: `backend/app/schemas/transfer.py`

Request: `TransferCreate`, `TransferLineCreate`, `TransferVerifyLine`, `TransferVerifyRequest`, `TransferCompleteRequest`
Response: `TransferLineRead` (with item_name, master_sku, barcode, location_code), `TransferRead` (summary), `TransferDetailRead` (with lines)

### 2.3 Router: `backend/app/routers/transfer.py`

| Endpoint | Method | Transition | Key Logic |
|----------|--------|------------|-----------|
| `POST /` | Create | → draft | Validate warehouses, items, locations |
| `GET /` | List | — | Paginated, filter by warehouse/status/direction |
| `GET /{id}` | Detail | — | Returns lines with item/location details |
| `GET /by-reference/{ref}` | Lookup | — | For barcode scanning at receiving end |
| `PATCH /{id}/ship` | Ship | draft → shipped | Creates outbound movement, deducts stock |
| `POST /{id}/verify` | Verify | shipped → received | Accepts scanned quantities, computes line statuses |
| `POST /{id}/complete` | Complete | received → completed | Creates inbound movement at destination |
| `PATCH /{id}/cancel` | Cancel | draft/shipped → cancelled | Reverses outbound movement if shipped |

### 2.4 Seed Data & Sequence Engine

- Added `"Inter-Warehouse Transfer"` to movement types in `seed.py`
- Registered `TRANSFER` module in `sequence.py` (MODULE_TABLE_MAP, MODULE_DISPLAY_NAMES, ALLOWED_SEGMENTS)

### 2.5 Migration

`20260315_0100_00_m8n9o0p1q2r3_add_warehouse_transfer_tables.py` — creates both tables + seeds movement type.

---

## 3. Frontend Changes

### 3.1 API Layer

| File | Purpose |
|------|---------|
| `frontend/src/api/base_types/transfer.ts` | TypeScript interfaces mirroring backend schemas |
| `frontend/src/api/base/transfer.ts` | 8 API wrapper functions (createTransfer, listTransfers, getTransfer, getTransferByReference, shipTransfer, verifyTransfer, completeTransfer, cancelTransfer) |

### 3.2 RecordMovementDrawer Enhancement

**File:** `frontend/src/pages/warehouse/inventory/RecordMovementDrawer.tsx`

When movement type = "Inter-Warehouse Transfer":
- Shows **Target Warehouse** dropdown (excludes current warehouse) instead of destination location
- On submit: calls `createTransfer()` → creates draft only (no stock deduction)
- Shows success panel with generated reference number + copy button
- Stock is only deducted when user clicks "Ship" on TransferListPage

### 3.3 TransferListPage

**File:** `frontend/src/pages/warehouse/inventory/TransferListPage.tsx`

- List of transfers using DataTable with direction/status filters
- Columns: Reference, Direction (Out/In), Partner Warehouse, Status, Lines, Created, Actions
- Status-based actions: Ship/Cancel for outgoing drafts, Receive for incoming shipped, View for completed/cancelled

### 3.4 TransferReceiptPage (Scan-to-Verify)

**File:** `frontend/src/pages/warehouse/inventory/TransferReceiptPage.tsx`

**Two-phase flow:**
1. **Reference Scanner** — scan transfer reference → loads manifest via `getTransferByReference()`
2. **Item Scanner + VerificationGrid** — scan items, real-time expected-vs-scanned comparison

**Scan logic:**
- Match barcode/SKU against manifest lines → increment scanned quantity
- No match → add to extra items list (amber warning)
- Audio feedback on every scan

**Discrepancy handling:**
- All matched → green "Complete Receipt" button
- Any discrepancy → mandatory notes textarea + "Complete with Discrepancies" button
- Extra items are log-only (recorded in notes, NOT added to inventory)

### 3.5 Supporting Components

| Component | File | Purpose |
|-----------|------|---------|
| `DiscrepancyBadge.tsx` | `pages/warehouse/inventory/` | Color-coded status pill (matched/short/over/missing/extra) |
| `TransferManifestHeader.tsx` | `pages/warehouse/inventory/` | Transfer metadata display |
| `VerificationGrid.tsx` | `pages/warehouse/inventory/` | Expected vs Scanned comparison table |
| `audioFeedback.ts` | `pages/warehouse/inventory/` | Web Audio API tones (success/error/confirm) |

### 3.6 Focus Mode (StockCheckDetailPage)

**Additions to:** `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.tsx`

- Toggle button in header (Fullscreen icon) — only visible when `status === 'in_progress'`
- Adds `focus-mode` class to `document.body` via useEffect
- Audio feedback: `playSuccess()` on barcode match, `playError()` on no match
- Dynamic re-sorting: last scanned item jumps to top, then uncounted, then counted
- Progress indicator bar below scanner

**CSS:** `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.css`
- Hides sidebar + app header
- Dark background (#111827), enlarged table text, larger inputs
- High-contrast status badges, dark card surfaces

### 3.7 Routing & Navigation

- `App.tsx`: Added routes `/inventory/transfers` → TransferListPage, `/inventory/transfers/receive` → TransferReceiptPage
- `nav.config.tsx`: Added "Transfers" leaf item under Inventory section with LocalShippingIcon

---

## 4. Files Summary

### New Files (Backend: 4)
| File | Purpose |
|------|---------|
| `backend/app/models/transfer.py` | WarehouseTransfer + TransferLine models |
| `backend/app/schemas/transfer.py` | Request/response schemas |
| `backend/app/routers/transfer.py` | 8 REST endpoints |
| `backend/alembic/versions/20260315_0100_00_..._add_warehouse_transfer_tables.py` | Migration |

### New Files (Frontend: 8)
| File | Purpose |
|------|---------|
| `frontend/src/api/base_types/transfer.ts` | TypeScript interfaces |
| `frontend/src/api/base/transfer.ts` | API client functions |
| `frontend/src/pages/warehouse/inventory/TransferListPage.tsx` | Transfer list/dashboard |
| `frontend/src/pages/warehouse/inventory/TransferReceiptPage.tsx` | Scan-to-verify receipt page |
| `frontend/src/pages/warehouse/inventory/VerificationGrid.tsx` | Expected vs Scanned table |
| `frontend/src/pages/warehouse/inventory/TransferManifestHeader.tsx` | Transfer header display |
| `frontend/src/pages/warehouse/inventory/DiscrepancyBadge.tsx` | Status badge component |
| `frontend/src/pages/warehouse/inventory/audioFeedback.ts` | Web Audio beep/buzz utility |

### New CSS File (1)
| File | Purpose |
|------|---------|
| `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.css` | Focus mode styles |

### Modified Files (7)
| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Import transfer models |
| `backend/app/models/seed.py` | Add "Inter-Warehouse Transfer" movement type |
| `backend/app/services/sequence.py` | Register TRANSFER module |
| `backend/app/main.py` | Register transfer router |
| `frontend/src/pages/warehouse/inventory/RecordMovementDrawer.tsx` | Inter-warehouse transfer mode |
| `frontend/src/pages/warehouse/inventory/StockCheckDetailPage.tsx` | Focus mode + audio + re-sorting |
| `frontend/src/App.tsx` | Transfer routes |
| `frontend/src/components/layout/nav.config.tsx` | Transfers nav item |

---

## 5. Key Design Decisions

1. **Two-step transfer flow**: RecordMovementDrawer creates a draft only; user must explicitly "Ship" from TransferListPage. This allows review before stock is deducted.
2. **Extra items are log-only**: Scanned items not on the manifest are recorded in discrepancy notes but NOT automatically added to destination inventory. Avoids introducing unverified stock.
3. **Separate model**: WarehouseTransfer is not InventoryMovement because transfers span two warehouses, have multi-step verification, and track discrepancies.
4. **Focus Mode via CSS body class**: Simplest approach — no prop drilling, no Context needed. `document.body.classList` toggle with useEffect cleanup.

---

## 6. Verification

1. **Backend**: Transfer lifecycle (create → ship → verify → complete) via API ✓
2. **Backend**: Cancel shipped transfer → stock restored ✓
3. **Backend**: Reference number generation via sequence engine ✓
4. **Frontend**: RecordMovementDrawer "Inter-Warehouse Transfer" → creates draft, shows reference ✓
5. **Frontend**: TransferListPage → Ship/Cancel/Receive actions ✓
6. **Frontend**: TransferReceiptPage → scan reference → scan items → discrepancy detection ✓
7. **Frontend**: Focus Mode toggle → sidebar hidden, dark theme, audio feedback ✓
8. **Frontend**: Dynamic re-sorting in Focus Mode ✓
9. **TypeScript**: `npx tsc --noEmit` passes ✓
10. **Navigation**: Transfer list accessible from sidebar ✓

---

*Phase 2 completed — v0.6.4 Scan-to-Verify + Focus Mode fully implemented 2026-03-15.*
