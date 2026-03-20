# WOMS Implementation Plan — Module 7 & 8: Item & Barcode Logic
**Prepared against:** PRE-ALPHA v0.9.1 (frontend) · PostgreSQL 52-table schema  
**Document scope:** Module 7 (Item & Barcode Logic) + Module 8 (Barcode Label Printing)  
**Depends on:** Modules 1–6 implementation plan  
**Last updated:** 2026-03-18

---

## How to Read This Document

Modules 7 and 8 are broken into **4 phases** that must be built in order. Each phase is a
self-contained, testable increment — phases 1 and 2 are pure backend and shared infrastructure;
phases 3 and 4 are UI and workflow integration.

Each phase section follows the same structure:

1. **What this phase delivers** — the concrete outcome when this phase is done
2. **DB changes** — schema migrations specific to this phase
3. **Backend work** — services, endpoints, Pydantic schemas
4. **Frontend work** — components, hooks, TypeScript interfaces
5. **New files** — complete file list
6. **Acceptance criteria** — how to verify the phase is complete before moving on

---

## Existing Infrastructure Audit

Before any new work begins, understand what the schema already provides so nothing is
duplicated.

### What already exists and must be reused

| Existing asset | Location | Role in this plan |
|---|---|---|
| `items.barcode` | `VARCHAR(200), NULLABLE, UNIQUE INDEX` (added v0.5.41) | Home for composite barcodes on all item/variation rows |
| `items.parent_id` | FK → `items.item_id` | Already encodes the Item → Variation hierarchy |
| `stock_lots.serial_number` | `VARCHAR(100), UNIQUE` | Individual unit serial numbers |
| `stock_lots.unique_barcode` | `VARCHAR(200), UNIQUE` | Lot-level scannable value |
| `sys_sequence_config` | ITEMS, STOCK_LOT_SERIAL, STOCK_LOT_BATCH modules | Barcode generation engine with Code-128, GS1-128, QR support |
| `useGlobalBarcodeListener` | `src/pages/warehouse/inventory/hooks/` | HID keyboard scanner detection |
| `items.variations_data` | JSONB with `combinations[]` | Variation SKU + barcode already stored per combination |
| `prevent_master_sku_update()` trigger | — | SKU immutability already enforced |

### What is genuinely missing

| Gap | Impact |
|---|---|
| No `serial_number_required` flag on `items` | Cannot enforce per-unit serial capture at Stock In |
| No `warranty_expires_at` on `stock_lots` | Cannot validate or display warranty status on scan |
| No `item_unit_cost` on `stock_lots` | Disposal cost impact calculation has no cost basis |
| `sys_sequence_config` ITEMS segment logic does not encode `parent_id` + `item_id` | Composite barcodes (variation-aware) cannot be generated |
| No central scan resolution service | Every workflow implements its own ad-hoc barcode lookup |
| No serial validation endpoint for Stock In | Duplicate or already-existing serials can be silently accepted |
| No `BarcodePrintDrawer` component | Label printing requires full reimplementation per page |
| No `ScanResolverContext` hook | `useGlobalBarcodeListener` is wired per-panel, not shared |

### The three-tier hierarchy — mapped to existing schema

The requested "Item → Variation → Individual Unit" hierarchy already exists structurally. No new
tables are needed:

```
Tier 1 — Item       → items row  (parent_id = NULL, has_variation = TRUE)
Tier 2 — Variation  → items row  (parent_id = {item_id}, barcode = composite value)
Tier 3 — Unit       → stock_lots row  (item_id = variation item_id, serial_number)
```

For non-variation items, Tier 1 and Tier 2 collapse into one `items` row.

---

## Phase 1 — Schema Foundation & Barcode Generation

**Build position:** Immediately after Module 4 (Disposal) — before any other module work.  
**Duration estimate:** 2–3 backend dev days.

### What this phase delivers

- `serial_number_required` flag on items — the upstream switch that controls serial capture
- `warranty_expires_at` and `item_unit_cost` on stock lots
- Composite barcode generation working correctly for both variation and non-variation items
- `sys_sequence_config` ITEMS module updated to produce `ITM-{parent_padded}-{item_padded}` values
- All existing `items.barcode` NULL values can be backfilled on demand

### DB Changes

**Migration 1: `add_serial_fields_to_items`**

```sql
ALTER TABLE items
  ADD COLUMN serial_number_required BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN warranty_period_months  INTEGER;
  -- warranty_period_months: if set, warranty_expires_at on stock_lots is auto-computed
  -- as received_at + warranty_period_months at Stock In time
```

**Migration 2: `add_warranty_and_cost_to_stock_lots`**

```sql
ALTER TABLE stock_lots
  ADD COLUMN warranty_expires_at DATE,
  ADD COLUMN item_unit_cost      NUMERIC(12,2);
```

**`sys_sequence_config` data update — ITEMS module segments:**

The ITEMS module `segments` JSONB must be updated to support composite barcodes. The generation
service reads this at runtime — no further migration needed.

```json
{
  "module_name": "ITEMS",
  "barcode_format": "Code-128",
  "separator": "-",
  "segments": [
    { "type": "literal",  "value": "ITM" },
    { "type": "field",    "field": "root_item_id", "padding": 6 },
    { "type": "field",    "field": "variation_item_id", "padding": 6, "omit_if_null": true }
  ]
}
```

Output examples:
- Non-variation item (item_id 10): `ITM-000010`
- Variation item (parent 10, variation 11): `ITM-000010-000011`

The `omit_if_null` flag on `variation_item_id` means the generation service checks whether
`parent_id` is null. If null, it uses `item_id` as `root_item_id` and omits the variation
segment. If not null, `root_item_id = parent_id` and `variation_item_id = item_id`.

### Backend Work

**Extend the barcode generation service** (`backend/app/services/barcode_service.py`):

- Update `generate_item_barcode(item_id)` to correctly resolve `root_item_id` and
  `variation_item_id` based on `parent_id`
- Add `backfill_item_barcodes(item_ids: list[int])` — bulk generates and writes barcodes for
  any `items` rows where `barcode IS NULL`; idempotent (safe to call multiple times)
- Add `generate_lot_serial_barcode(lot_id)` — uses STOCK_LOT_SERIAL module config; writes to
  `stock_lots.unique_barcode`

**Updated Pydantic schemas:**

- Add `serial_number_required: bool` and `warranty_period_months: Optional[int]` to `ItemRead`
  and `ItemCreate`
- Add `warranty_expires_at: Optional[date]` and `item_unit_cost: Optional[Decimal]` to
  `StockLotRead` and `StockLotCreate`

**New endpoints (2):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/items/barcodes/generate` | Generate barcodes for a list of item IDs (bulk backfill) |
| `POST` | `/items/{id}/barcode/regenerate` | Force regenerate a single item's barcode (admin only) |

### Frontend Work

**`ItemFormPage.tsx` additions:**

Add a "Serialisation & Warranty" section (collapsible, shown below the standard fields):

```
Serialisation
─────────────────────────────────────────────
[ ] Require serial number per unit received
    When enabled, every unit received at Stock In must have an
    individually scanned or manually entered serial number.
    Use for high-value items, electronics, or warranty goods.

Warranty period (months): [ __ ]
    If set, warranty expiry is auto-calculated from the receipt date.
    Leave blank for items with no warranty tracking.
```

Rules:
- `serial_number_required` on a variation item is read-only — it inherits from the parent; show
  a note linking to the parent item
- `warranty_period_months` is only shown when `serial_number_required = TRUE` (warranty tracking
  only makes sense per unit)

**`ItemsListPage.tsx` additions:**

Add a "Serialised" column badge (shown only when `serial_number_required = TRUE`):
- Pill label: `S/N Required` in amber, 11px, compact

**TypeScript additions** (`base_types/items.ts`):
- Add `serial_number_required: boolean` and `warranty_period_months: number | null` to `ItemRead`
- Add `warranty_expires_at: string | null` and `item_unit_cost: number | null` to `StockLotRead`

### New Files

```
backend/app/services/
  barcode_service.py                # Extended with composite generation + backfill

backend/alembic/versions/
  add_serial_fields_to_items.py
  add_warranty_and_cost_to_stock_lots.py
```

```
frontend/src/pages/items/
  components/
    SerialisationSection.tsx        # Collapsible form section for serial + warranty fields
    SerialisedBadge.tsx             # "S/N Required" amber pill badge
```

### Acceptance Criteria

- [ ] Creating a variation item sets `ITM-{parent}-{variation}` as its barcode
- [ ] Creating a non-variation item sets `ITM-{item_id}` as its barcode
- [ ] Setting `serial_number_required = TRUE` on a parent item is reflected on all variation
      rows in `ItemFormPage` (read-only with parent link)
- [ ] `POST /items/barcodes/generate` with 50 item IDs completes without error and writes
      correct composite values
- [ ] `stock_lots` rows can be created with `warranty_expires_at` and `item_unit_cost` populated

---

## Phase 2 — Scan Resolution Service & Serial Validation

**Build position:** Immediately after Phase 1.  
**Duration estimate:** 3–4 backend dev days.

### What this phase delivers

- A single `POST /warehouse/scan/resolve` endpoint that resolves any scanned value across all
  five entity types
- Serial number validation endpoint for Stock In — duplicate and collision detection before
  session completion
- All existing per-panel barcode lookup logic can be replaced by this one service going forward

### DB Changes

No schema changes in this phase. All resolution logic reads from existing tables.

### Backend Work

**New service: `scan_resolution_service.py`**

Central resolution logic. Tries each match in order and returns the first hit:

```python
RESOLUTION_ORDER = [
    resolve_item_barcode,        # items.barcode exact match
    resolve_master_sku,          # items.master_sku exact match (legacy fallback)
    resolve_serial_number,       # stock_lots.serial_number exact match
    resolve_lot_barcode,         # stock_lots.unique_barcode exact match
    resolve_location_code,       # inventory_location.display_code exact match
]
```

**Resolution response shapes:**

```python
# type: "variation" — scanned an item/variation barcode
{
  "type": "variation",
  "item_id": int,
  "parent_id": int | None,
  "item_name": str,
  "master_sku": str,
  "barcode": str,
  "serial_number_required": bool,
  "has_variation": bool
}

# type: "serial_unit" — scanned an individual unit's serial number
{
  "type": "serial_unit",
  "lot_id": int,
  "item_id": int,
  "serial_number": str,
  "unique_barcode": str,
  "warranty_expires_at": date | None,
  "warranty_status": "valid" | "expired" | "none",
  "days_remaining": int | None,
  "current_location_id": int | None,
  "inventory_level_id": int | None
}

# type: "lot" — scanned a batch barcode
{
  "type": "lot",
  "lot_id": int,
  "item_id": int,
  "batch_number": str,
  "unique_barcode": str,
  "expiry_date": date | None,
  "quantity_available": int
}

# type: "location" — scanned a bin location code
{
  "type": "location",
  "location_id": int,
  "display_code": str,
  "inventory_type_name": str,
  "current_utilization": int,
  "max_capacity": int | None
}

# type: "unknown" — no match found
{
  "type": "unknown",
  "scanned_value": str
}
```

**Warranty status computation logic:**

```python
def compute_warranty_status(warranty_expires_at: date | None) -> dict:
    if warranty_expires_at is None:
        return { "warranty_status": "none", "days_remaining": None }
    today = date.today()
    delta = (warranty_expires_at - today).days
    if delta >= 0:
        return { "warranty_status": "valid",   "days_remaining": delta }
    else:
        return { "warranty_status": "expired", "days_remaining": delta }
        # days_remaining is negative when expired
```

**New service: `serial_validation_service.py`**

Called from the Stock In completion flow. Validates a batch of serial numbers before
committing to `stock_lots`:

```python
def validate_serials(item_id: int, serials: list[str]) -> list[SerialValidationResult]:
    # Check 1: duplicates within the submitted batch
    # Check 2: collision against existing stock_lots.serial_number for same item_id
    # Returns per-serial status: "valid" | "duplicate_in_batch" | "already_exists"
```

**New Pydantic schemas:**

- `ScanResolveRequest`: `{ scanned_value: str }`
- `ScanResolveResponse`: union of all five resolution shapes above
- `SerialValidationRequest`: `{ item_id: int, serials: list[str] }`
- `SerialValidationResult`: `{ serial: str, status: "valid" | "duplicate_in_batch" | "already_exists" }`

**New endpoints (2):**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/warehouse/scan/resolve` | Resolve any scanned value — returns typed result |
| `POST` | `/warehouse/receiving/sessions/{id}/validate-serials` | Pre-commit serial validation for Stock In |

### Frontend Work

**New shared hook: `useScanResolver`**

Wraps `useGlobalBarcodeListener` and calls `/warehouse/scan/resolve` on each scan. Returns a
typed resolution result to the consuming component.

```typescript
// src/hooks/useScanResolver.ts

type ScanResolution =
  | { type: 'variation';    itemId: number; parentId: number | null; itemName: string;
      masterSku: string; serialNumberRequired: boolean }
  | { type: 'serial_unit';  lotId: number; itemId: number; serialNumber: string;
      warrantyStatus: 'valid' | 'expired' | 'none'; daysRemaining: number | null;
      currentLocationId: number | null }
  | { type: 'lot';          lotId: number; itemId: number; batchNumber: string;
      expiryDate: string | null; quantityAvailable: number }
  | { type: 'location';     locationId: number; displayCode: string;
      inventoryTypeName: string }
  | { type: 'unknown';      scannedValue: string }

function useScanResolver(
  onResolve: (result: ScanResolution) => void,
  options?: { enabled?: boolean }
): void
```

The `enabled` option allows panels to disable scanning when a modal is open or during
text input focus, preventing accidental scans.

**TypeScript additions** (`base_types/scan.ts` — new file):

```typescript
export type ScanResolution = { ... }   // all five union members
export interface SerialValidationResult {
  serial: string;
  status: 'valid' | 'duplicate_in_batch' | 'already_exists';
}
```

**API client additions** (`api/base/scan.ts` — new file):

```typescript
export function resolveBarcode(scannedValue: string): Promise<ScanResolution>
export function validateSerials(sessionId: number, serials: string[]): Promise<SerialValidationResult[]>
```

### New Files

```
backend/app/services/
  scan_resolution_service.py        # Central resolution logic
  serial_validation_service.py      # Serial duplicate + collision detection

backend/app/routers/
  scan.py                           # POST /warehouse/scan/resolve

backend/app/schemas/
  scan.py                           # ScanResolveRequest, ScanResolveResponse, all resolution shapes
```

```
frontend/src/hooks/
  useScanResolver.ts                # Wraps useGlobalBarcodeListener + scan/resolve endpoint

frontend/src/api/
  base_types/scan.ts                # ScanResolution union type, SerialValidationResult
  base/scan.ts                      # resolveBarcode(), validateSerials()
```

### Acceptance Criteria

- [ ] Scanning `ITM-000010-000011` returns `type: "variation"` with correct `item_id`, `parent_id`
- [ ] Scanning a valid `stock_lots.serial_number` returns `type: "serial_unit"` with
      `warranty_status: "valid"` when `warranty_expires_at` is in the future
- [ ] Scanning `WS1-COLD-A01-B3-2-4` returns `type: "location"` with correct `location_id`
- [ ] Scanning a garbage string returns `type: "unknown"`
- [ ] `validate-serials` with `["SN-001", "SN-001"]` returns `duplicate_in_batch` for the second
- [ ] `validate-serials` with a serial that already exists in `stock_lots` for the same item
      returns `already_exists`
- [ ] `useScanResolver` fires `onResolve` within 200ms of a barcode scan on a dev device

---

## Phase 3 — Stock In Serial Capture & Scan Integration

**Build position:** After Phase 2, concurrent with or just before Module 2 (Stock In) work.  
**Duration estimate:** 3–4 frontend dev days.

### What this phase delivers

- Serial capture mode in `StockInPanel` — triggered when a received item has
  `serial_number_required = TRUE`
- Live per-serial validation with inline error feedback
- Warranty expiry auto-computed from `warranty_period_months` at session completion
- `useScanResolver` wired into all existing scan-enabled panels, replacing ad-hoc lookup code
- Ghost inventory in Reconciliation (Module 5) also benefits — serial scans resolve correctly

### DB Changes

No schema changes in this phase. All reads/writes use columns added in Phase 1.

### Backend Work

**Extend `POST /warehouse/receiving/sessions/{id}/complete`:**

When completing a session that contains lines with `serial_number_required = TRUE`:
1. Verify that every expected unit has a corresponding validated serial (calls serial validation
   service internally)
2. For each serial, create a `stock_lots` row with:
   - `serial_number` = captured serial
   - `item_id` = variation item_id
   - `warranty_expires_at` = `received_at` + `warranty_period_months` (if set on item)
   - `item_unit_cost` = from the receiving line (if captured)
   - `unique_barcode` = generated via STOCK_LOT_SERIAL config

The completion gate sequence becomes:
```
1. validate serials (serial_validation_service)
2. discrepancy gate (existing)
3. complete → create stock_lots + inventory_movements
```

**Extend `ReceivingLineRead` schema:**

```python
class ReceivingLineRead(BaseModel):
    ...
    serial_number_required: bool   # inherited from item
    captured_serials: list[str]    # current serial entries for this line
    serial_validation_results: list[SerialValidationResult]  # live status per serial
```

### Frontend Work

**`ReceivingLineTable.tsx` — serial capture mode**

When `serial_number_required = TRUE` on the line's item, the quantity input column is replaced
by a serial capture column:

```
Item: TSHIRT Red-XL           Expected: 5 units
─────────────────────────────────────────────────
Captured serials:
  SN-001  ✓ valid
  SN-002  ✓ valid
  SN-003  ✗ already exists in system — remove and re-check
  SN-004  ✓ valid

  [  Scan or type serial number...  ] [+Add]

  4/5 valid   •  1 error
```

Behaviour:
- Each serial is validated against `validate-serials` as entered (300ms debounce — not on
  submit, inline)
- `✓ valid` in green, `✗ duplicate_in_batch` or `✗ already_exists` in red with the reason text
- Removing a serial re-triggers validation of the remaining set
- The "Complete Session" gate in `StockInPanel` checks: all `serial_number_required` lines must
  have `captured_serials.length === expected_qty` with no validation errors

**`useScanResolver` wired into `StockInPanel`:**

Replace the existing ad-hoc barcode lookup in `StockInPanel` with `useScanResolver`:

```typescript
useScanResolver((result) => {
  if (result.type === 'variation') {
    matchLineByItemId(result.itemId);
    if (result.serialNumberRequired) {
      openSerialCaptureForLine(result.itemId);
    }
  }
  if (result.type === 'serial_unit') {
    appendSerialToActiveLine(result.serialNumber);
  }
  if (result.type === 'location') {
    setActiveDestinationLocation(result.locationId);
  }
  if (result.type === 'unknown') {
    playError();
    showInlineToast('Barcode not recognised');
  }
});
```

**`useScanResolver` wired into `TransferReceiptPage`:**

Replace the existing manual scan lookup in `TransferReceiptPage`:

```typescript
useScanResolver((result) => {
  if (result.type === 'variation') {
    matchManifestLine(result.itemId);
  }
  if (result.type === 'location') {
    // ignore — location scans not relevant during receipt
  }
  if (result.type === 'unknown') {
    playError();
  }
});
```

**`useScanResolver` wired into `EditorPage` (Stock Check):**

```typescript
useScanResolver((result) => {
  if (result.type === 'variation' || result.type === 'serial_unit') {
    const itemId = result.type === 'serial_unit' ? result.itemId : result.itemId;
    matchCountLine(itemId);
    playSuccess();
  }
  if (result.type === 'location') {
    // switch active section filter to the scanned location's section
    setActiveSection(result.displayCode);
  }
});
```

### New Files

```
frontend/src/pages/warehouse/inventory/movements/
  SerialCaptureInput.tsx            # Individual serial entry field with live validation badge
  SerialCaptureList.tsx             # Full serial capture column for ReceivingLineTable
  SerialValidationBadge.tsx         # ✓ valid / ✗ already_exists inline status badge
```

**Modified files:**

| File | Change |
|---|---|
| `ReceivingLineTable.tsx` | Add serial capture mode column |
| `StockInPanel.tsx` | Replace ad-hoc barcode lookup with `useScanResolver`; add serial completion gate |
| `TransferReceiptPage.tsx` | Replace ad-hoc scan lookup with `useScanResolver` |
| `EditorPage.tsx` | Replace ad-hoc scan lookup with `useScanResolver` |

### Acceptance Criteria

- [ ] Receiving a line where the item has `serial_number_required = TRUE` shows serial capture
      column instead of quantity input
- [ ] Entering a serial that already exists in `stock_lots` for the same item shows `✗ already
      exists` inline without blocking other serials
- [ ] "Complete Session" is disabled until all `serial_number_required` lines have the correct
      count of valid serials with no errors
- [ ] On completion, `stock_lots` rows are created with correct `serial_number` and
      `warranty_expires_at` (if item has `warranty_period_months` set)
- [ ] Scanning a variation barcode in `StockInPanel` matches the correct receiving line
- [ ] Scanning a location code in `StockInPanel` sets the destination location
- [ ] Scanning an unknown barcode plays the error tone and shows the inline message

---

## Phase 4 — Barcode Label Printing (Module 8)

**Build position:** After Phase 1 (barcodes exist) and Phase 2 (scan resolver exists). Can
begin in parallel with Phase 3.  
**Duration estimate:** 3–4 frontend dev days. No backend work in this phase.

### What this phase delivers

- `BarcodePrintDrawer` — shared print slide-over used by all print contexts
- `BarcodeLabelTemplate` — renders one label in three sizes; used for preview and print output
- Print entry points in: Items list, Item detail, Location Management, Stock In completion,
  Ghost inventory recording (Reconciliation)
- Three label types: variation label, serial unit label, lot/batch label
- `@media print` CSS that suppresses the full app shell and renders only the label grid

### DB Changes

None. All data for printing already exists after Phase 1.

### Backend Work

Three thin data-fetch endpoints. No new models or business logic — these are read-only
aggregations of existing data:

| Method | Path | Returns |
|---|---|---|
| `GET` | `/items/barcode-print-data?ids=1,2,3` | `[{ item_id, barcode, item_name, master_sku, serial_number_required, variations[] }]` |
| `GET` | `/warehouse/locations/barcode-print-data?ids=4,5,6` | `[{ location_id, display_code, inventory_type_name }]` |
| `GET` | `/warehouse/receiving/sessions/{id}/barcode-print-data` | All received lines: `[{ item_id, barcode, item_name, received_qty, serial_numbers[], lot_barcode? }]` |

The receiving session endpoint is the only one with any join logic — it reads
`receiving_lines` → `items` + `stock_lots` (for serial-tracked items) in a single query.

**New Pydantic schemas:**

- `ItemBarcodePrintData`
- `LocationBarcodePrintData`
- `SessionBarcodePrintData`

### Frontend Work

**Core shared components** (`src/components/shared/`):

**`BarcodeLabelTemplate.tsx`** — renders one label from a spec. Used for the print preview
inside the drawer, and duplicated into the `#barcode-print-root` div on print:

```typescript
interface BarcodeLabelSpec {
  type: 'variation' | 'serial_unit' | 'lot' | 'location';
  barcodeValue: string;
  barcodeFormat: 'CODE128' | 'QR' | 'CODE39';
  line1: string;           // primary label text (item name or display_code)
  line2?: string;          // secondary (SKU, lot number, inventory type)
  line3?: string;          // tertiary (expiry date, warranty date, serial number)
  labelSize: '50x25' | '100x50' | '100x150';
}
```

Label visual layout per type:

```
── Variation label (50x25mm) ──────────────────
  [CODE128 barcode]
  TSHIRT Red-XL
  SKU: TSHIRT-RED-XL
────────────────────────────────────────────────

── Serial unit label (100x50mm) ───────────────
  [CODE128 barcode]
  TSHIRT Red-XL
  Serial: SN-001
  Warranty: until 2027-03-18   ● VALID
────────────────────────────────────────────────

── Lot label (100x50mm) ───────────────────────
  [CODE128 barcode]
  Batch: BATCH-2026-03
  Expiry: 2026-09-01   Qty: 24
────────────────────────────────────────────────

── Location label (100x50mm) ──────────────────
  [CODE128 barcode — display_code]
  WS1-COLD-A01-B3-2-4
  Pick Face
────────────────────────────────────────────────
```

**`BarcodePrintDrawer.tsx`** — right slide-over panel:

1. Receives `BarcodeLabelSpec[]` + pre-selected `labelSize`
2. Renders a preview of the first label using `BarcodeLabelTemplate` + `react-barcode`
3. Label size selector: `50×25mm (small)`, `100×50mm (standard)`, `100×150mm (large)`
4. Quantity control: global "print N of each" input (default: 1; for Stock In, defaults to
   received quantity per line)
5. "Print" button → calls `printLabels(specs, qty)` function

**`useLabelPrint.ts`** — the print execution hook:

```typescript
function useLabelPrint() {
  function printLabels(specs: BarcodeLabelSpec[], qtyEach: number): void {
    // 1. Build label grid HTML (specs × qtyEach repetitions)
    // 2. Inject into #barcode-print-root
    // 3. Call window.print()
    // 4. On afterprint event, remove #barcode-print-root from DOM
  }
  return { printLabels };
}
```

**`@media print` CSS strategy** (`BarcodePrintDrawer.css`):

```css
@media print {
  /* Suppress entire app */
  body > * { display: none !important; }

  /* Show only print target */
  #barcode-print-root {
    display: block !important;
    position: absolute;
    top: 0; left: 0;
  }

  .label-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, var(--label-width));
    gap: 2mm;
    padding: 5mm;
  }

  .label-cell {
    width: var(--label-width);
    height: var(--label-height);
    overflow: hidden;
    page-break-inside: avoid;
    border: 0.2mm solid #ccc;
    padding: 1.5mm;
    box-sizing: border-box;
  }

  /* Label size variables — set by useLabelPrint based on selected size */
  /* 50x25: --label-width: 50mm; --label-height: 25mm  */
  /* 100x50: --label-width: 100mm; --label-height: 50mm */
}
```

**Integration points — where print buttons appear:**

**Items list (`ItemsListPage.tsx`):**
- Row action menu: "Print Label" → calls `GET /items/barcode-print-data?ids={id}` → opens
  `BarcodePrintDrawer` with variation label spec
- Multi-select toolbar: "Print Labels ({n})" → bulk fetch → opens drawer with all specs

**Item detail (`ItemFormPage.tsx` — edit mode):**
- Add "Print Label" button next to the barcode field (shown only when `barcode` is not null)

**Location Management (`LocationDetailDrawer.tsx`):**
- "Print Bin Label" button in the drawer header
- Row action in `LocationListView`: "Print Label"
- Both call `GET /warehouse/locations/barcode-print-data?ids={id}` → location label spec

**Stock In — post-completion (`StockInPanel.tsx`):**
After the "Session completed" confirmation, show:

```
  Session completed. 24 units received.
  ┌─────────────────────────────────────────────────┐
  │  Print labels for received stock?               │
  │  • 18 × variation labels (non-serialised)       │
  │  • 6 × serial unit labels (TSHIRT Red-XL)       │
  │                                                 │
  │  [Print Received Labels]          [Done, skip]  │
  └─────────────────────────────────────────────────┘
```

Calls `GET /warehouse/receiving/sessions/{id}/barcode-print-data` → opens `BarcodePrintDrawer`
with quantities pre-filled from received amounts. This step is optional — "Done, skip" bypasses
it without consequences.

**Ghost inventory recording (`GhostItemEntryForm.tsx`):**
After recording a ghost item, offer a temporary "Found Item — Unverified" label:

```
Item recorded as found. Print a temporary label?

  [BARCODE]
  FOUND ITEM — UNVERIFIED
  SKU: TSHIRT-RED-XL   Qty: 3
  Loc: WS1-COLD-A01-B3
  Pending reconciliation approval

  [Print Temp Label]   [Skip]
```

The temporary label spec is built client-side without an API call — all data is already
in the `GhostItemEntryForm` state at the time of submission.

### New Files

```
frontend/src/components/shared/
  BarcodeLabelTemplate.tsx          # Single label renderer — preview and print
  BarcodeLabelTemplate.css
  BarcodePrintDrawer.tsx            # Right slide-over: preview + size + qty + print
  BarcodePrintDrawer.css

frontend/src/hooks/
  useLabelPrint.ts                  # Print execution: inject root div + window.print()

frontend/src/api/
  base_types/print.ts               # BarcodeLabelSpec interface
  base/print.ts                     # fetchItemPrintData(), fetchLocationPrintData(),
                                    # fetchSessionPrintData()
```

**Modified files:**

| File | Change |
|---|---|
| `ItemsListPage.tsx` | Add "Print Label" row action and bulk print toolbar button |
| `ItemFormPage.tsx` | Add "Print Label" button next to barcode field in edit mode |
| `LocationDetailDrawer.tsx` | Add "Print Bin Label" header button |
| `LocationListView.tsx` | Add "Print Label" row action |
| `StockInPanel.tsx` | Add post-completion print prompt |
| `GhostItemEntryForm.tsx` | Add temporary label print offer after submission |

### Acceptance Criteria

- [ ] "Print Label" on a variation item opens `BarcodePrintDrawer` with a variation label
      spec pre-populated
- [ ] "Print Label" on a serialised item that has received stock opens the drawer with serial
      unit labels (one spec per serial number)
- [ ] `window.print()` renders only the label grid — app shell is fully suppressed
- [ ] Label size selector changes the rendered preview and the `--label-width` / `--label-height`
      CSS variables before printing
- [ ] Quantity input defaults to 1 for item/location labels and to received qty for post-Stock
      In labels
- [ ] Post-completion print prompt appears after session completes; "Done, skip" bypasses
      it cleanly
- [ ] Ghost item "Print Temp Label" generates a label with the unverified watermark text and
      the found location/qty

---

## Consolidated DB Migration Summary

| Migration | Phase | Change |
|---|---|---|
| `add_serial_fields_to_items` | 1 | `serial_number_required BOOL`, `warranty_period_months INT` on `items` |
| `add_warranty_and_cost_to_stock_lots` | 1 | `warranty_expires_at DATE`, `item_unit_cost NUMERIC(12,2)` on `stock_lots` |

Two migrations total. No existing columns are dropped or renamed.

---

## Consolidated New Files Summary

### Backend

```
backend/app/services/
  barcode_service.py                # Phase 1 — composite generation + backfill
  scan_resolution_service.py        # Phase 2 — central scan resolution
  serial_validation_service.py      # Phase 2 — duplicate + collision detection

backend/app/routers/
  scan.py                           # Phase 2 — POST /warehouse/scan/resolve

backend/app/schemas/
  scan.py                           # Phase 2 — all resolution response shapes
  print.py                          # Phase 4 — print data response schemas

backend/alembic/versions/
  add_serial_fields_to_items.py     # Phase 1
  add_warranty_and_cost_to_stock_lots.py  # Phase 1
```

### Frontend

```
src/hooks/
  useScanResolver.ts                # Phase 2 — wraps useGlobalBarcodeListener + scan/resolve
  useLabelPrint.ts                  # Phase 4 — print execution

src/api/
  base_types/scan.ts                # Phase 2 — ScanResolution union type
  base_types/print.ts               # Phase 4 — BarcodeLabelSpec interface
  base/scan.ts                      # Phase 2 — resolveBarcode(), validateSerials()
  base/print.ts                     # Phase 4 — fetch print data functions

src/components/shared/
  BarcodeLabelTemplate.tsx          # Phase 4 — single label renderer
  BarcodeLabelTemplate.css
  BarcodePrintDrawer.tsx            # Phase 4 — print slide-over
  BarcodePrintDrawer.css

src/pages/items/components/
  SerialisationSection.tsx          # Phase 1 — serial + warranty fields in ItemFormPage
  SerialisedBadge.tsx               # Phase 1 — "S/N Required" badge in ItemsListPage

src/pages/warehouse/inventory/movements/
  SerialCaptureInput.tsx            # Phase 3 — individual serial entry field
  SerialCaptureList.tsx             # Phase 3 — serial capture column
  SerialValidationBadge.tsx         # Phase 3 — ✓ valid / ✗ error badge
```

### Modified existing files (by phase)

| Phase | File | Change |
|---|---|---|
| 1 | `ItemFormPage.tsx` | Add `SerialisationSection` |
| 1 | `ItemsListPage.tsx` | Add `SerialisedBadge` column |
| 1 | `base_types/items.ts` | Add serial + warranty fields to `ItemRead` |
| 2 | — | No frontend file changes in Phase 2 |
| 3 | `ReceivingLineTable.tsx` | Serial capture mode column |
| 3 | `StockInPanel.tsx` | Replace ad-hoc scan logic with `useScanResolver`; serial gate |
| 3 | `TransferReceiptPage.tsx` | Replace ad-hoc scan logic with `useScanResolver` |
| 3 | `EditorPage.tsx` | Replace ad-hoc scan logic with `useScanResolver` |
| 4 | `ItemsListPage.tsx` | Print Label row action + bulk print toolbar |
| 4 | `ItemFormPage.tsx` | Print Label button next to barcode field |
| 4 | `LocationDetailDrawer.tsx` | Print Bin Label header button |
| 4 | `LocationListView.tsx` | Print Label row action |
| 4 | `StockInPanel.tsx` | Post-completion print prompt |
| 4 | `GhostItemEntryForm.tsx` | Temp label print offer |

---

## Build Sequence Within This Plan

| Step | Phase | Key output | Unlocks |
|---|---|---|---|
| 1 | Phase 1 — Schema foundation | `serial_number_required`, composite barcode generation, `warranty_expires_at` | All subsequent phases; `items.barcode` is now correctly populated |
| 2 | Phase 2 — Scan resolution | `useScanResolver` hook, `POST /scan/resolve`, serial validation | Phase 3 (Stock In serial capture), all existing panels switch to centralised resolution |
| 3 | Phase 3 — Stock In integration | Serial capture mode, `useScanResolver` in all scan panels | Serialised goods can be received; scan flow is consistent across all workflows |
| 4 | Phase 4 — Label printing | `BarcodePrintDrawer`, print entry points in all relevant pages | Physical label generation for items, locations, lots, and received stock |

Phases 3 and 4 can run in parallel once Phase 2 is complete — they have no dependency on
each other, only on the shared hook and API infrastructure from Phase 2.

---

## Position in the Overall Module Build Sequence

Inserting Modules 7+8 into the full build order from the main implementation plan:

| Step | Module | Notes |
|---|---|---|
| 1 | Module 4 — Disposal | Establishes approval gate pattern |
| **2** | **Module 7+8 Phase 1** | **Schema foundation — serial_number_required, warranty, composite barcodes** |
| **3** | **Module 7+8 Phase 2** | **Scan resolution service + useScanResolver hook** |
| 4 | Module 1 — Location Management | Can now use `useScanResolver` for location scans |
| **5** | **Module 7+8 Phase 4** | **Label printing — BarcodePrintDrawer (Phase 4 before Stock In so it's available during Module 2 work)** |
| 6 | Module 2 — Stock In | Integrates serial capture (Phase 3) and print prompt natively |
| **7** | **Module 7+8 Phase 3** | **Serial capture wired into StockInPanel (concurrent with or just after Module 2)** |
| 8 | Module 5 — Stock Reconciliation | Ghost inventory `useScanResolver` already wired from Phase 3 |
| 9 | Module 3 — Inter-Warehouse Transfer | `useScanResolver` already wired from Phase 3 |
| 10 | Module 6 — Supplementary | No barcode dependencies |
