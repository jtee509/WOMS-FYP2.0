# Frontend Development Progress

All frontend updates, changes, and new feature implementations are documented here. Each entry must state **what** was changed and **why**.

Format: `[PRE-ALPHA vX.Y.Z | YYYY-MM-DD HH:MM] — Brief title`

---

## Frontend Ground Rules

1. Document all updates in this file (`frontend-development-progress.md`)
2. Document all APIs in `web-api.md`
3. Version naming aligned with backend `PRE-ALPHA vX.Y.Z`
4. Comprehensive API testing for all endpoints
5. UI color templates unchanged unless explicitly approved
6. All errors logged in `frontend-error.md` (mark as fixed when resolved)
7. **File Organisation**: Every new page and ALL its page-specific items (sub-components, helpers, types) must live inside a dedicated subfolder under `src/pages/` (e.g., `src/pages/settings/SettingsPage.tsx`, `src/pages/settings/AttributeCard.tsx`). Create the subfolder if it does not yet exist. `src/components/` is strictly reserved for universal/shared components used across multiple pages (e.g., DataTable, PageHeader, Sidebar)
8. **Styling Standards**: All CSS must be in separate files — no inline styles or in-component style blocks
9. **Routing Configuration**: Use `BrowserRouter` for application routing
10. **Tailwind CSS**: Use Tailwind CSS v4 as the base styling framework — all new styling must use Tailwind utility classes. MUI `sx` prop and `.styles.ts` files are deprecated and will be migrated to Tailwind

---

## [PRE-ALPHA v0.11.0 | 2026-03-25] — Enhanced Stock-In Verification: Print → Scan → Reconcile

**What changed:**

Added full serialized item verification workflow to the Stock In (receiving) module. For items marked `is_serialized=true`, the receiving process now follows a Print → Scan → Reconcile loop instead of simple quantity counting: (1) Print labels generates unique StockLot barcodes with `pending_verification` status, (2) scanning each barcode transitions it to `verified`, (3) reconciliation gates session completion until all printed labels are accounted for.

### New Components
- `PrintLabelsModal.tsx` — Modal to generate N labels with quantity + location; displays barcodes for printing via `window.print()`
- `VoidScanModal.tsx` — Void a specific StockLot with mandatory reason selection (predefined list + custom)
- `ReconciliationPanel.tsx` — Per-line breakdown: printed / verified / pending (missing) / voided; auto-shown for sessions with serialized items
- `StockLotTable.tsx` — Expandable table of individual StockLot rows with status badges, timestamps, and void action; filterable by verification status
- `SerialScanFeedback.tsx` — Auto-dismissing success/duplicate/voided/error feedback after each serial scan

### New Types (`receiving.ts`)
- `StockLotRead`, `VerificationStatus`, `PrintLabelsRequest/Response`, `SerialScanResponse`, `VoidScanRequest`, `ReconciliationLine`, `ReconciliationReport`
- Added `is_serialized` to `ReceivingLineRead` and `ReceivingScanResponse`

### New API Functions (`receiving.ts`)
- `printLabels()`, `scanSerialBarcode()`, `voidStockLot()`, `getReconciliation()`, `listSessionLots()`

### Modified Components
- **`StockInPanel.tsx`** — Serialized lines show "Print" + "Lots" buttons instead of "Edit Count"; qty field disabled; serial scan feedback banner; reconciliation panel auto-rendered when session has serialized lines
- **`MovementItemRow.tsx`** — Quantity input disabled (grayed out) for serialized items with tooltip; `is_serialized` propagated from item selection
- **`MovementItemEntry`** type — Added optional `is_serialized` field

### Why
The previous workflow treated label printing as stock-in, causing inaccurate inventory for serialized items. This separates intent (print = "Pending Arrival") from action (scan = stock increase), blocks duplicate scans, requires void with reason instead of delete, and ensures only verified units count toward available stock.

---

## [PRE-ALPHA v0.10.0 | 2026-03-23] — Variation-Level Inventory Tracking & Barcode Resolution

**What changed:**

Added `variation_sku` and `variation_label` fields across all inventory-related frontend types to support per-variation stock tracking. Added `BarcodeResolution` type and `resolveBarcode()` API function for universal barcode lookup (item + SKU + variation barcode). Updated all `EMPTY_ENTRY` initializers and `MovementItemEntry` construction in 7 component files.

### New Types / API
- `api/base_types/items.ts` — `BarcodeResolution` interface (item_id, item_name, master_sku, barcode, variation_sku, variation_label, is_variation)
- `api/base/items.ts` — `resolveBarcode(barcode)` function

### Modified Types
- `api/base_types/warehouse.ts` — InventoryLevelEnrichedRead, MovementLineItem, MovementItemEntry, StockCheckLineRead, LocationSlotCreate/Read (all +variation_sku/label)
- `api/base_types/transfer.ts` — TransferLineCreate, TransferLineRead (+variation_sku/label)
- `api/base_types/receiving.ts` — ReceivingLineRead, ReceivingScanResponse (+variation_sku/label)
- `api/base_types/disposal.ts` — DisposalRequestCreate, DisposalApprovalRead (+variation_sku/label)

### Modified Components
- `MovementItemGrid.tsx`, `RecordMovementDrawer.tsx`, `InterWarehousePanel.tsx`, `ConditionPanel.tsx`, `CourierPanel.tsx` — updated EMPTY_ENTRY with variation fields
- `MovementItemRow.tsx` — onUpdate calls include variation_sku/label
- `hooks/useMovementStateMachine.ts` — MovementEntry + initial entry include variation fields

**Why:** Foundation for per-variation inventory. All types are now variation-aware; component UI for variation selection will follow in Phase 7 (Barcode Search & Scanning Enhancement).

---

## [PRE-ALPHA v0.9.7 | 2026-03-22] — Inter-Warehouse Transfer Enhancements

**What changed:**

Added packing confirmation gate, per-line discrepancy reasons, printable Transfer Order, incoming transfer schedule, and full transfer detail page with status timeline.

### New Files
- `pages/warehouse/inventory/transfers/TransferDetailPage.tsx` + `.css` — Full detail page with status timeline (Draft→Packed→Shipped→Received→Completed), lines table, action buttons (Ship, Receive, Cancel, Print TO), notes section, discrepancy report
- `pages/warehouse/inventory/transfers/PackingConfirmationStep.tsx` — Inline checklist card; all items must be checked to enable confirm button; optional packing notes
- `pages/warehouse/inventory/transfers/TransferPrintView.tsx` + `.css` — Printable Transfer Order with barcode (react-barcode), warehouse addresses, lines table with empty "Received" column for hand-writing, signature lines, @media print CSS
- `pages/warehouse/inventory/transfers/TransferDiscrepancyReport.tsx` — Structured discrepancy report table from JSONB snapshot; shows delta, status badges, human-readable reason labels
- `pages/warehouse/inventory/transfers/ReceiverSchedulePage.tsx` — Incoming transfer schedule for selected warehouse; DataTable with reference, from warehouse, status, shipped date, View/Receive actions

### Modified Files
- `pages/warehouse/inventory/TransferReceiptPage.tsx` — Added per-line discrepancy reason dropdowns (TRANSFER_DISCREPANCY_REASONS) for mismatched lines + receiver_notes textarea; passes discrepancy_reason per line in verifyTransfer and receiver_notes in completeTransfer
- `pages/warehouse/inventory/movements/InterWarehousePanel.tsx` — Added View button (→ detail page), Pack action for unpacked drafts, packing confirmed icon indicator on status badges
- `App.tsx` — Added 3 routes: `/inventory/transfers/:id` (TransferDetailPage), `/inventory/transfers/:id/print` (TransferPrintView), `/inventory/incoming` (ReceiverSchedulePage)

### API Changes
- `api/base_types/transfer.ts` — Added TRANSFER_DISCREPANCY_REASONS, TRANSFER_DISCREPANCY_LABELS, TransferPackingConfirmRequest, TransferPrintData; updated read interfaces with packing/discrepancy fields
- `api/base/transfer.ts` — Added confirmPacking(), getTransferPrintData(), getIncomingSchedule()

### Dependencies
- `react-barcode` — barcode rendering for Transfer Order print view

**Why:** Shipping without packing confirmation risked short-shipments. Free-text-only discrepancy notes prevented root-cause analysis. The printable Transfer Order creates a physical paper trail for warehouse operations. The incoming schedule gives receiving staff advance visibility of inbound transfers.

---

## [PRE-ALPHA v0.9.6 | 2026-03-21] — Ghost Inventory: Found Item Capture & Resolution in Stock Checks

**What changed:**

Added ghost inventory support to the stock check workflow. During physical counting, staff can now capture "found items" — inventory discovered at a location with no corresponding system record — via a slide-down form with item search, location picker, quantity, and notes. Ghost lines appear with distinctive amber styling (background + left border + "Found Item" badge) in the counting table. During reconciliation, a dedicated Ghost Inventory Resolution Panel lists all unresolved ghost items with per-line action selectors (Create Record / Flag for Review / Dispose). The "Adjust Inventory" button is blocked until all ghost items are resolved, matching the 409 ghost gate on the backend.

### New Files
- `frontend/src/pages/warehouse/inventory/stock_check/editor/GhostItemEntryForm.tsx` — Item search (debounced, 300ms) + location dropdown + quantity + notes; amber-themed dashed-border form; calls `captureGhostItems()` API
- `frontend/src/pages/warehouse/inventory/stock_check/editor/GhostItemBanner.tsx` — Inline amber badge for ghost lines showing "Found Item" label, found location code, resolution status, and truncated notes
- `frontend/src/pages/warehouse/inventory/stock_check/reconciliation/GhostItemActionSelect.tsx` — Styled dropdown with 3 options: Create Record (green), Flag for Review (amber), Dispose (red)
- `frontend/src/pages/warehouse/inventory/stock_check/reconciliation/GhostInventoryResolutionPanel.tsx` — Resolution table with progress indicator, batch resolve button, and all-resolved success banner

### Modified Files
- `frontend/src/api/base_types/warehouse.ts` — Added `GhostResolution` type, `GhostItemCapture`, `GhostItemBatchCapture`, `GhostResolutionAction`, `GhostResolutionBatch` interfaces; updated `StockCheckLineRead` with ghost fields
- `frontend/src/api/base/warehouse.ts` — Added `captureGhostItems()`, `resolveGhostItems()` API functions
- `frontend/src/pages/warehouse/inventory/stock_check/editor/EditorPage.tsx` — "Found Item" button in toolbar; `GhostItemEntryForm` slide-down on toggle; ghost lines get amber bg + left border + `GhostItemBanner` in item cell
- `frontend/src/pages/warehouse/inventory/stock_check/manager/ReconciliationPage.tsx` — `GhostInventoryResolutionPanel` above adjustment table; `hasUnresolvedGhosts` check blocks "Adjust Inventory" button; priority warning message for unresolved ghosts

---

## [PRE-ALPHA v0.9.5 | 2026-03-20] — Stock In Enhancements: Source Types, Unexpected Items, Discrepancy Gate

**What changed:**

Enhanced the inbound receiving workflow with three capabilities: (1) **Source type selector** — operators now choose whether an inbound session is a Supplier Shipment, Customer Return, or Inter-Warehouse Transfer at creation time, with color-coded toggle buttons. (2) **Unexpected item tracking** — items found during receiving that weren't on the expected manifest are flagged with an amber "Unexpected" badge in the lines table. (3) **Discrepancy resolution gate** — when a session has discrepancies (short/over/missing) or unexpected items, the "Complete" action returns a 409 error which triggers a modal where operators must acknowledge the discrepancies with resolution notes before the system allows completion.

### New Files
- `frontend/src/pages/warehouse/inventory/movements/StockInSourceSelector.tsx` — Toggle button group: Supplier Shipment (blue), Customer Return (amber), Inter-Warehouse (purple)
- `frontend/src/pages/warehouse/inventory/movements/DiscrepancyReportModal.tsx` — Full-screen modal with summary cards (matched/short/over/missing counts), discrepancy lines table, resolution notes textarea, accept & resolve action

### Modified Files
- `frontend/src/api/base_types/receiving.ts` — Added `ReceivingSourceType`, `UnexpectedLineCreate`, `DiscrepancyReportCreate`; updated session/line read/create types with new fields
- `frontend/src/api/base/receiving.ts` — Added `createUnexpectedLine()`, `submitDiscrepancyReport()` API functions
- `frontend/src/pages/warehouse/inventory/movements/StockInPanel.tsx` — Integrated source selector in create form; source type badge in detail header; "Source" column in list; unexpected badge on lines; 409 catch opens discrepancy modal; `showDiscrepancyModal` state

---

## [PRE-ALPHA v0.9.3 | 2026-03-18] — Stock Location Management (Functional Zones + Occupancy Grid)

**What changed:**

Added visual occupancy grid and server-side functional zone configuration. The occupancy grid provides a card-based overview of all warehouse bins with color-coded status badges (Empty/Reserved/Occupied/Full). Clicking a bin opens a slot management drawer where operators can view, assign, and remove item-to-location assignments. FunctionalZoneConfig was migrated from localStorage to the backend API.

### New Files
- `frontend/src/pages/warehouse/inventory/shared/LocationOccupancyBadge.tsx` — Badge component with 4 statuses
- `frontend/src/pages/warehouse/locations/LocationOccupancyGrid.tsx` — Card grid with filter tabs + search + click-to-open
- `frontend/src/pages/warehouse/locations/LocationSlotDrawer.tsx` — Slide-over panel for slot CRUD

### Modified Files
- `frontend/src/api/base_types/warehouse.ts` — Added `FunctionalZoneConfigCreate`, `FunctionalZoneConfigRead`, `OccupancyStatus`, `LocationOccupancyRead`
- `frontend/src/api/base/warehouse.ts` — Added `listFunctionalZones()`, `upsertFunctionalZones()`, `getLocationOccupancy()`
- `frontend/src/pages/warehouse/inventory/allocation/FunctionalZoneConfig.tsx` — Migrated from localStorage to API
- `frontend/src/pages/warehouse/locations/LocationAllocationPage.tsx` — Added "Visual Grid" view mode tab

---

## [PRE-ALPHA v0.9.2 | 2026-03-18] — Disposal Module (Remove Stock Approval Workflow)

**What changed:**

Full-stack implementation of the Disposal module — a two-step approval workflow for stock write-offs (damaged, expired, quality failure, obsolete, contaminated). Staff creates a disposal request, a manager approves or rejects (with optional quantity adjustment), and approved requests are executed to permanently remove stock via Write Off movements.

### New Files
- `frontend/src/api/base_types/disposal.ts` — TypeScript interfaces: `DisposalStatus`, `DisposalReason`, `DisposalRequestCreate`, `DisposalApproveAction`, `DisposalApprovalRead`
- `frontend/src/api/base/disposal.ts` — 7 API functions (create, list, getPending, getDetail, approve, execute, cancel)
- `frontend/src/pages/warehouse/inventory/disposal/DisposalListPage.tsx` — Main list page with DataTable, status filter tabs, pagination, live badge counts
- `frontend/src/pages/warehouse/inventory/disposal/DisposalRequestForm.tsx` — Create form with item search (debounced), location selector, quantity, reason dropdown, notes
- `frontend/src/pages/warehouse/inventory/disposal/DisposalDetailPage.tsx` — Detail view with audit trail, approve/reject/execute/cancel actions, qty edit on approval, reject modal

### Modified Files
- `frontend/src/pages/warehouse/inventory/shared/UnifiedStatusBadge.tsx` — Added `disposal` domain with 5 statuses (pending_approval, approved, rejected, disposed, cancelled)
- `frontend/src/pages/warehouse/inventory/operations/OperationsLandingPage.tsx` — Added "Remove Stock (Disposal)" card with live pending count badge
- `frontend/src/App.tsx` — 3 new routes: `/inventory/operations/disposal`, `/inventory/operations/disposal/new`, `/inventory/operations/disposal/:id`

### Routes
| Path | Component | Description |
|------|-----------|-------------|
| `/inventory/operations/disposal` | DisposalListPage | Disposal list with filters |
| `/inventory/operations/disposal/new` | DisposalRequestForm | Create new disposal request |
| `/inventory/operations/disposal/:id` | DisposalDetailPage | Detail + actions |

---

## [PRE-ALPHA v0.9.1 | 2026-03-18] — Stock In: Document Upload + Quick Stock-In Form

**What changed:**

Added two capabilities to the Stock In workflow: (1) document upload/management for receiving sessions and inventory movements, and (2) a Quick Stock In form for ad-hoc inbound stock recording without the full session lifecycle.

### New Files
- `frontend/src/pages/warehouse/inventory/movements/DocumentUploadZone.tsx` — Drag-drop file upload component (any type, 10MB limit, dual pending/attached modes)
- `frontend/src/pages/warehouse/inventory/movements/QuickStockInForm.tsx` — Simple stock-in form (location picker, item search + quantity table, document upload, uses existing movements/v2 Receipt endpoint)

### Modified Files
- `frontend/src/api/base_types/receiving.ts` — Added `ReceivingDocumentRead` interface; updated `ReceivingSessionDetailRead` to include `documents`
- `frontend/src/api/base/receiving.ts` — Added 5 document API functions (uploadSessionDocument, uploadMovementDocument, listSessionDocuments, listMovementDocuments, deleteReceivingDocument)
- `frontend/src/pages/warehouse/inventory/movements/StockInPanel.tsx` — Added `'quick'` view, "Quick Stock In" button in list header, DocumentUploadZone in session detail view, document upload/delete handlers, item line picker on create form (search + expected quantity table, sends `lines` to `ReceivingSessionCreate`)

### API Integration
- Document upload uses `multipart/form-data` via FormData
- Quick stock-in reuses `POST /warehouse/movements/v2` (Receipt type) — no new stock logic, just a frontend convenience form
- After movement creation, pending documents are uploaded to the movement

---

## [PRE-ALPHA v0.9.0 | 2026-03-18] — Bundle v2: Platform Decoupling + Variation-Level Components

**What changed:**

Complete rewrite of the Bundle module. Bundles are now platform-independent (no `platform_id`/`seller_id` required) and support variation-level components. A bundle component can reference either a whole item (`variation_sku: null`) or a specific variation within an item's JSONB (`variation_sku: "TSHIRT-RED-M"`). Orphaned variations (removed from parent item after bundle creation) are detected at read time and flagged in the UI.

### New Files
- `backend/app/models/items.py` — `BundleComponent` SQLModel class with `variation_sku`, `quantity`, `sort_order`
- `backend/alembic/versions/20260318_0000_00_q2r3s4t5u6v7_create_bundle_components_with_variations.py` — Migration creating `bundle_components` table

### Modified Files (Backend)
- `backend/app/models/__init__.py` — Registered `BundleComponent` import
- `backend/app/schemas/items.py` — Added variation fields to `BundleComponentInput`, `BundleComponentRead`; removed `platform_id`/`seller_id` from `BundleCreateRequest`; removed `listing_id`/`platform_sku` from `BundleReadResponse`
- `backend/app/routers/items.py` — Rewrote all 7 bundle endpoints to use `BundleComponent` instead of `PlatformSKU`/`ListingComponent`; added `_resolve_variation_info()`, `_build_components_read()`, `_validate_components()` helpers
- `backend/app/services/items_import/bundle_importer.py` — Updated to insert `BundleComponent` rows directly (removed platform/seller resolution)

### Modified Files (Frontend)
- `frontend/src/api/base_types/items.ts` — Updated `BundleComponentInput`, `BundleComponentRead`, `BundleCreateRequest`, `BundleReadResponse` types
- `frontend/src/pages/bundles/ComponentSearch.tsx` — Complete rewrite with inline variation picker; `excludeIds` → `excludeKeys` (composite `item_id:variation_sku`); exported `makeExcludeKey()` helper
- `frontend/src/pages/bundles/ComponentList.tsx` — Shows variation label beneath item name, variation barcode, orphaned warning badge
- `frontend/src/pages/bundles/BundleFormPage.tsx` — Handles `variation_sku` in add/edit; composite exclusion keys; removed `_existingListingId` state
- `frontend/src/pages/bundles/BundlesListPage.tsx` — Expanded rows show variation label, variation SKU, variation barcode, orphaned warning
- `frontend/src/pages/items/ItemsListPage.tsx` — Expanded component rows show variation details + barcode column

### Key Design Decisions
- **Variation reference by SKU**: Most stable identifier — unlike combo indexes (brittle on reorder) or value arrays (break on rename)
- **Orphan detection at read time**: Rather than blocking item updates, orphaned variations are flagged with `orphaned: true` and shown as warnings in the UI
- **UNIQUE constraint**: `(bundle_item_id, component_item_id, variation_sku)` with `NULLS NOT DISTINCT` — same item can appear as both whole-item and specific variation(s)

---

## [PRE-ALPHA v0.8.2 | 2026-03-16] — Inventory UX Simplification: 6 Nav Items → 3

**What changed:**

Simplified the entire inventory section from 6 sidebar nav items to 3 (Stock Overview, Operations, Stock Checks). Configuration pages (Allocation Rules, Alert Triggers, Data Export) moved to a new Settings → Inventory tab. All features preserved — no deletions.

### New Files
- `frontend/src/pages/warehouse/inventory/StockOverviewPage.tsx` — Unified dashboard: stock levels + alerts + activity timeline (3 collapsible sections)
- `frontend/src/pages/warehouse/inventory/operations/OperationsLandingPage.tsx` — Card-grid launcher for 4 operations with live count badges
- `frontend/src/pages/warehouse/inventory/operations/StockInPage.tsx` — Page shell wrapping StockInPanel
- `frontend/src/pages/warehouse/inventory/operations/StockOutPage.tsx` — Page shell wrapping StockOutPanel
- `frontend/src/pages/warehouse/inventory/operations/TransfersPage.tsx` — Page shell wrapping InterWarehousePanel + MovementHistoryTable
- `frontend/src/pages/warehouse/inventory/operations/AdjustmentsPage.tsx` — Page shell wrapping AdjustmentsPanel + MovementHistoryTable
- `frontend/src/pages/settings/InventorySettingsTab.tsx` — Settings tab with Allocation, Triggers, Export accordions

### Modified Files
- `frontend/src/components/layout/nav.config.tsx` — Inventory: 6 children → 3 (Stock Overview, Operations, Stock Checks)
- `frontend/src/App.tsx` — 8 new routes, 8 legacy redirects, updated imports
- `frontend/src/pages/settings/SettingsPage.tsx` — Added 'inventory' tab + useSearchParams for ?tab= URL support

### Routing Changes
| Old Route | New Route / Redirect |
|-----------|---------------------|
| `/inventory/levels` | → `/inventory` (Stock Overview) |
| `/inventory/movements` | → `/inventory/operations` (Operations Landing) |
| `/inventory/stock-check` | → `/inventory/stock-checks` |
| `/inventory/allocation` | → `/settings?tab=inventory` |
| `/inventory/triggers` | → `/settings?tab=inventory` |
| `/inventory/analytics` | → `/settings?tab=inventory` |

---

## [PRE-ALPHA v0.8.1 | 2026-03-16] — Inventory Workflow Restructure: Inbound/Outbound

**What changed:**

Restructured the Movement Hub from generic transaction types (Inter-Warehouse, Intra-Warehouse, Courier/Shipping, Condition-Based) to workflow-aligned tabs matching real warehouse operations: **Stock In**, **Stock Out**, Inter-Warehouse, **Adjustments**. Added backend ReceivingSession model for inbound goods verification. Fixed the 422 React crash bug.

### New Files
- `frontend/src/pages/warehouse/inventory/movements/StockInPanel.tsx` — Inbound receiving workflow (session list → create → barcode scan → count → complete)
- `frontend/src/pages/warehouse/inventory/movements/StockOutPanel.tsx` — Outbound fulfillment (pending orders → pick list → stock verification → ship)
- `frontend/src/pages/warehouse/inventory/movements/AdjustmentsPanel.tsx` — Merged bin-to-bin + condition adjustments with mode toggle
- `frontend/src/api/base_types/receiving.ts` — TypeScript types for receiving API
- `frontend/src/api/base/receiving.ts` — API functions for receiving endpoints

### Modified Files
- `frontend/src/pages/warehouse/inventory/movements/MovementHubPage.tsx` — New tab config (stock_in, stock_out, inter_warehouse, adjustments)
- `frontend/src/pages/warehouse/inventory/hooks/useMovementStateMachine.ts` — Updated MovementCategory type
- `frontend/src/pages/warehouse/inventory/shared/UnifiedStatusBadge.tsx` — Added receiving + receiving_line domains
- `frontend/src/api/base/client.ts` — Fixed 422 error normalization (Pydantic validation objects → readable string)

### Backend (new)
- `backend/app/models/receiving.py` — ReceivingSession, ReceivingLine models
- `backend/app/schemas/receiving.py` — Pydantic schemas
- `backend/app/routers/receiving.py` — 10 REST endpoints (CRUD + lifecycle + barcode scan + discrepancy report)
- `backend/alembic/versions/20260316_0100_00_..._add_receiving_session_tables.py` — Migration

### Why
The previous tab structure was developer-centric (organized by data flow type) rather than user-centric (organized by business process). The user's actual workflow is:
1. **Inbound**: Goods arrive → verify against expected list → scan barcodes → record stock in → items live in system
2. **Outbound**: Orders received → pick list → verify stock → minus stock → ship

This restructure aligns the UI with those two core processes.

---

## [PRE-ALPHA v0.8.0 | 2026-03-16] — Stock Check (Cycle Count) V2 — Full Redo

**What changed:**

Complete redo of the stock check module — decomposed the monolithic 935-line `StockCheckDetailPage` into a status-driven shell with 3 role-specific sub-pages, added re-count workflow, persisted multi-level approvals, manual inventory adjustments, and full audit trail.

### New Files

**Shell & Shared:**
- `pages/warehouse/inventory/stock_check/StockCheckDetailShell.tsx` — Route component: fetches data, renders DraftView / EditorPage / ApproverPage / ReconciliationPage / ArchiveView based on status
- `pages/warehouse/inventory/stock_check/StockCheckDetailShell.css` — Focus mode styles
- `pages/warehouse/inventory/stock_check/shared/ConfirmationModal.tsx` — Reusable dangerous-action confirmation with danger/warning/info variants
- `pages/warehouse/inventory/stock_check/shared/VarianceFooterBar.tsx` — Sticky footer with real-time totals (counted/total, variance count, surplus/shortage/net)
- `pages/warehouse/inventory/stock_check/shared/LineHistoryDrawer.tsx` — Per-line audit trail slide-out with timeline view

**Editor (Counter's Workspace):**
- `pages/warehouse/inventory/stock_check/editor/EditorPage.tsx` — Barcode scanning, progressive disclosure, blind count mode, guided count mode (one-item-at-a-time cards), re-count mode (flagged lines only, blind), focus mode, section filtering, audio feedback, save/submit
- `pages/warehouse/inventory/stock_check/editor/DiscrepancyReasonSelect.tsx` — Dropdown with human-readable reason code labels
- `pages/warehouse/inventory/stock_check/editor/RecountBanner.tsx` — Purple banner for re-count mode

**Approver (Review Portal):**
- `pages/warehouse/inventory/stock_check/approver/ApproverPage.tsx` — Exception-first filter, approval chain panel (L1/L2/L3 from DB), cost impact column, bulk actions (approve zero-variance, flag for re-count), line history drawer

**Manager (Reconciliation):**
- `pages/warehouse/inventory/stock_check/manager/ReconciliationPage.tsx` — Per-line final_accepted_qty + discrepancy reason (required for non-zero), summary panel (inbound/outbound/net), confirmation checkbox + modal, two-step API (reconcileLines → adjustInventory)

### Modified Files
- `pages/warehouse/inventory/shared/UnifiedStatusBadge.tsx` — Added `recount_requested` status (purple)
- `pages/warehouse/inventory/StockCheckListPage.tsx` — Added `recount_requested` status tab, `blind_count_enabled` toggle in create modal, Mode column in table
- `App.tsx` — Route `/inventory/stock-check/:id` now points to `StockCheckDetailShell`
- `api/base_types/warehouse.ts` — 12+ new interfaces/types for V2 (approvals, history, thresholds, recount, reconcile)
- `api/base/warehouse.ts` — 8 new API functions (submitApproval, requestRecount, submitRecounts, reconcileLines, adjustInventory, getStockCheckHistory, getThresholdConfig, updateThresholdConfig)

**Why:** The original stock check page was a single monolithic component handling counter, approver, and manager workflows with no re-count support, no persisted approvals, no audit trail, no structured discrepancy reasons, and auto-reconciliation without manager verification. This redo provides professional-grade cycle count functionality with role separation, data integrity (blind counts, progressive disclosure), and full traceability.

---

## [PRE-ALPHA v0.7.1 | 2026-03-16] — Variation Barcodes + Bundle Component Barcode Display

**What changed:**

Extended barcode support to item variations and bundle component displays.

- `VariationBuilder.types.ts`: Added `barcode: string | null` to `VariationCombination` interface
- `VariationBuilder.utils.ts`: Updated `syncCombinations()` and `migrateOldFormat()` to handle barcode field
- `VariationBuilder.tsx`: Added read-only Barcode column in CombinationTable — shows monospace barcode or "Auto-generated" placeholder
- `base_types/items.ts`: Added `barcode: string | null` to `BundleComponentRead` interface
- `BundlesListPage.tsx`: Added Barcode column in expanded component rows
- `BundleFormPage.tsx`: Passes barcode from API response and search results to ComponentList
- `ComponentList.tsx`: Added `barcode` to `ComponentRow` interface + Barcode column in table

**Why:** Variation combinations needed individual barcodes for warehouse scanning/picking. Bundle component lists needed to show each item's barcode for order fulfillment visibility.

---

## [PRE-ALPHA v0.7.0 | 2026-03-16] — Inventory Management System Overhaul

**What changed:**

Complete architectural overhaul of the inventory management section, transforming disconnected pages into a unified warehouse orchestration system across 7 implementation phases.

### Phase 0 — Foundation (shared hooks & utilities)
- `useGlobalBarcodeListener` hook: HID keyboard barcode scanner detection via inter-character latency (<50ms for 10+ chars), auto-skip for focused form fields
- `useMovementStateMachine` hook: typed `useReducer` FSM with states Idle→SelectingType→AddingItems→Reviewing→Submitting→Success→Error
- `useVirtualizedList` hook: thin wrapper around `react-window` FixedSizeList with scrollToIndex/scrollToBottom
- `UnifiedStatusBadge`: consolidated status badge component replacing 4+ duplicated STATUS_BADGE maps (supports domains: stock, transfer, stock_check, movement, alert, approval)
- `extractErrorMessage`: shared error extraction utility (was duplicated in 6+ files)
- Added `react-window` + `@types/react-window` dependencies

### Phase 1 — Navigation & Route Restructure
- Sidebar restructured: Stock Levels, Stock Movements (Movement Hub), Reconciliation (Stock Check), Auto-Allocation, Alert Triggers, History & Analytics
- Removed standalone "Transfers" nav item (absorbed into Movement Hub)
- Legacy route redirects: `/inventory/transfers` → `/inventory/movements?tab=inter_warehouse`, `/inventory/alerts` → `/inventory/triggers`

### Phase 2 — Movement Hub (unified 4-tab interface)
- `MovementHubPage`: tabbed interface with URL-driven tab state (`?tab=inter_warehouse`)
- `InterWarehousePanel`: full IWT management with transfer list, direction/status filters, ship/receive/cancel actions, collapsible create form
- `IntraWarehousePanel`: 6-phase continuous scan workflow (scan_source→scan_items→scan_destination→review→submit→success), barcode-driven, auto-detects location codes vs item SKUs
- `CourierPanel`: outbound shipment manifest with multi-select, global action bar (Ship/Cancel Selected), create form
- `ConditionPanel`: condition type cards (Damaged/Repair/Scrap/Write-Off) with predefined reason codes, photo evidence upload with preview
- `MovementHistoryTable`: unified movement history with type filter and UnifiedStatusBadge

### Phase 3 — Reconciliation Enhancements
- `BlindCountToggle`: hides system_quantity and variance columns during counting to prevent bias, persists preference in localStorage
- `ABCClassBadge`: A/B/C inventory classification badges (A=red/weekly, B=amber/monthly, C=emerald/quarterly) with `computeABCClass()` utility
- `ApprovalGate`: multi-level approval UI (L1 Supervisor → L2 Manager for net variance ≥10 → L3 Finance for net variance ≥50), approval chain visualization, Approve & Reconcile / Request Re-count buttons
- `VarianceSummaryPanel`: visual variance summary with positive/negative/net totals, accepted/rejected line counts, grouped by warehouse section
- `StockCheckDetailPage` integrated: blind count toggle, ABC badges on item cells, variance summary panel + approval gate replace old reconcile modal
- `StockCheckListPage` enhanced: status filter tabs with counts, replaced duplicated STATUS_BADGE/STATUS_LABEL with UnifiedStatusBadge
- Both pages now use shared `extractErrorMessage` instead of inline duplicates

### Phase 4 — Auto-Allocation Rule Builder
- `AllocationRulePage`: 3-tab page (Allocation Rules, Functional Zones, Affinity Slotting)
- `AllocationRuleBuilder`: trigger-action rule paradigm (triggers: ABC class, item category, weight range, item type; actions: assign zone, assign location, set primary, set max qty), CRUD with enable/disable/duplicate, localStorage persistence
- `FunctionalZoneConfig`: 6 predefined functional zones (Returns, Shipping, Transit, Golden Zone, Quarantine, Bulk Storage), section/zone mapping via chip toggles
- `AffinitySlottingPanel`: co-occurrence visualization placeholder with sample data structure (requires backend analysis pipeline)

### Phase 5 — Alert Triggers Configuration
- `AlertTriggersPage`: two-panel layout (config left, alerts right)
- `TriggerConfigPanel`: per-item/group threshold config (low stock, critical, overstock, inactivity), scope selection (global/category/item), enable/disable toggles, localStorage persistence
- `AlertDashboard`: live alert feed from backend API, severity-grouped collapsible sections, quick-resolve with notes input, resolved alerts history toggle

### Phase 6 — History & Analytics
- `AnalyticsPage`: 3-tab segmented control (Timeline, Trends, Export)
- `EventTimeline`: unified chronological stream combining movements, stock checks, transfers, and alerts with kind-based filtering, vertical timeline with color-coded dots and UnifiedStatusBadge
- `TrendCharts`: d3-powered bar chart (movement volume by type) + horizontal bar chart (stock check variance counts), responsive SVG viewBox
- `DataExportPanel`: CSV export for movements/stock checks/transfers, ML-ready format (ISO 8601 timestamps, quoted fields, UTF-8), last export result indicator

**Why:** The inventory section consisted of disconnected pages with duplicated utility code and inconsistent UX patterns. This overhaul creates a unified, state-machine-driven system with centralized status display, shared utilities, barcode-first workflows, and analytics — preparing the platform for high-throughput warehouse operations.

**New files (33):**
- `pages/warehouse/inventory/hooks/` — useGlobalBarcodeListener.ts, useMovementStateMachine.ts, useVirtualizedList.ts
- `pages/warehouse/inventory/shared/` — UnifiedStatusBadge.tsx, extractErrorMessage.ts
- `pages/warehouse/inventory/movements/` — MovementHubPage.tsx/.css, InterWarehousePanel.tsx, IntraWarehousePanel.tsx, CourierPanel.tsx, ConditionPanel.tsx, MovementHistoryTable.tsx
- `pages/warehouse/inventory/reconciliation/` — BlindCountToggle.tsx, ABCClassBadge.tsx, ApprovalGate.tsx, VarianceSummaryPanel.tsx
- `pages/warehouse/inventory/allocation/` — AllocationRulePage.tsx, AllocationRuleBuilder.tsx, FunctionalZoneConfig.tsx, AffinitySlottingPanel.tsx
- `pages/warehouse/inventory/triggers/` — AlertTriggersPage.tsx (rewritten), TriggerConfigPanel.tsx, AlertDashboard.tsx
- `pages/warehouse/inventory/analytics/` — AnalyticsPage.tsx (rewritten), EventTimeline.tsx, TrendCharts.tsx, DataExportPanel.tsx

**Modified files:**
- `App.tsx` — Updated routes for Movement Hub, Allocation, Triggers, Analytics; removed unused imports
- `nav.config.tsx` — Restructured Inventory sidebar section
- `StockCheckDetailPage.tsx` — Integrated blind count, ABC badges, variance summary, approval gate
- `StockCheckListPage.tsx` — Added status filter tabs, shared utilities
- `package.json` — Added react-window + @types/react-window

---

## [PRE-ALPHA v0.6.5 | 2026-03-16] — Items Barcode Auto-Generation Integration

**What changed:**

1. **Barcode column in ItemsListPage** — Added a "Barcode" column to the items DataTable, positioned after the Item column. Displays the system-generated barcode in monospace text, or "—" when null (no convention active).

2. **Read-only barcode display in ItemFormPage** — In edit mode, when an item has a barcode, a read-only field is shown above the form fields with monospace styling and a "System-generated. Cannot be changed." helper. Hidden in create mode and when barcode is null.

3. **TypeScript type update** — Added `barcode: string | null` to the `ItemRead` interface in `base_types/items.ts`. `BundleListItem` inherits it automatically via `extends ItemRead`.

**Files modified:**
- `frontend/src/api/base_types/items.ts` — added barcode field to ItemRead
- `frontend/src/pages/items/ItemsListPage.tsx` — added Barcode column
- `frontend/src/pages/items/ItemFormPage.tsx` — added barcode state + read-only display

---

## [PRE-ALPHA v0.6.4 | 2026-03-15] — Scan-to-Verify: Inter-Warehouse Transfers + Focus Mode

**What changed:**

1. **Inter-Warehouse Transfer UI** — Added full transfer workflow to the inventory module:
   - `RecordMovementDrawer` extended: selecting "Inter-Warehouse Transfer" movement type shows a target warehouse picker (instead of destination location), calls `createTransfer()` to create a draft, and displays the generated reference number with a copy button. Stock is NOT deducted at this stage.
   - New `TransferListPage` (`/inventory/transfers`): paginated list of transfers using DataTable with direction (outgoing/incoming) and status filters. Status-based action buttons: Ship/Cancel for outgoing drafts, Receive for incoming shipped transfers.
   - New `TransferReceiptPage` (`/inventory/transfers/receive`): two-phase scan-to-verify flow. Phase 1: scan transfer reference barcode to load manifest. Phase 2: scan individual item barcodes with real-time expected-vs-scanned comparison grid. Discrepancy detection with mandatory notes for mismatches.
   - Supporting components: `VerificationGrid` (expected vs scanned table with delta column), `TransferManifestHeader` (transfer metadata display), `DiscrepancyBadge` (color-coded status pills for matched/short/over/missing/extra).

2. **Stock Check Focus Mode** — Enhanced `StockCheckDetailPage`:
   - Toggle button (Fullscreen icon) in header, visible only during `in_progress` status
   - Adds `focus-mode` CSS class to `document.body` → hides sidebar + app header, dark background (#111827), enlarged fonts, high-contrast badges
   - Audio feedback via Web Audio API: `playSuccess()` on barcode match, `playError()` on no match
   - Dynamic re-sorting: last scanned item sorts to top, then uncounted, then counted
   - Progress bar indicator below barcode scanner

3. **API Layer** — New `frontend/src/api/base_types/transfer.ts` (TypeScript interfaces) and `frontend/src/api/base/transfer.ts` (8 API functions: createTransfer, listTransfers, getTransfer, getTransferByReference, shipTransfer, verifyTransfer, completeTransfer, cancelTransfer).

4. **Audio Utility** — `audioFeedback.ts`: Web Audio API with lazy AudioContext creation. `playSuccess()` (800Hz sine, 150ms), `playError()` (200Hz square, 300ms), `playConfirm()` (600Hz sine, 100ms).

5. **Routing & Navigation** — Added routes in `App.tsx` for `/inventory/transfers` and `/inventory/transfers/receive`. Added "Transfers" nav item under Inventory section in `nav.config.tsx` with `LocalShippingIcon`.

**Why:** The warehouse had no mechanism for inter-site stock transfers with manifest verification. Staff needed a way to create transfer drafts, ship them (deducting source stock), and verify receipt at the destination with barcode scanning and discrepancy detection. Focus Mode addresses the need for distraction-free rapid scanning during stock checks.

### New files
| File | Purpose |
|------|---------|
| `src/api/base_types/transfer.ts` | Transfer TypeScript interfaces |
| `src/api/base/transfer.ts` | 8 transfer API functions |
| `src/pages/warehouse/inventory/TransferListPage.tsx` | Transfer list/dashboard |
| `src/pages/warehouse/inventory/TransferReceiptPage.tsx` | Scan-to-verify receipt page |
| `src/pages/warehouse/inventory/VerificationGrid.tsx` | Expected vs Scanned table |
| `src/pages/warehouse/inventory/TransferManifestHeader.tsx` | Transfer metadata display |
| `src/pages/warehouse/inventory/DiscrepancyBadge.tsx` | Status badge component |
| `src/pages/warehouse/inventory/audioFeedback.ts` | Web Audio beep/buzz utility |
| `src/pages/warehouse/inventory/StockCheckDetailPage.css` | Focus mode styles |

### Modified files
| File | Change |
|------|--------|
| `src/pages/warehouse/inventory/RecordMovementDrawer.tsx` | Inter-warehouse transfer mode (target warehouse picker, draft creation, reference display) |
| `src/pages/warehouse/inventory/StockCheckDetailPage.tsx` | Focus mode toggle, audio feedback, dynamic re-sorting, progress bar |
| `src/App.tsx` | Two new routes for transfers |
| `src/components/layout/nav.config.tsx` | Transfers nav item under Inventory |

---

## [PRE-ALPHA v0.6.1 | 2026-03-14] — Frontend File Reorganization

**What changed:** Reorganized all frontend page files to be grouped by function in dedicated subfolders under `src/pages/`. Seven root-level pages moved into domain subfolders: `LoginPage` → `pages/auth/`, `DashboardPage` → `pages/dashboard/`, `MLSyncPage` + `ReferencePage` → `pages/data/`, `NotFoundPage` → `pages/errors/`, `PlaceholderPage` → `pages/common/`, `OrderImportPage` → `pages/orders/`. Four dashboard card components (`StatCard`, `OrderOverviewCard`, `PlatformDistributionCard`, `RecentImportsCard`) moved from `components/dashboard/` to `pages/dashboard/` since they are only used by DashboardPage. Split `pages/warehouse/` into two subfolders: `warehouse/locations/` (LocationSetupPage, LocationGeneratorPage, LocationAllocationPage + location_generator/ sub-components) and `warehouse/inventory/` (InventoryLevelsPage, InventoryMovementsPage, InventoryAlertsPage, StockCheckListPage, StockCheckDetailPage, RecordMovementDrawer, MovementItemGrid, MovementItemRow, StockStatusBadge). Deleted 3 orphaned files: `pages/warehouse/WarehouseSelector.tsx`, `pages/warehouse/WarehouseListPage.tsx`, `components/hooks/useD3.ts`. Updated all import paths in App.tsx and all moved files. TypeScript compilation passes cleanly.

**Why:** The project's file organization rule (Ground Rule #7) requires every page and its page-specific sub-components to live inside a dedicated subfolder. Root-level pages violated this rule. The warehouse folder mixed two distinct domains (location management vs inventory operations) making it harder to navigate. Dashboard components in `components/` were only used by one page, violating the shared-only principle for `components/`.

### File structure after reorganization
```
pages/
  auth/LoginPage.tsx
  dashboard/DashboardPage.tsx, StatCard.tsx, OrderOverviewCard.tsx, PlatformDistributionCard.tsx, RecentImportsCard.tsx
  data/MLSyncPage.tsx, ReferencePage.tsx
  errors/NotFoundPage.tsx
  common/PlaceholderPage.tsx
  orders/OrderImportPage.tsx (+ existing OrderDetailsPage, MassShipPage, etc.)
  warehouse/locations/LocationSetupPage.tsx, LocationGeneratorPage.tsx, LocationAllocationPage.tsx, location_generator/...
  warehouse/inventory/InventoryLevelsPage.tsx, InventoryMovementsPage.tsx, InventoryAlertsPage.tsx, StockCheck*, RecordMovementDrawer.tsx, MovementItem*.tsx, StockStatusBadge.tsx
  admin/, bundles/, items/, settings/ (unchanged)
```

---

## [PRE-ALPHA v0.6.0 | 2026-03-14] — Stock Movement Drawer, Stock Check Pages & Location Allocation

**What changed:** Three major warehouse UI features implemented. (1) **Multi-Item Movement Drawer**: Replaced the single-item movement modal in InventoryMovementsPage with a 520px slide-over `RecordMovementDrawer`. The drawer dynamically configures source/destination fields based on movement type (Receipt, Shipment, Transfer, Adjustment, Return, Write Off) via a `TYPE_CONFIG` mapping. Includes a `MovementItemGrid` with dynamic add/remove rows, each powered by `MovementItemRow` — a debounced (300ms) item autocomplete that fetches inventory at the source location for outbound movements or all items for inbound, showing available stock badges and quantity validation. Destination dropdown now shows "(Assigned)" hints for locations with active slot assignments. (2) **Stock Check (Cycle Count) Pages**: `StockCheckListPage` with DataTable pagination, status-colored badges (draft=gray, in_progress=blue, pending_review=amber, completed=green, cancelled=red), create modal with scope filters (section/zone/aisle/bay populated from location data), and row actions (Start/Cancel/View per status). `StockCheckDetailPage` with header info panel (stats chips for lines/counted/variance/dates), inline-editable counting grid (number inputs with blur/enter save, batch "Save All" button), variance review mode with per-line accept/reject toggles + bulk Accept All/Reject All, and reconcile confirmation modal. (3) **Location Allocation Page**: `LocationAllocationPage` with dual view toggle (By Location / By Item). By Location: location dropdown → table of assigned items with capacity utilization bars (green <70%, amber 70-90%, red >90%), primary star icons, edit/remove actions. By Item: debounced search → table of assigned locations. Assign modal with item search + location select + primary/priority/max_qty/notes. Edit modal for updating slot properties. Delete with stock-present blocking.

**Why:** The single-item movement modal was a bottleneck for warehouse staff processing bulk receipts/shipments — each item required a separate form submission. Stock verification had no structured workflow, making it impossible to audit physical vs. system discrepancies. Without location allocation, items could be placed anywhere with no capacity control or designated home locations.

### New files
| File | Purpose |
|------|---------|
| `pages/warehouse/RecordMovementDrawer.tsx` | 520px slide-over drawer for multi-item movements |
| `pages/warehouse/MovementItemGrid.tsx` | Dynamic item row grid with add/remove |
| `pages/warehouse/MovementItemRow.tsx` | Item autocomplete with stock lookup |
| `pages/warehouse/StockCheckListPage.tsx` | Stock check list with DataTable + create modal |
| `pages/warehouse/StockCheckDetailPage.tsx` | Detail page: counting grid + variance review + reconcile |
| `pages/warehouse/LocationAllocationPage.tsx` | Dual-view allocation management |

### Modified files
| File | Change |
|------|--------|
| `api/base_types/warehouse.ts` | Added 15+ types: StockCheck*, LocationSlot*, Movement v2 |
| `api/base/warehouse.ts` | Added 16 API functions for stock-check, slots, capacity |
| `pages/warehouse/InventoryMovementsPage.tsx` | Replaced modal with RecordMovementDrawer |
| `App.tsx` | Added routes: /inventory/stock-check, /inventory/stock-check/:id, /inventory/allocation |
| `components/layout/nav.config.tsx` | Added "Location Allocation" nav item under Inventory |

---

## [PRE-ALPHA v0.5.50 | 2026-03-14] — Unified Location Generator Interface

**What changed:** Complete rewrite of the Site Generator page (`LocationGeneratorPage.tsx`) into a streamlined single-view interface. Left panel is now a pure configuration sidebar (`ConfigPanel`) with checkbox-driven level cards for bulk generation — no splash screen, no Existing/New toggle, no review step. Right panel is a unified editable table (`UnifiedLocationTable`) that shows all locations (saved from DB + staged from generator) in a single view. Features: inline cell editing (transparent inputs with focus ring), row-level trash/undo actions, "Add Row" button per section, real-time duplicate detection with red highlight and warning tooltips, status-based row styling (saved=neutral, staged=blue, edited=amber, deleted=red strikethrough), and a sticky `CommitBar` that appears when pending changes exist. Save All executes sequential API calls: create staged → update edited → soft-delete deleted → refresh. `BulkCreationWizard.tsx` left untouched for `LocationManagementSection` in Settings.

**Why:** The previous design had a split personality — BulkCreationWizard managed its own location tables, edit mode, drawers, and staging in the left panel, while the right panel showed a separate read-only view. This made the workflow disjointed and required users to mentally track state across two panels. The unified interface provides a single source of truth with all editing native to table rows.

### New files
| File | Purpose |
|------|---------|
| `pages/warehouse/location_generator/types.ts` | `UnifiedLocationRow`, `RowStatus`, conversion helpers |
| `pages/warehouse/location_generator/helpers.ts` | `PreviewLocation`, `locationCode`, generator logic |
| `pages/warehouse/location_generator/ConfigPanel.tsx` | Left sidebar: level cards + create button |
| `pages/warehouse/location_generator/SectionAccordion.tsx` | Section accordion with editable rows + actions |
| `pages/warehouse/location_generator/CommitBar.tsx` | Sticky bottom bar: save/discard + summary |
| `pages/warehouse/location_generator/UnifiedLocationTable.tsx` | Right panel: filter + stats + accordions |

### Modified files
| File | Change |
|------|--------|
| `pages/warehouse/LocationGeneratorPage.tsx` | Full rewrite: unified state, new component imports |

---

## [PRE-ALPHA v0.7.0 | 2026-03-11] — Order Details & Mass Ship Pages

**What changed:** Built two fully functional pages for the Orders section. **Order Details** (`/orders/details`): paginated order list with DataTable integration, search (debounced), multi-filter bar (platform, store, status, date range), checkbox row selection for bulk actions, and a 680px slide-out `OrderViewDrawer` showing customer/shipping/financial info cards, line items table (SKU extraction from platform_sku_data JSONB), and collapsible raw platform data viewer. Created `OrderStatusBadge`, `FulfillmentStatusBadge`, and `PlatformBadge` components for consistent status/platform rendering across all order views. **Mass Ship** (`/orders/mass-ship`): 3-step wizard — (1) ShipmentSelectionStep with filter+table+checkbox selection, pre-filtered to "processing" orders; (2) TrackingAssignmentStep with editable courier/tracking table, bulk courier assignment, paste-column support, duplicate tracking detection; (3) ReviewConfirmStep with summary cards (totals by platform/courier), manifest table, and confirm button with loading state. Post-submit summary shows success/fail counts and error details. Cross-linked: selecting orders in Order Details and clicking "Ship Selected" navigates to Mass Ship with pre-selection. Backend enhanced: `GET /orders` now JOINs Platform/Seller for platform_name/store_name, aggregates detail_count/total_paid, supports date_from/date_to/assigned_warehouse_id/sort_by/sort_dir params. Added `POST /orders/bulk-ship` endpoint for atomic mass fulfillment.

**Why:** Staff needed a way to browse, search, and inspect orders from the frontend (previously only placeholder pages existed). Mass shipping is a critical daily operation — processing dozens of orders individually is impractical. The 3-step wizard ensures tracking numbers are assigned before shipping, preventing errors. The enriched list endpoint reduces N+1 lookups. The drawer pattern (matching inventory movements) keeps list context visible while inspecting details.

### New files
| File | Purpose |
|------|---------|
| `pages/orders/OrderDetailsPage.tsx` | Order list page with filters, table, drawer |
| `pages/orders/OrderDetailsPage.css` | Page-specific styles |
| `pages/orders/OrderViewDrawer.tsx` | Slide-out order detail panel |
| `pages/orders/OrderViewDrawer.css` | Drawer animation and layout styles |
| `pages/orders/OrderLineItemsTable.tsx` | Line items sub-table for drawer |
| `pages/orders/OrderStatusBadge.tsx` | Order status + cancellation badge |
| `pages/orders/FulfillmentStatusBadge.tsx` | Fulfillment status badge |
| `pages/orders/PlatformBadge.tsx` | Platform identity badge (SHP/LZD/TIK/MAN) |
| `pages/orders/OrderFilters.tsx` | Filter bar component |
| `pages/orders/OrderFilters.css` | Filter bar styles |
| `pages/orders/MassShipPage.tsx` | Mass ship 3-step wizard |
| `pages/orders/MassShipPage.css` | Wizard styles |
| `pages/orders/ShipmentSelectionStep.tsx` | Step 1: select orders |
| `pages/orders/TrackingAssignmentStep.tsx` | Step 2: assign tracking |
| `pages/orders/ReviewConfirmStep.tsx` | Step 3: review & confirm |

### Modified files
| File | Change |
|------|--------|
| `api/base_types/orders.ts` | Full order type definitions (status unions, interfaces, payloads) |
| `api/base/orders.ts` | listOrders, getOrder, updateOrder, updateOrderDetail, bulkShipOrders |
| `App.tsx` | Registered OrderDetailsPage and MassShipPage routes |

---

## [PRE-ALPHA v0.6.9 | 2026-03-11] — Phase 3 Complete: Inventory Intelligence & Analytics (Steps 3.0–3.7)

**What changed:** Built the complete inventory analytics and intelligence layer. Created `useInventorySync` — a custom hook that invalidates all inventory-related React Query caches (levels, alerts, movements, analytics) after any mutation, ensuring cross-view data consistency. Enhanced `InventoryLevelsPage` with stock-status row colouring (ROW_TINT map: low=yellow, critical=red, out_of_stock=gray, overstock=blue) and `InlineNumberCell` — a click-to-edit component for threshold fields (reorder_point, safety_stock, max_stock) that flashes green on successful save. Added `rowClassName` prop to the shared `DataTable` component for dynamic per-row CSS class injection. Built 4 analytics chart components: `DailyMovementChart` (d3 stacked bar), `MovementTypeBreakdown` (d3 donut with legend), `TopMovedItemsList` (Tailwind ranked list with progress bars), `StockHealthSummary` (d3 donut with centre total). Created `InventoryAnalyticsPage` with a 2x2 chart grid, date-range selector (presets: 7d/30d/90d/YTD/Custom), 3 parallel `useQuery` calls via TanStack React Query, loading skeletons, and empty states. Added "Analytics" nav entry and route under Inventory section. Backend gained 3 analytics endpoints and a PATCH endpoint for inline threshold editing.

**Why:** Phases 1–2 gave staff the tools to record and manage movements, but the system offered no aggregated insights or self-service threshold management. Warehouse operators had to ask a developer to change reorder points, and managers had no charts to spot trends. Inline editing removes the developer bottleneck for threshold changes. The analytics dashboard provides movement trends, item ranking, type distribution, and stock health at a glance — critical for demand planning and spotting operational problems before they escalate.

### New files
- `frontend/src/pages/warehouse/useInventorySync.ts` — Custom hook: calls `queryClient.invalidateQueries()` for inventory-levels, inventory-alerts, inventory-movements, inventory-analytics keys. Used in RecordMovementDrawer, MovementActionMenu, InventoryAlertsPage to keep all views consistent after mutations.
- `frontend/src/pages/warehouse/DailyMovementChart.tsx` — d3 stacked bar chart: X-axis = date, Y-axis = movement count, colour-coded by movement type. Responsive SVG with hover tooltips.
- `frontend/src/pages/warehouse/MovementTypeBreakdown.tsx` — d3 donut chart with percentage legend showing proportion of each movement type (Receipt, Shipment, Transfer, etc.) over the selected date range.
- `frontend/src/pages/warehouse/TopMovedItemsList.tsx` — Pure Tailwind ranked list: displays top N items by total quantity moved, with relative-width progress bars for visual comparison.
- `frontend/src/pages/warehouse/StockHealthSummary.tsx` — d3 donut chart: segments coloured to match `StockStatusBadge` palette (healthy=green, low=yellow, critical=red, out_of_stock=gray, overstock=blue); centre label shows total item count.
- `frontend/src/pages/warehouse/InventoryAnalyticsPage.tsx` — Full analytics dashboard page: 2x2 responsive grid with 4 chart cards, date-range selector with preset buttons (7d, 30d, 90d, YTD, Custom with date inputs), 3 parallel `useQuery` calls (movements-per-day, top-items, stock-health), loading skeletons per card, empty-state messages, warehouse selection guard.

### Modified files
- `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` — Stock-status row colouring via `rowClassName` prop (ROW_TINT map); `InlineNumberCell` click-to-edit for reorder_point, safety_stock, max_stock with green flash animation on save; integrated `useInventorySync`
- `frontend/src/components/common/DataTable.tsx` — Added `rowClassName` prop: accepts a function `(row) => string` returning CSS classes for dynamic per-row styling
- `frontend/src/api/base_types/warehouse.ts` — Added types: `MovementPerDay`, `TopMovedItem`, `StockHealthEntry`, `AnalyticsDateRange`, `InventoryLevelUpdatePayload`
- `frontend/src/api/base/warehouse.ts` — Added functions: `getMovementsPerDay()`, `getTopItems()`, `getStockHealth()`, `updateInventoryLevel()`
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx` — Integrated `useInventorySync` for post-save invalidation
- `frontend/src/pages/warehouse/MovementActionMenu.tsx` — Integrated `useInventorySync` for post-action invalidation
- `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` — Integrated `useInventorySync` for post-resolve invalidation
- `frontend/src/layout/nav.config.tsx` — Added "Analytics" nav entry (BarChartIcon, `/inventory/analytics`) under Inventory section
- `frontend/src/App.tsx` — Added route: `<Route path="/inventory/analytics" element={<InventoryAnalyticsPage />} />`

### Patterns introduced
- **useInventorySync hook pattern:** Centralised cache invalidation for all inventory query keys. Any component that mutates inventory data calls `invalidateAll()` from this hook instead of manually invalidating individual keys. This prevents stale data across the levels, alerts, movements, and analytics views.
- **InlineNumberCell pattern:** Click-to-edit number fields within DataTable rows. Renders as plain text by default; clicking activates a number input. On blur or Enter, PATCHes the backend and shows a green flash animation to confirm the save. Reusable for any numeric field that needs inline editing.
- **rowClassName dynamic styling:** DataTable now accepts a `rowClassName` function prop, enabling per-row conditional CSS classes based on row data (e.g., colouring rows by stock status).
- **Parallel useQuery pattern:** InventoryAnalyticsPage fires 3 independent `useQuery` calls simultaneously (movements-per-day, top-items, stock-health), each with its own loading/error state. Charts render independently as data arrives, avoiding waterfall loading.

---

## [PRE-ALPHA v0.6.8 | 2026-03-11] — Phase 2 Complete: MovementActionMenu, Status Tabs, Expandable Rows (Steps 2.7–2.9)

**What changed:** Built `MovementActionMenu` — a contextual kebab dropdown that shows lifecycle actions (approve/complete/cancel) based on the movement's current status, with confirm dialogs before execution and portal rendering to avoid table overflow clipping. Enhanced `InventoryMovementsPage` with status filter tabs (All/Pending/In Transit/Completed/Cancelled), expandable rows (chevron toggle + `MovementExpandedRow` detail panel), a Status column using `MovementStatusBadge`, and an Actions column hosting the new `MovementActionMenu`. Backend `GET /movements` endpoint now accepts an optional `status` query parameter for server-side filtering. Frontend `ListMovementsParams` updated to pass the status filter.

**Why:** Phase 2 completion. Staff could see movement status and details (v0.6.7) but had no way to act on them from the movements list. The action menu lets warehouse operators approve, complete, or cancel movements directly from the table row. Status tabs reduce cognitive load by letting staff focus on one lifecycle stage at a time (e.g., "show me only pending movements that need approval"). Server-side filtering ensures pagination correctness — client-side filtering would break page counts and miss records beyond the current page.

### Files created
- `frontend/src/pages/warehouse/MovementActionMenu.tsx` — Kebab dropdown with contextual lifecycle actions; confirm dialogs prevent accidental transitions; portal rendering avoids z-index/overflow issues in table rows

### Files modified
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` — Status filter tabs, expandable rows with chevron indicators, Status + Actions columns, status param in data fetching
- `backend/app/routers/warehouse.py` — `GET /{warehouse_id}/movements` gains optional `status` query parameter (server-side filter)
- `frontend/src/api/base_types/warehouse.ts` — `ListMovementsParams` gains optional `status` field

---

## [PRE-ALPHA v0.6.7 | 2026-03-11] — Movement Item Detail API + StatusBadge + ExpandedRow (Steps 2.3–2.6)

**What changed:** Added `MovementItemDetail` type and `getMovementItems()` API function to the frontend warehouse module. Built `MovementStatusBadge` — a colored pill component that maps movement status to visual cues (pending=yellow, in_transit=blue, completed=green, cancelled=gray). Built `MovementExpandedRow` — an expandable row component that fetches per-item transaction details via `GET /movements/{id}/items` and renders item name, master SKU, location codes, quantity, and directional arrows for transfers. Includes loading spinner, error state, and empty state handling.

**Why:** The movements table shows one row per movement, but warehouse staff need to see the status at a glance (badge) and drill into movement details (expanded row) to verify which items moved between which locations. These components complete the read-side UX for movement lifecycle — the badge shows where a movement is in the workflow, and the expanded row shows what it contains.

### Backend changes (v0.6.6)
- `backend/app/schemas/warehouse.py` — `MovementItemDetailRead` schema (item_id, item_name, master_sku, location_from, location_to, quantity, is_inbound)
- `backend/app/routers/warehouse.py` — `GET /warehouse/movements/{id}/items` endpoint; joins transactions with Item + InventoryLocation; groups transfer outbound/inbound pairs into single rows

### Frontend changes (v0.6.7)
- `frontend/src/api/base_types/warehouse.ts` — added `MovementItemDetail` interface
- `frontend/src/api/base/warehouse.ts` — added `getMovementItems(id)` function

### New files
- `frontend/src/pages/warehouse/MovementStatusBadge.tsx` — Colored pill component: maps `MovementStatus` to background/text color pairs; standalone for reuse in list and detail views
- `frontend/src/pages/warehouse/MovementExpandedRow.tsx` — Fetches movement items on mount via `getMovementItems(id)`, renders table with item name, SKU, location from/to (with arrow icons for transfers), quantity; loading/error/empty states

---

## [PRE-ALPHA v0.6.5 | 2026-03-11] — Movement Lifecycle Backend + Frontend API (Steps 2.0–2.2)

**What changed:** Added `status` column to `InventoryMovement` model (pending/in_transit/completed/cancelled) with Alembic migration. Movement creation now sets `status="pending"` and defers stock-level updates. Three new lifecycle endpoints: approve (pending→in_transit, deducts outbound stock), complete (in_transit→completed, adds inbound stock), cancel (reverses if needed). Frontend API functions added for all three transitions.

**Why:** The previous flow immediately applied stock changes on movement creation, with no review step. The lifecycle model lets warehouse staff review movements before stock is affected, supports transfer workflows where goods are in transit, and allows cancellation with automatic reversal.

### Backend changes
- `backend/app/models/warehouse.py` — `status` field on `InventoryMovement` (default "pending")
- `backend/app/schemas/warehouse.py` — `MovementStatus` literal type, `status` on `InventoryMovementRead`
- `backend/app/routers/warehouse.py` — `POST /movements` defers stock updates; 3 new `PATCH` lifecycle endpoints; `_build_movement_response` / `_fetch_movement_transactions` helpers
- `backend/alembic/versions/20260311_1316_add_status_to_inventory_movement.py` — migration adds `status` column + index

### Frontend changes
- `frontend/src/api/base/warehouse.ts` — `approveMovement()`, `completeMovement()`, `cancelMovement()`
- `frontend/src/api/base_types/warehouse.ts` — `MovementStatus` type, `status` field on `InventoryMovementRead`

---

## [PRE-ALPHA v0.6.3 | 2026-03-11] — Phase 1 Complete: Drawer Integration (Steps 1.6–1.7)

**What changed:** Replaced the old single-item movement modal in `InventoryMovementsPage` with the new `RecordMovementDrawer`. Removed ~200 lines of modal state, handlers, and JSX. Added a single `drawerOpen` boolean + `<RecordMovementDrawer>` render.

**Why:** Phase 1 completion — the multi-item drawer is now the live UI for recording movements. The old modal was single-item-only and couldn't support multi-item workflows, cross-field validation, or movement-type-aware location visibility.

### Modified files
- `src/pages/warehouse/InventoryMovementsPage.tsx` — removed modal, added drawer integration

### Removed code (from InventoryMovementsPage)
- State: `showModal`, `movementTypes`, `locations`, `formTypeId`, `formItemId`, `formItemSearch`, `itemResults`, `formRef`, `formNotes`, `txRows`, `saving`, `formError`
- Handlers: `openRecord`, `updateTx`, `addTxRow`, `removeTxRow`, `handleSubmit`
- Effects: movement types fetch, locations fetch, item search autocomplete
- JSX: entire modal overlay and body
- Imports: `CloseIcon`, `DeleteIcon`, `createMovement`, `listMovementTypes`, `listLocations`, `listItems`, unused type imports

### Phase 1 summary (all steps)
| Step | Component | Files |
|------|-----------|-------|
| 1.0 | Dependencies | `zod`, `@hookform/resolvers` |
| 1.1 | Backend `location_id` filter | `warehouse.py`, `warehouse.ts` |
| 1.2 | Form types + zod schema | `movement.types.ts` |
| 1.3 | MovementItemRow | `MovementItemRow.tsx`, `.css` |
| 1.4 | MovementItemGrid | `MovementItemGrid.tsx`, `.css` |
| 1.5 | RecordMovementDrawer | `RecordMovementDrawer.tsx`, `.css` |
| 1.6 | Page integration | `InventoryMovementsPage.tsx` |
| 1.7 | Verification + docs | `tsc --noEmit` passes |

---

## [PRE-ALPHA v0.6.2 | 2026-03-11] — RecordMovementDrawer (Step 1.5)

**What changed:** Built the main slide-over drawer for recording multi-item inventory movements. Wraps metadata fields (type, reference, locations) + `MovementItemGrid` + notes into a right-side panel with form orchestration and submission.

**Why:** The old single-item movement modal couldn't handle multi-item movements. The drawer pattern lets users reference the background table while filling out the form, and movement-type-aware field visibility prevents confusion (e.g. receipts don't ask for a source location).

### New files
- `src/pages/warehouse/RecordMovementDrawer.tsx` — Drawer with `FormProvider`, movement-type-aware location fields, multi-item submission (1 API call per item), transfer paired transactions, error handling
- `src/pages/warehouse/RecordMovementDrawer.css` — Backdrop, slide animation (cubic-bezier), header/body/footer, responsive location grid

### Movement type → field visibility
| Type | Source | Destination |
|------|--------|-------------|
| Receipt | hidden | shown |
| Shipment | shown | hidden |
| Transfer | shown | shown |
| Adjustment / Write Off / Cycle Count / Return | shown | hidden |

### Architecture notes
- Props: `open`, `onClose`, `warehouseId`, `onSuccess`
- Uses `FormProvider` so child components (`MovementItemGrid`, `MovementItemRow`) can access form context via `useFormContext`
- `activeLocationId` switches between source/dest depending on type — feeds into grid's inventory search
- One `POST /warehouse/movements` per item row (backend constraint: single `item_id` per movement)
- Transfer creates 2 transactions per item (outbound source + inbound dest)
- Form resets on close; close blocked during submission

---

## [PRE-ALPHA v0.6.1 | 2026-03-11] — Movement Item Row & Grid Components (Steps 1.3–1.4)

**What changed:** Built the two core UI building blocks for the multi-item movement drawer: `MovementItemRow` (per-row product autocomplete + qty + stock badge + remove) and `MovementItemGrid` (dynamic `useFieldArray` table with add/remove).

**Why:** The existing movement modal is single-item only (one movement = one item). The new drawer needs a multi-row item picker with per-row search against inventory levels, stock-aware quantity validation, and duplicate-item prevention — none of which the old modal supports.

### New files
- `src/pages/warehouse/MovementItemRow.tsx` — Debounced search (300ms) → `listInventoryLevels` with `location_id` filter; selected-item chip with clear button; available stock badge; qty input; remove button; `selectedItemIds` prop disables already-picked items in dropdown
- `src/pages/warehouse/MovementItemRow.css` — Selected chip, search dropdown, stock badge styles
- `src/pages/warehouse/MovementItemGrid.tsx` — `useFieldArray` grid with table layout, "Add Item" button, minimum-1-row guard, form-level zod error display
- `src/pages/warehouse/MovementItemGrid.css` — Table wrapper, thead, dashed add button styles

### Architecture notes
- Each `MovementItemRow` owns its search state independently (avoids indexed state arrays at grid level)
- `useWatch` on `items` feeds a memoized `selectedItemIds` Set to all rows for duplicate prevention
- Components use `useFormContext<MovementFormValues>()` — they must be rendered inside a `<FormProvider>` wrapping a `useForm` with `movementFormResolver`

---

## [PRE-ALPHA v0.6.0 | 2026-03-11] — Inventory Enhancement Phase 1 (Steps 1.0–1.2)

**What changed:** Installed `zod` (v4.3.6) and `@hookform/resolvers` (v5.2.2) for advanced form validation. Added `location_id` filter to the inventory levels API client. Created `movement.types.ts` with TypeScript interfaces and a zod validation schema for the upcoming multi-item movement drawer.

**Why:** The existing single-item movement modal cannot handle multi-item movements efficiently. The new drawer form requires cross-field validation (no duplicate items, source ≠ destination, quantity ≤ current stock) that react-hook-form alone cannot express — zod's `superRefine` solves this.

### New files
- `src/pages/warehouse/movement.types.ts` — `MovementFormValues`, `MovementItemEntry`, `MovementItemEntryMeta`, zod schema with `superRefine`, `movementFormResolver`, default values

### Modified files
- `src/api/base/warehouse.ts` — Added `location_id` to `ListInventoryParams`
- `package.json` — Added `zod`, `@hookform/resolvers`

### Backend changes (supporting)
- `backend/app/routers/warehouse.py` — `GET /{warehouse_id}/inventory` now accepts optional `location_id` query param; filters to that location with `quantity_available > 0`

---

## [PRE-ALPHA v0.5.54 | 2026-03-11] — Bundle Mass Upload

**What changed:** Built a full bundle mass upload feature (backend endpoint + frontend page). Users can upload CSV/Excel files where each row is a bundle component. Rows with the same `bundle_sku` are grouped into a single bundle.

**Why:** Bundles tab in the Mass Upload page was a "coming soon" placeholder. Users need to bulk-create bundles from spreadsheets, especially when migrating existing bundle data or creating many bundles at once.

### New files
- `src/pages/items/BundlesMassUploadPage.tsx` — Full upload page: CSV template download, drag-drop file picker, SheetJS preview table, result display with success/error counts and per-row error table
- `backend/app/services/items_import/bundle_importer.py` — Backend service: parses CSV/Excel, groups by bundle_sku, resolves FKs, validates component SKUs, creates Item + PlatformSKU + ListingComponent records

### Modified files
- `backend/app/routers/items.py` — Added `POST /items/bundles/import` endpoint
- `src/api/base/items.ts` — Added `importBundles()` function
- `src/pages/items/CatalogUploadPage.tsx` — Bundles tab now renders `BundlesMassUploadPage` instead of placeholder

### API endpoint
- `POST /api/v1/items/bundles/import` — File upload (multipart/form-data), returns `ImportResult` (total_rows, success_rows, error_rows, errors[])

---

## [PRE-ALPHA v0.5.53 | 2026-03-11] — Tabbed Create & Upload Pages

**What changed:** "Create New Item" and "Mass Upload" pages now have Item/Bundle tabs instead of being item-only. Created `CatalogCreatePage` (Item/Bundle segmented tabs wrapping existing form pages) and `CatalogUploadPage` (Items/Bundles tabs, bundle upload shows "coming soon" placeholder). Added `hideHeader` prop to `ItemFormPage`, `BundleFormPage`, and `ItemsMassUploadPage`. Nav entry renamed to "Create New".

**Why:** Users needed a unified creation flow — switching between creating an item vs a bundle should be a tab click, not a different page. Same for mass upload, which will support bundles in a future release.

### New files
- `src/pages/items/CatalogCreatePage.tsx` — Wrapper with segmented tabs (Item/Bundle); reads `?type=bundle` query param for deep-linking
- `src/pages/items/CatalogUploadPage.tsx` — Wrapper with segmented tabs (Items/Bundles); bundles tab shows placeholder

### Modified files
- `src/pages/items/ItemFormPage.tsx` — Added `hideHeader` prop
- `src/pages/bundles/BundleFormPage.tsx` — Added `hideHeader` prop; back button points to `/catalog/items`
- `src/pages/items/ItemsMassUploadPage.tsx` — Added `hideHeader` prop
- `src/pages/items/ItemsListPage.tsx` — "Create Bundle" dropdown navigates to `/catalog/items/new?type=bundle`
- `src/App.tsx` — Routes updated: `/catalog/items/new` → CatalogCreatePage, `/catalog/items/upload` → CatalogUploadPage, `/catalog/bundles/new` redirects
- `src/components/layout/nav.config.tsx` — "Create New Item" → "Create New"; isActive covers bundle paths

---

## [PRE-ALPHA v0.5.52 | 2026-03-11] — Unified "My Items" Page (Items + Bundles Merged)

**What changed:** Merged the separate Items list (`ItemsListPage`) and Bundles list (`BundlesListPage`) into a single unified "My Items" page. Removed separate Bundles/Create Bundle nav entries; `/catalog/bundles` now redirects to the unified page.

**Why:** Users had to switch between two separate pages to manage items and bundles. Consolidating into one page reduces navigation friction, provides a unified view of all catalog items, and simplifies the Catalog sidebar section.

### Modified files
- `src/pages/items/ItemsListPage.tsx` — Complete rewrite: dual-tab system (primary: All/Items/Bundles; secondary: All/Live/Unpublished/Deleted), dropdown "Add New" button (Create Item / Create Bundle), visual Bundle badge (violet, LayersIcon), expandable rows for bundle components (fetched via `getBundle()`) and item variations, combined status counts across items and bundles, Item Type filter dropdown (hidden on Bundles tab)
- `src/components/layout/nav.config.tsx` — Removed "Bundles" and "Create Bundle" nav entries; renamed "Items" to "My Items"; extended `isActive` to cover bundle paths
- `src/App.tsx` — `/catalog/bundles` route redirects to `/catalog/items`; removed `BundlesListPage` import

### Key features
- **Primary tabs**: All (items+bundles combined), Items (excludes bundle type), Bundles (uses `listBundles` API)
- **Secondary tabs**: All, Live, Unpublished, Deleted — counts sum across items+bundles on "All" tab, filter per-type otherwise
- **Add New dropdown**: single button with Create Item / Create Bundle options
- **Bundle badge**: violet pill with LayersIcon in Item Type column
- **Expandable rows**: bundles show component table (item, SKU, qty); items show variation table
- **Smart dispatch**: delete/restore/toggle calls correct API (item vs bundle) based on `item_type`

---

## [PRE-ALPHA v0.5.46 | 2026-03-09] — My Bundles Dashboard

**What changed:** Built the "My Bundles" dashboard page (`BundlesListPage`) mirroring the existing "My Items" page structure, with a dedicated backend API for listing bundles with component counts.

**Why:** The `/catalog/bundles` route was a PlaceholderPage. Users need a dedicated dashboard to view, search, filter, toggle status, soft-delete, restore, and inspect bundles — matching the established UX pattern from the Items module.

### New files
- `src/pages/bundles/BundlesListPage.tsx` — Full bundles dashboard: card header ("My Bundles" + "+ Create New Bundle"), 4 tabs (All/Live/Unpublished/Deleted with counts), DataTable with columns (Bundle, Components, Category, Status, Brand, Actions), expandable rows showing component breakdown
- `src/pages/bundles/BundleFilters.tsx` — Filter bar: search (name/SKU) + Category dropdown + Brand dropdown

### Modified files
- `src/App.tsx` — `/catalog/bundles` route now renders `BundlesListPage` (was PlaceholderPage)
- `src/api/base_types/items.ts` — Added `BundleListItem` interface (extends `ItemRead` with `component_count`, `total_quantity`)
- `src/api/base/items.ts` — Added `listBundles()`, `getBundleCounts()`, `getBundle()` functions; added `ListBundlesParams` interface
- `src/pages/bundles/BundleFormPage.tsx` — Edit mode now uses `getBundle(id)` instead of `updateBundle(id, {})` workaround

### Key features
- **Components column**: Badge showing "3 Items (7 qty)" per bundle — data from new `GET /items/bundles` endpoint with LEFT JOIN component counts
- **Expand-to-view**: Clicking a bundle row fetches and displays a component breakdown table (item name, SKU, quantity) via `GET /items/bundles/{id}`
- **Soft-delete/restore**: Uses `DELETE /items/bundles/{id}` and `POST /items/bundles/{id}/restore` — same endpoints from v0.5.45
- **Status toggle**: Inline switch that calls `PATCH /items/bundles/{id}` with `is_active` toggle
- **Tabs with counts**: Dedicated `GET /items/bundles/counts` endpoint scoped to Bundle type

---

## [PRE-ALPHA v0.5.44 | 2026-03-09] — Bundle Form Page (Create / Edit)

**What changed:** Built the complete bundle creation and editing UI: a dedicated form page with searchable item picker, dynamic component list with quantity steppers, and full integration with the `POST /items/bundles` and `PATCH /items/bundles/{id}` backend endpoints.

**Why:** The `/catalog/bundles` route was a PlaceholderPage. This implements the form for creating and modifying bundles — allowing users to search for items, add them as components with quantities, set bundle metadata (SKU, name, category, platform/seller), and submit in a single atomic transaction.

### New files
- `src/pages/bundles/BundleFormPage.tsx` — Main form page (create + edit modes); uses `react-hook-form`, loads dropdown options via `Promise.allSettled`, validates bundle composition client-side, handles image upload, platform/seller selection (create-only), component management
- `src/pages/bundles/ComponentSearch.tsx` — Searchable dropdown that queries `GET /items` with debounce (350ms), excludes already-added items and Bundle-type items, shows thumbnail + name + SKU per result
- `src/pages/bundles/ComponentList.tsx` — Dynamic component table with +/- stepper buttons, direct quantity input, delete per row, summary bar (component count + total quantity)

### Modified files
- `src/api/base_types/items.ts` — Added `BundleComponentInput`, `BundleCreateRequest`, `BundleUpdateRequest`, `BundleComponentRead`, `BundleReadResponse` interfaces
- `src/api/base/items.ts` — Added `createBundle()` and `updateBundle()` API functions
- `src/App.tsx` — Added routes: `/catalog/bundles/new` and `/catalog/bundles/:id/edit` pointing to `BundleFormPage`
- `src/components/layout/nav.config.tsx` — Added "Create Bundle" nav leaf under Catalog; updated Bundles leaf with `isActive` override to exclude `/new` sub-path

### UI features
- **Searchable item picker**: type-ahead search (min 2 chars, 350ms debounce) queries active items, excludes Bundle-type items and already-selected items; dropdown shows thumbnail + name + SKU
- **Component table**: inline quantity stepper (+/- buttons + direct input), row delete, row numbers, summary bar with total count
- **Bundle metadata**: name, SKU, SKU display name, description, category/brand/UOM dropdowns, image upload, active toggle
- **Platform/Seller**: required in create mode only (filtered sellers by selected platform); hidden in edit mode
- **Client-side validation**: required fields, SKU no-spaces rule, bundle composition rules (>1 items or qty > 1), platform/seller required in create mode
- **Error handling**: server error messages displayed in alert box; loading spinner during submit

---

## [PRE-ALPHA v0.5.40 | 2026-03-07] — Warehouse Overview & Location Management in Settings

**What changed:** Replaced the Settings Warehouse tab placeholder with a full warehouse management experience: embedded warehouse table + inline location management panel.

**Why:** The Warehouse tab was a stub. This implements the complete feature set: warehouse CRUD, hierarchical location tree, bulk pattern generator, and CSV/Excel import.

### New files
| File | Purpose |
|---|---|
| `pages/settings/WarehouseSettingsTab.tsx` | Warehouse table (all CRUD), expandable location panel per row |
| `pages/settings/warehouse_locations/BulkCreationWizard.tsx` | Pattern-based location generator with Cartesian product preview |
| `pages/settings/warehouse_locations/CsvLocationImport.tsx` | SheetJS-powered file import with validation + progress bar |
| `pages/settings/warehouse_locations/LocationTree.tsx` | Nested tree (Section→Zone→Aisle→Rack→Bin) with edit/delete per node |
| `pages/settings/warehouse_locations/PreviewTable.tsx` | Preview table for generated locations |
| `pages/settings/warehouse_locations/EditNodeModal.tsx` | Modal to rename a single tree node |
| `pages/settings/warehouse_locations/LocationManagementPage.css` | Panel layout CSS |

### Modified files
| File | Change |
|---|---|
| `pages/settings/LocationManagementSection.tsx` | Added `overrideWarehouseId`/`overrideWarehouseName` props; added Generator/Import tab switcher |
| `pages/settings/SettingsPage.tsx` | Warehouse tab renders `<WarehouseSettingsTab />` |
| `api/base_types/warehouse.ts` | Added `is_active`, `sort_order` to `InventoryLocationCreate/Update` |

### Feature breakdown
- **Warehouse table** — compact table with search, status filter, Add/Edit modal, status toggle, duplicate, soft delete; clicking "Manage" on any row expands an inline location panel
- **Location Tree** — hierarchical expand/collapse tree with type badges, location counts, hover edit/delete actions
- **Pattern Generator** — enable each hierarchy level independently; set prefix + numeric range (with zero-padding) or explicit comma-separated values; preview Cartesian product before committing
- **CSV/Excel Import** — download template → upload file → parse + validate → preview with error highlighting → import row-by-row with live progress bar → result summary

---

## [PRE-ALPHA v0.5.39 | 2026-03-07] — Warehouse Settings Grid Refactor

**What changed:** Refactored `WarehouseCard.tsx` (Settings > Warehouse > Management tab) into a fully responsive CSS Grid with a permanently-visible primary action card.

**Why:** The previous implementation violated several UI contracts: the `+ Create` CTA card disappeared while the form was open (breaking the "always first" slot requirement), used non-standard breakpoints (`sm/xl`), and had no empty state for zero warehouses.

### Changes in detail

| Change | Before | After |
|---|---|---|
| Grid breakpoints | `cols-1 sm:cols-2 lg:cols-3 xl:cols-4` | `cols-1 md:cols-2 lg:cols-4` |
| CTA card visibility | Hidden when form open | Always visible in slot 0 |
| Create form placement | Inside grid as `col-span-full` replacing CTA | Above the grid; CTA card stays in position |
| CTA toggle behaviour | n/a | Click again to close form (icon rotates 45°) |
| Name font weight | `font-semibold` | `font-bold` |
| Status badge | Inline JSX | Extracted `<StatusBadge />` component |
| CTA card | Inline JSX | Extracted `<CreateWarehouseCard />` component |
| Empty state | None | `<EmptyState />` with inbox icon + copy |

### Files modified
- `frontend/src/pages/settings/WarehouseCard.tsx` — full refactor (no new files created; all sub-components stay in the same file per single-file convention)

---

## [PRE-ALPHA v0.5.35 | 2026-03-06] — Move Location Management into Settings > Warehouse > Locations & Sections

**What changed:** Relocated the Location Management UI (Location Tree, Bulk Creation Wizard, Preview Table) from its standalone page (`/inventory/locations`) into the Settings page's **Warehouse > Locations & Sections** sub-tab. Created `LocationManagementSection.tsx` in `pages/settings/` as the section wrapper. Removed the standalone route, nav item, and `LocationManagementPage.tsx`. The underlying components (`LocationTree`, `BulkCreationWizard`, `PreviewTable`) remain in `pages/warehouse/locations/` and are imported by the settings section.

**Why:** The user requested the location management UI live inside the Settings > Warehouse configuration area rather than as a standalone page, keeping all warehouse configuration tools in one administrative surface.

### Files created

| File | Purpose |
|------|---------|
| `pages/settings/LocationManagementSection.tsx` | Settings-embedded version of the location management UI: uses `useWarehouse()` context, TanStack Query for hierarchy + bulk-generate, two-column layout (tree + wizard/preview) with `border` styling (no nested cards inside the settings card) |

### Files modified

| File | Change |
|------|--------|
| `pages/settings/SettingsPage.tsx` | Replaced `WarehouseLocationCard` import/usage with `LocationManagementSection` in the "configuration" sub-tab |
| `App.tsx` | Removed `/inventory/locations` route and `LocationManagementPage` import |
| `components/layout/nav.config.tsx` | Removed "Locations" leaf from Inventory section |

### Files deleted

| File | Why |
|------|-----|
| `pages/warehouse/locations/LocationManagementPage.tsx` | Dead code — functionality moved to `LocationManagementSection` |

### Build

- TypeScript: zero errors
- Production: 949.39 kB JS (-5 kB), 37.11 kB CSS

---

## [PRE-ALPHA v0.5.34 | 2026-03-06] — Warehouse Location Management Components

**What changed:** Built location management components with three parts: a Location Tree sidebar (accordion-style hierarchy navigation), a Bulk Creation Wizard (range inputs for each hierarchy level), and a Preview Table (Cartesian product preview before saving). Integrated TanStack Query for API state management and Lucide React for icons. Added TypeScript types and API functions for hierarchy and bulk-generate endpoints.

**Why:** Warehouse managers need a visual tool to explore the location hierarchy and scaffold hundreds of locations at once. These components bridge the backend bulk-generate and hierarchy endpoints (v0.5.32-v0.5.33) with a purpose-built frontend interface.

### Dependencies added

| Package | Version | Purpose |
|---------|---------|---------|
| `@tanstack/react-query` | ^5.x | Server-state management — `useQuery` for hierarchy fetch, `useMutation` for bulk-generate with automatic cache invalidation |
| `lucide-react` | ^0.x | Icon library for tree nodes and wizard UI (ChevronRight, Warehouse, MapPin, Save, etc.) |

### Files created (all in `src/pages/warehouse/locations/`)

| File | Purpose |
|------|---------|
| `LocationTree.tsx` | Recursive accordion component — renders `LocationTreeNode[]` with expand/collapse, level-specific icons, count badges, display_code for leaves |
| `BulkCreationWizard.tsx` | 5 segment cards (section/zone/aisle/rack/bin) with enable toggle, range/values mode selector, prefix/start/end/pad inputs, client-side Cartesian product preview, live validation, total combinations counter with 10K limit |
| `PreviewTable.tsx` | Paginated preview table (50 rows/page) showing generated location codes before API call, active-column detection, large-batch warning |
| `LocationManagementPage.css` | Fixed-width tree panel (340px), scrollbar styling, responsive stacking below 1024px |

### Files modified

| File | Change |
|------|--------|
| `App.tsx` | Wrapped Routes in `QueryClientProvider` |
| `api/base_types/warehouse.ts` | Added `LocationTreeNode`, `SegmentRangeInput`, `BulkGenerateRequest`, `BulkGenerateError`, `BulkGenerateResponse` types |
| `api/base/warehouse.ts` | Added `getLocationHierarchy()`, `bulkGenerateLocations()` API functions |

### UX decisions

- **Two-column layout** — Tree sidebar (340px fixed) on the left for exploration, wizard + preview on the right for bulk operations. Stacks vertically on mobile (<1024px).
- **Client-side preview** — Cartesian product computed in TypeScript (`expandSegment` + `cartesianProduct`) before any API call, giving instant feedback. The same computation runs on the backend for the actual insert.
- **Range vs Values mode** — Each hierarchy level can use numeric ranges (prefix + start/end/pad) or an explicit comma-separated values list (e.g. "COLD, DRY, AMBIENT"). This matches the backend `SegmentRange` two-mode design.
- **10,000 combination limit** — Validated client-side and displayed as an error banner; matches backend `MAX_COMBINATIONS` guard.
- **TanStack Query cache invalidation** — On successful bulk-generate, the `location-hierarchy` query is automatically invalidated, causing the tree sidebar to refresh with the newly created locations.
- **Lucide icons for tree** — Different icon per hierarchy level (Warehouse, LayoutGrid, MapPin, ArrowRightLeft, Server, Box) for visual distinction at a glance.

---

## [PRE-ALPHA v0.5.29 | 2026-03-06] — Layout Restructure: Full-Width Header + Global Warehouse Context

**What changed:** Restructured `MainLayout.tsx` to match the new wireframe layout. The header now spans the full viewport width (fixed positioning, z-1300) with Logo, Hamburger, Search, Account dropdown, and a Notification bell placeholder. The sidebar starts below the header with a global `WarehouseSelector` at the top. Created `WarehouseContext` for app-wide warehouse state and migrated all three inventory pages to consume it.

**Why:** The previous layout had the logo/brand inside the sidebar and the top bar nested inside the main content area (offset by sidebar margin). The wireframe calls for a full-width top header above both sidebar and content, consistent with modern dashboard patterns. The global warehouse selector replaces per-page selectors so operators set the warehouse once and it persists across pages.

### Files created

| File | Purpose |
|------|---------|
| `api/contexts/WarehouseContext.tsx` | React context providing `warehouses`, `selectedWarehouseId`, `selectedWarehouse`, `setSelectedWarehouseId`, `loading`. Fetches active warehouses on mount, persists selection to `localStorage` (`selected_warehouse_id`), auto-selects first warehouse if nothing persisted. |
| `components/layout/WarehouseSelector.tsx` | Sidebar pill-shaped dropdown that reads from `useWarehouse()` context. Shows warehouse name + chevron when expanded, icon-only when collapsed, dropdown with checkmark for selected item. |

### Files modified

| File | Change |
|------|--------|
| `components/layout/MainLayout.tsx` | Extracted header to fixed full-width top bar (`z-[1300]`, `h-16`); moved logo from sidebar to header; added `NotificationsNoneIcon` placeholder; replaced sidebar brand area with `LayoutWarehouseSelector`; sidebar `top: 64px`, `height: calc(100vh - 64px)`; added `HEADER_HEIGHT` constant |
| `App.tsx` | Wrapped `<MainLayout />` in `<WarehouseProvider>` inside the `ProtectedRoute` route element |
| `pages/warehouse/InventoryLevelsPage.tsx` | Replaced local `warehouseId` state + `WarehouseSelector` import with `useWarehouse()` context; removed per-page warehouse dropdown from header |
| `pages/warehouse/InventoryMovementsPage.tsx` | Same migration to global warehouse context |
| `pages/warehouse/InventoryAlertsPage.tsx` | Same migration to global warehouse context |

### UX decisions
- Logo text ("WOMS") is hidden on very small screens (`hidden sm:inline`) to save header space
- Notification bell is a static placeholder — no badge or dropdown until backend notification system exists
- Warehouse selector adapts to sidebar collapsed state: shows icon-only when collapsed, with a flyout dropdown positioned to the right
- Inventory pages no longer show "Select a warehouse" empty states when using global context (auto-selects first warehouse)
- Existing `pages/warehouse/WarehouseSelector.tsx` kept intact for backward compatibility

---

## [PRE-ALPHA v0.5.23 | 2026-03-04] — Settings Module Expansion

**What changed:** Settings page reorganised into three named sections. Added `PlatformCard` for marketplace CRUD and `WarehouseLocationCard` for per-warehouse storage location management. Backed by new backend endpoints and API layer.

**Why:** Operators need to configure warehouse topology (locations) and marketplace connections (platforms) from the same administrative surface as item attribute tables.

### Files added

| File | Purpose |
|------|---------|
| `pages/settings/PlatformCard.tsx` | Inline Add/Edit card for platform CRUD — name, address, postcode, API endpoint, active toggle |
| `pages/settings/WarehouseLocationCard.tsx` | Per-warehouse location card — dropdown to select warehouse, grid form for section/zone/aisle/rack/bin, formatted code display (`A-Z1-01`) |
| `api/base_types/platform.ts` | `PlatformRead/Create/Update`, `SellerRead/Create/Update` types |
| `api/base/platform.ts` | `listPlatforms`, `createPlatform`, `updatePlatform`, `listSellers`, `createSeller`, `updateSeller` functions |

### Files modified

| File | Change |
|------|--------|
| `pages/settings/SettingsPage.tsx` | Reorganised into 3 sections: **Items Data** (Item Types, Categories, Brands, UOMs, Statuses), **Warehouse** (WarehouseLocationCard), **Platforms** (PlatformCard); section headings + descriptions added |
| `api/base_types/warehouse.ts` | Added `InventoryLocationCreate` and `InventoryLocationUpdate` types |
| `api/base/warehouse.ts` | Added `createLocation`, `updateLocation`, `deleteLocation` API functions |

### UX decisions
- Location code displayed as `section-zone-aisle-rack-bin` with blank parts omitted; falls back to `LOC-{id}`
- Platform delete omitted intentionally — platforms are reference data linked to order history; deactivation via toggle is the safe operation
- Both cards share the same inline form expansion pattern as `AttributeCard` for consistency

---

## [PRE-ALPHA v0.5.22 | 2026-03-04 16:00] — Bundle Image Upload + Delete

**What changed:** Image upload capability added to `BundleFormPage`; delete action added to `CatalogBundlesPage`; bundle list now shows a thumbnail column.

**Why:** Operators need to visually identify bundles the same way they do regular items. Delete allows removing stale bundles without DB access.

### Files modified

| File | Change |
|------|--------|
| `pages/catalog/BundleFormPage.tsx` | +`imageUrl`/`imageUploading` state + `fileInputRef`; image upload UI block (click-to-upload square, preview, remove button, hidden file input); `image_url` in create + update payloads; edit-mode sets `imageUrl` from `item.image_url` |
| `pages/catalog/CatalogBundlesPage.tsx` | +`deleteItem`, `DeleteOutlineIcon`, `ImageIcon` imports; +`deleting` state; +`handleDelete()` with confirm dialog; Bundle Name column shows thumbnail; Actions column is now edit + delete pair |

### UX decisions
- Upload pattern identical to `ItemFormPage` — consistency is intentional so operators learn one pattern
- Thumbnail placeholder matches `ItemsListPage` style exactly

---

## [PRE-ALPHA v0.5.21 | 2026-03-04 14:00] — Bundles Sub-Module (Catalog)

**What changed:** New Bundles sub-module under Catalog — dedicated list page and create/edit form for Bundle-type items.

**Why:** Bundle creation has a distinct workflow (component picker, qty validation, SKU generation) that does not belong in the general Item form. A dedicated sub-module gives operators a purpose-built interface while reusing the existing `ItemBundleComponent` BOM backend (v0.5.17) and `BundleComponentsTab` (v0.5.20).

### Files created/modified

| File | Change |
|------|--------|
| `pages/catalog/CatalogBundlesPage.tsx` | NEW — Bundle list: type ID resolved via `listItemTypes()`, filters items by `item_type_id`, DataTable with toggle/search/pagination |
| `pages/catalog/BundleFormPage.tsx` | NEW — Create mode: local `PendingComponent[]` + batch submit; Edit mode: embeds `BundleComponentsTab`; auto-SKU toggle; live ≥2 qty validation |
| `components/layout/MainLayout.tsx` | +`RedeemIcon`; Bundles MenuItem under Catalog SubMenu |
| `App.tsx` | +3 routes: `/catalog/bundles`, `/catalog/bundles/new`, `/catalog/bundles/:id/edit` |

### UX decisions
- **Auto-generate SKU** is a toggle — reactive, read-only while enabled; clears back to editable on disable
- **Qty indicator** has three states (green/amber/neutral) so operator always knows how far they are from the minimum
- **Batch create submission** — item is created first, then components are added in a loop; on any component failure the bundle item still exists and operator is redirected to edit mode to add remaining components
- **Bundle type ID lookup** — resolved once on mount, cached in state; if "Bundle" type not found in seed, a configuration error state is shown with remediation instructions

---

## [PRE-ALPHA v0.5.20 | 2026-03-04 10:00] — Bundle SKU Frontend UI

**What changed:** Frontend Phase 4 of the Bundle SKU module — BOM management on the Item Form, Bundle ATP Lookup on the Inventory Levels page, and bundle fulfillment support in the Record Movement modal.

**Why:** Closes the bundle SKU feature loop started in v0.5.17–v0.5.19. Warehouse operators need a UI to manage Bill-of-Materials for bundle products, look up live bundle ATP without raw API calls, and record a bundle sale that deducts all component stocks atomically in a single operation.

### Files created/modified

| File | Change |
|------|--------|
| `api/base_types/items.ts` | +5 bundle types (BundleComponentRead/Create/Update, BundleATPRead, BundleMembershipRead) |
| `api/base/items.ts` | +6 bundle API functions |
| `api/base_types/warehouse.ts` | +`reserved_quantity` on enriched level; +4 fulfillment types |
| `api/base/warehouse.ts` | +3 fulfillment API functions (reserveStock, releaseStock, fulfillBundle) |
| `pages/items/BundleComponentsTab.tsx` | NEW — BOM editor: search items, add/toggle/remove components |
| `pages/items/ItemFormPage.tsx` | Tab strip (Details / Bundle Components) when item_type = "Bundle" in edit mode |
| `pages/warehouse/InventoryLevelsPage.tsx` | Collapsible Bundle ATP Lookup card; Qty column now shows reserved_quantity |
| `pages/warehouse/InventoryMovementsPage.tsx` | Bundle mode selector when Bundle item selected; fulfill path calls POST /warehouse/fulfill/bundle |

### UX decisions
- **Tab strip** in ItemFormPage only renders in edit mode (bundle must already exist before BOM can be managed)
- **BundleATPLookup** filters item search client-side for `item_type.name === "Bundle"` — avoids new backend endpoint
- **Auto-switch to fulfill mode** — when a Bundle item is selected in the movement modal, fulfill mode is pre-selected; operator can override to manual if needed
- **Inline confirm-remove** pattern on BundleComponentsTab rows — avoids modal overhead for a simple destructive action

---

## [PRE-ALPHA v0.5.17–v0.5.19 | 2026-03-04 01:00] — Bundle SKU Backend (Frontend Phase Pending)

**What changed:** Backend-only release. Bundle SKU schema, services, and API are complete. Frontend (v0.5.20) completed in the next entry.

---

## [PRE-ALPHA v0.5.12 | 2026-03-03 21:00] — Warehouse & Inventory Frontend Module

**What changed:** Built the complete warehouse/inventory frontend module — 4 new pages, shared components, TypeScript types, API functions, sidebar navigation, and routing.

**Why:** The warehouse backend was functional but had no frontend surface. This release gives operations staff a full UI for managing warehouses, monitoring stock levels with color-coded status, recording movements (inbound/outbound/transfer), and resolving inventory alerts.

### New Pages (all in `src/pages/warehouse/`)

1. **WarehouseListPage** (`/inventory/warehouses`) — CRUD list with inline create/edit modal, active status toggle, search, click-through to stock levels
2. **InventoryLevelsPage** (`/inventory/levels`) — Real-time stock matrix with warehouse selector, summary chips (counts by status), status filter tabs (All/OK/Low/Critical/Out of Stock/Overstock), search by item name or SKU
3. **InventoryMovementsPage** (`/inventory/movements`) — Movement history table with Record Movement modal (movement type, item autocomplete, multi-location transactions for transfers, reference number, notes)
4. **InventoryAlertsPage** (`/inventory/alerts`) — Alert action center with resolve modal, unresolved/all/resolved filter, summary chips per alert type

### Shared Page Components (in `src/pages/warehouse/`)

- **StockStatusBadge** — Color-coded badge (green OK, yellow Low, orange/red Critical, red Out of Stock, blue Overstock)
- **WarehouseSelector** — Dropdown that loads active warehouses on mount, used across Levels/Movements/Alerts pages

### API Layer

| File | Contents |
|------|----------|
| `src/api/base_types/warehouse.ts` | 13 TypeScript interfaces: `WarehouseRead/Create/Update`, `InventoryLocationRead`, `LocationSummary`, `InventoryLevelEnrichedRead`, `StockStatus`, `InventoryAlertRead`, `AlertType`, `MovementTypeRead`, `InventoryMovementRead`, `InventoryTransactionCreate`, `InventoryMovementCreate` |
| `src/api/base/warehouse.ts` | 11 API functions: `listWarehouses`, `getWarehouse`, `createWarehouse`, `updateWarehouse`, `listLocations`, `listInventoryLevels`, `listAlerts`, `resolveAlert`, `listMovementTypes`, `listMovements`, `createMovement` |

### Navigation

- Added **Inventory** submenu to `MainLayout.tsx` sidebar with 4 items: Warehouses, Stock Levels, Movements, Alerts
- Added 4 routes to `App.tsx`

### Files Modified / Created

| File | Action |
|------|--------|
| `frontend/src/api/base_types/warehouse.ts` | Created |
| `frontend/src/api/base/warehouse.ts` | Created |
| `frontend/src/pages/warehouse/StockStatusBadge.tsx` | Created |
| `frontend/src/pages/warehouse/WarehouseSelector.tsx` | Created |
| `frontend/src/pages/warehouse/WarehouseListPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Created |
| `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` | Created |
| `frontend/src/App.tsx` | Modified — added 4 inventory routes |
| `frontend/src/components/layout/MainLayout.tsx` | Modified — added Inventory submenu + 4 icon imports |

---

## [PRE-ALPHA v0.5.11 | 2026-03-03 16:00] — Items Mass Upload

**What changed:** Implemented an end-to-end mass upload feature for the Items catalog. Users can upload a CSV or Excel file containing multiple items, preview the first 5 rows client-side (via SheetJS), confirm, and have the backend validate and insert all valid rows in one request. Per-row errors are reported back without aborting the entire batch.

**Why:** Manually creating hundreds of items one-by-one is impractical. A mass upload tool with client-side preview and clear per-row error feedback improves the data-entry experience significantly for operations staff.

### Key Features

1. **Client-side parse & preview** — SheetJS (`xlsx`) reads the uploaded file in the browser, extracts the first sheet, and renders the first 5 rows in a preview table before any network call is made. This lets users catch gross formatting errors instantly.
2. **Drag-and-drop dropzone** — Drop zone accepts `.csv`, `.xlsx`, `.xls` via `ondragover`/`ondrop`. Hidden `<input type="file">` handles click-to-select.
3. **Template download** — "Download CSV Template" generates a Blob in-browser (no server call) with the correct column headers and triggers a programmatic download.
4. **Client-side validation** — Extension whitelist, non-empty file, max 10 MB — all checked before the request is sent.
5. **Confirm & Upload flow** — "Upload Items" button appears below the preview. Reverts to dropzone via "Cancel".
6. **Per-row error table** — After upload, shows success count + a table (Row | Master SKU | Error) for every failed row. "Upload Another File" resets the UI.
7. **Backend column normalisation** — `parser.py` maps common header aliases (e.g. `"Product Name"` → `item_name`, `"Internal CODE"` → `master_sku`, `"BaseUOM"` → `uom`) so files from external sources work without manual header renaming.
8. **FK resolution & duplicate detection** — `validator.py` builds in-memory caches (one SELECT per lookup table) and checks for duplicate `master_sku` both within the file and against existing DB rows.
9. **Batch insert** — `importer.py` inserts all valid rows in a single flush; errors do not prevent valid rows from being saved.

### Files Modified / Created

| File | Action |
|------|--------|
| `backend/app/schemas/items.py` | Added `ImportRowError`, `ImportResult` schemas |
| `backend/app/services/items_import/__init__.py` | Created (empty package marker) |
| `backend/app/services/items_import/parser.py` | Created — CSV/Excel parser with alias normalisation |
| `backend/app/services/items_import/validator.py` | Created — FK cache, duplicate check, `is_active` parse |
| `backend/app/services/items_import/importer.py` | Created — orchestrates parse → validate → bulk insert |
| `backend/app/routers/items.py` | Added `POST /import` endpoint |
| `frontend/src/api/base_types/items.ts` | Added `ImportRowError`, `ItemsImportResult` types |
| `frontend/src/api/base/items.ts` | Added `importItems(file)` API function |
| `frontend/src/pages/items/ItemsMassUploadPage.tsx` | Created — full upload page with drag-drop, preview, result |
| `frontend/src/App.tsx` | Added `/catalog/items/upload` route |
| `frontend/src/pages/items/ItemsListPage.tsx` | Wired "Mass Upload" button to navigate to upload page; fixed icon import |

### npm Dependency Added

| Package | Version | Purpose |
|---------|---------|---------|
| `xlsx` | ^0.18.5 | SheetJS — client-side CSV/Excel parsing for preview |

---

## [PRE-ALPHA v0.5.10 | 2026-03-03 14:00] — Create Item: Toggle Switch, Validation & Backend Integrity

**What changed:** Replaced the Status `<select>` with a CSS toggle switch, tightened client-side validation on `master_sku` (no-spaces rule) and `sku_name` (max 500), standardized all select placeholders to "Select", removed the string-to-bool coercion hack from `onSubmit`, and added `disabled:cursor-not-allowed` to the submit button.

**Why:** A boolean field should use a boolean control. The previous select required a runtime type coercion and lacked uniqueness feedback for `master_sku`. The `sku_name` max-length was inconsistent with the backend schema.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/ItemFormPage.tsx` | Status toggle switch (watch+setValue), master_sku no-spaces validation, sku_name maxLength 500, select placeholder "Select", Row 4 → 2-col + toggle row, remove is_active string coercion, disabled:cursor-not-allowed on submit |

### Validation Rules (as-built)

| Field | Rule | Error Message |
|-------|------|---------------|
| item_name | Required, max 500 chars | "Item name is required" / "Max 500 characters" |
| master_sku | Required, max 100 chars, no whitespace | "Master SKU is required" / "Max 100 characters" / "Master SKU must not contain spaces" |
| sku_name | Optional, max 500 chars | "Max 500 characters" |

---

## [PRE-ALPHA v0.5.9 | 2026-03-03 12:00] — VariationBuilder Redesign

**What changed:** Completely redesigned the `VariationBuilder` component to match the specified e-commerce seller-centre style UI, and removed `price`/`stock` from variation combinations.

**Why:** The previous chip-based UI differed from the target design. The new layout uses a 2-column option grid with character counters, drag handles, and per-option delete icons — more ergonomic for product managers entering variation data. Price and stock are removed from variations as they belong in the pricing/order module, not the item catalogue.

### Key Changes

1. **Option grid** — 2-column layout; each option shows an inline `N/20` character counter, a `DragIndicatorIcon` handle (visual), and a delete button
2. **Name counter** — Variation name input now shows `N/14` inline counter on the right
3. **Max 5 options** — Draft "Input" slot appears after committed options up to the 5-option cap
4. **Section header** — Added `• Variations` label above the builder panels
5. **Combination table** — Price and Stock columns removed; only Image + variation values + SKU remain
6. **Type cleanup** — Removed `price` and `stock` fields from `VariationCombination` interface and all utility functions

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/VariationBuilder.types.ts` | Removed `price`, `stock` from `VariationCombination` |
| `frontend/src/pages/items/VariationBuilder.utils.ts` | Updated default combo shape; strip price/stock in `migrateOldFormat` |
| `frontend/src/pages/items/VariationBuilder.tsx` | Full redesign — 2-column option grid, char counters, drag handles, simplified combination table |

---

## [PRE-ALPHA v0.5.8 | 2026-03-02 21:00] — Item Main Image Upload

**What changed:** Added a product image upload section to the Item Create/Edit form. Users can click to upload an image (JPG/PNG/WebP/GIF, max 5 MB), see a live preview, and remove the image. The upload goes to a new `POST /items/upload-image` endpoint which stores files locally and returns a URL path. The URL is sent as part of the normal item JSON payload.

**Why:** Items had no visual representation. Product images are essential for e-commerce catalog management and visual identification in the item list.

### Key Features

1. **Click-to-upload area** — 128x128 dashed-border placeholder with ImageIcon; shows preview after upload
2. **Upload-first pattern** — Image uploaded via separate endpoint, URL stored in `image_url` column
3. **Validation** — Content type (4 image formats) + size limit (5 MB) enforced on backend
4. **Remove image** — Click "Remove image" to clear, sets `image_url` to null on save
5. **Edit mode** — Existing image loads and displays on edit

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/api/base_types/items.ts` | Added `image_url` to TypeScript types |
| `frontend/src/api/base/items.ts` | Added `uploadItemImage()` API function |
| `frontend/src/pages/ItemFormPage.tsx` | Added image upload UI section at top of form |
| `frontend/vite.config.ts` | Added `/uploads` proxy rule for dev server |

### Build

- Production: 493.07 kB JS, 25.86 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.7 | 2026-03-02 17:30] — VariationBuilder Component

**What changed:** Replaced the basic variation section in ItemFormPage with a full e-commerce-style VariationBuilder. Users can now define up to 2 variation dimensions with auto-growing option inputs, and a dynamic combination table generates rows for every cartesian product with per-variant SKU, Price, Stock, and image placeholder fields. Includes batch-apply for mass updates.

**Why:** The old variation section was just text rows (attribute name + comma-separated values) with no per-variant data. Sellers need a matrix view to manage individual variation SKUs, prices, and stock levels — matching the UX of Shopee/Lazada seller centers.

### Key Features

1. **Variation Builder** — Define variation name + options with auto-grow inputs (type + Enter to add)
2. **Max 2 Levels** — Primary (e.g. Colour) + optional secondary (e.g. Size)
3. **Combination Table** — Auto-generated rows for every cartesian product
4. **Per-Variant Fields** — SKU, Price, Stock, and image placeholder per combination row
5. **Batch Apply** — Mass-update Price/Stock/SKU across all rows at once
6. **Backwards Compatibility** — `migrateOldFormat()` auto-generates combinations from old attribute-only data

### New Files (all in `src/pages/items/`)

| File | Purpose |
|------|---------|
| `VariationBuilder.types.ts` | Shared interfaces: `VariationsData`, `VariationAttribute`, `VariationCombination` |
| `VariationBuilder.utils.ts` | Pure functions: `cartesianProduct()`, `syncCombinations()`, `migrateOldFormat()` |
| `VariationBuilder.tsx` | Main component + `VariationLevel` and `CombinationTable` sub-components |

### Files Modified

| File | Change |
|------|--------|
| `ItemFormPage.tsx` | Removed `VariationRow`, `useFieldArray`, old helpers; added `useState<VariationsData>` + `<VariationBuilder>` integration |

### Build

- Production: 491.28 kB JS, 25.68 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.6.1 | 2026-03-02 16:00] — Move Item Type to Tabs Row

**What changed:** Relocated the "Item Type" dropdown from the lower filter row to the tabs row, right-aligned via `justify-between`. Removed Item Type props/state/fetch from `ItemFilters.tsx`; added them to `ItemsListPage.tsx`.

**Why:** Item Type (Outgoing Product, Raw Material, Office Supply) is a workspace-level toggle, not a search filter. Elevating it to the tabs row makes it visually distinct and frees space in the filter bar for the remaining Search + Category + Brand controls.

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/pages/items/ItemFilters.tsx` | Removed `itemTypeId`, `onItemTypeChange`, `itemTypes` state, `listItemTypes` import, and `<select>` |
| `frontend/src/pages/ItemsListPage.tsx` | Added `itemTypes` state + fetch; Item Type `<select>` in tabs row with `flex-wrap justify-between`; cleaned up `<ItemFilters>` props |

---

## [PRE-ALPHA v0.5.6 | 2026-03-02] — Items Page Redesign (List + Form)

**What changed:** Redesigned the Items list page and Create/Edit form to match a reference admin dashboard design. Added tab-based status filtering with live counts, checkbox row selection, page-number pagination, combined item column, and flattened the multi-tab form into a single-card layout.

**Why:** The previous v0.5.4 implementation was functional but didn't match the target UX. This redesign improves: (1) status visibility via tab counts, (2) filtering with inline search + Item Type dropdown, (3) data density with combined columns, and (4) form usability by showing all fields at once.

### Key Changes

1. **Tab-based Status Filtering** — All / Live / Unpublished / Deleted tabs with real-time counts from new `GET /items/counts` endpoint
2. **Combined Items Column** — Image placeholder + item name + SKU in a single column
3. **Checkbox Selection** — DataTable now supports `selectable` prop with select-all/individual checkboxes
4. **Page-Number Pagination** — Replaced prev/next with clickable page numbers, ellipsis, first/last buttons
5. **Inline Filters** — Search + Category + Brand dropdowns in filter bar (removed Active/Inactive — tabs handle it; Item Type moved to tabs row in v0.5.6.1)
6. **Single-Card Form** — Removed tab layout; all fields visible in one card (Name+SKU → Description → Category+Brand → UOM+Type+Status → Variations)
7. **Status Badges** — Active (green), Inactive (gray), Deleted (red) inline badges in list

### File Organization

- Moved `ItemFilters.tsx` from `components/items/` → `pages/items/` (page-specific component rule: `components/` is for universal/shared components only)

### Files Modified

| File | Change |
|------|--------|
| `frontend/src/api/base/items.ts` | Added `getItemCounts()`, `item_type_id` + `include_deleted` params |
| `frontend/src/api/base_types/items.ts` | Added `deleted_at` to `ItemRead` |
| `frontend/src/components/common/DataTable.tsx` | Added `selectable`, `noCard` props; page-number pagination |
| `frontend/src/pages/items/ItemFilters.tsx` | Relocated + added search input + Item Type dropdown |
| `frontend/src/pages/ItemsListPage.tsx` | Full redesign with tabs, card wrapper, new columns |
| `frontend/src/pages/ItemFormPage.tsx` | Flattened tabs → single card, reordered fields |

### Build

- Production: 489.60 kB JS, 24.55 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.4 | 2026-03-02] — Items Module (Master Catalog)

**What changed:** Built the complete Items module frontend with a paginated catalog list, advanced filtering, variation row expansion, and a multi-tab create/edit form.

**Why:** The Items module is the core data management interface — users need to browse, search, create, and edit their product catalog with variation support (size, color, etc.).

### Key Features

1. **Item Catalog List** (`/catalog/items`)
   - Server-side paginated DataTable (reusable component)
   - Global search by item name or master SKU (debounced)
   - Column filters: Status, Category, Brand (loaded from backend)
   - Row expansion: click parent items to view child variations inline
   - Edit and Delete actions per row (soft-delete with confirmation)

2. **Item Create/Edit Form** (`/catalog/items/new`, `/catalog/items/:id/edit`)
   - Powered by `react-hook-form` with `useFieldArray` for dynamic variations
   - **Tab 1 — Basic Info**: 9 form fields (name, SKU, description, 5 dropdown selects for lookups, UOM)
   - **Tab 2 — Variations**: Toggle `has_variation`, add attribute rows (name + comma-separated values), auto-generated SKU combination preview grid
   - Edit mode: loads existing item data, master_sku is readonly
   - Validation: required fields, max length enforcement

3. **Reusable DataTable** (`src/components/common/DataTable.tsx`)
   - Generic `<T>` component with typed columns
   - Pagination controls (prev/next, page size selector, "Showing X-Y of Z")
   - Optional search bar, row expansion, header actions slot
   - Consistent Tailwind styling matching project patterns

4. **Sidebar Navigation**
   - New "Catalog" collapsible group with `SubMenu` (react-pro-sidebar)
   - "Items" link with active state detection for `/catalog/*` paths

### New Dependencies
- `react-hook-form` (multi-tab form with dynamic arrays)

### Files Created
- `frontend/src/components/common/DataTable.tsx`
- `frontend/src/components/items/ItemFilters.tsx`
- `frontend/src/pages/ItemsListPage.tsx`
- `frontend/src/pages/ItemFormPage.tsx`

### Files Modified
- `frontend/src/api/base_types/items.ts` — added `ItemRead`, `ItemCreate`, `ItemUpdate`, `PaginatedResponse<T>`
- `frontend/src/api/base/items.ts` — added 5 item CRUD functions
- `frontend/src/App.tsx` — added 3 catalog routes
- `frontend/src/components/layout/MainLayout.tsx` — added Catalog SubMenu nav group

### Build
- Production: 488.06 kB JS, 24.11 kB CSS (zero errors)

---

## [PRE-ALPHA v0.5.3 | 2026-02-27 ~00:30] — Settings Page with Item Attributes CRUD

**What changed:** Added a new Settings page (`/settings`) with full CRUD for 5 item-attribute lookup tables: Status, ItemType, Category, Brand, and BaseUOM. Built a reusable `AttributeCard` component that handles inline add/edit/delete for any ID+name pair. Added 20 API functions with normaliser helpers to map varying backend field names to a generic `{ id, name }` interface. Settings nav item added to sidebar.

### New Files

| File | Purpose |
|------|---------|
| `src/api/base_types/items.ts` | `AttributeItem` interface — generic `{ id: number; name: string }` |
| `src/api/base/items.ts` | 20 API functions (4 per table) + 5 normaliser helpers |
| `src/components/settings/AttributeCard.tsx` | Reusable CRUD card: inline add/edit/delete, Enter/Escape keys, error display, loading spinner |
| `src/pages/SettingsPage.tsx` | Settings page with responsive grid (`md:grid-cols-2 xl:grid-cols-3`) of 5 AttributeCards |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/App.tsx` | Added `/settings` route inside protected group | Route to SettingsPage |
| `src/components/layout/MainLayout.tsx` | Added Settings nav item with `SettingsIcon` | Sidebar navigation entry |

### Design Decisions

- **Generic `AttributeItem` type**: All 5 tables have identical structure after normalisation — one component, one interface
- **Normaliser pattern**: Backend uses `status_id`/`status_name`, `uom_id`/`uom_name`, etc. Normalisers at the API boundary convert to uniform `{ id, name }`
- **`Promise.allSettled`**: Loads all 5 tables independently — one table's failure doesn't block others
- **`makeHandlers` factory**: Generates `onCreate`/`onUpdate`/`onDelete` callbacks for each table without repetition
- **MUI icons only**: `AddIcon`, `EditIcon`, `DeleteIcon` from `@mui/icons-material` — consistent with existing icon approach

### Build Result

- TypeScript: zero errors
- Production build: 425.02 kB JS (+8 kB from 5 new API functions + SettingsPage), 16.62 kB CSS

---

## [PRE-ALPHA v0.5.1.6 | 2026-02-26 ~23:30] — Convert layouts/ + components/ to Tailwind, remove MUI theme

**What changed:** Migrated MainLayout, ProtectedRoute, and PageHeader from MUI to native HTML + Tailwind. Removed MUI `ThemeProvider` and `theme.ts` — all design tokens now in `index.css`. Created `useIsMobile` hook to replace MUI `useMediaQuery`. MUI icons retained. JS bundle dropped from 466 kB to 417 kB (-49 kB).

### Components Converted

| Component | MUI Components Removed |
|-----------|----------------------|
| `MainLayout.tsx` | Box, AppBar, Toolbar, Typography, IconButton, useMediaQuery, useTheme |
| `ProtectedRoute.tsx` | Box, CircularProgress |
| `PageHeader.tsx` | Box, Typography |

### New Files

| File | Purpose |
|------|---------|
| `src/hooks/useIsMobile.ts` | Replaces MUI `useMediaQuery` using native `window.matchMedia` |

### Files Deleted

- `MainLayout.styles.ts`, `ProtectedRoute.styles.ts`, `PageHeader.styles.ts`, `common.styles.ts`, `theme/theme.ts`

### MUI Status

- **Still used**: `@mui/icons-material` (8 icons across MainLayout + LoginPage)
- **Removed from app code**: ThemeProvider, CssBaseline, all MUI components (Box, AppBar, Typography, etc.)
- **Kept as peer deps**: `@mui/material`, `@emotion/react`, `@emotion/styled` (required by `@mui/icons-material`)

---

## [PRE-ALPHA v0.5.1.5 | 2026-02-26 ~23:00] — Convert pages/ to Tailwind CSS

**What changed:** Migrated all 6 page components from MUI to native HTML + Tailwind utility classes. JS bundle dropped from 561 kB to 466 kB (-96 kB) by removing MUI component imports from pages.

### Pages Converted

| Page | MUI Components Removed |
|------|----------------------|
| `LoginPage.tsx` | Box, Card, TextField, Button, Typography, Alert, IconButton, InputAdornment, CircularProgress |
| `NotFoundPage.tsx` | Box, Typography, Button |
| `DashboardPage.tsx` | Box, Card, CardContent, Grid, Typography |
| `OrderImportPage.tsx` | Box, Alert |
| `ReferencePage.tsx` | Box, Alert |
| `MLSyncPage.tsx` | Box, Alert |

### Custom CSS Added to `index.css`

| Class | Purpose |
|-------|---------|
| `.login-blob--*` (5 variants) | Decorative gradient circles for login panel |
| `.form-input` / `.form-input--error` | Styled text inputs with focus/error states |
| `.form-label` / `.form-helper` | Input labels and helper text |

### Files Deleted

- `LoginPage.styles.ts`, `NotFoundPage.styles.ts` — replaced by Tailwind classes

---

## [PRE-ALPHA v0.5.1.4 | 2026-02-26 ~22:00] — Add Tailwind CSS v4 as Base Styling Framework

**What changed:** Installed Tailwind CSS v4 with Vite plugin, created base CSS template with project theme tokens, and established ground rule #10 for Tailwind as the new styling standard.

### Setup

| Step | Detail |
|------|--------|
| Install | `tailwindcss` + `@tailwindcss/vite` |
| Vite plugin | Added `tailwindcss()` to `vite.config.ts` plugins |
| Base CSS | `src/index.css` — `@import "tailwindcss"` + `@theme` with all project design tokens |
| Entry point | `main.tsx` imports `index.css`; `CssBaseline` removed (Tailwind preflight replaces it) |

### Available Tailwind Theme Classes

| Class Pattern | Maps To |
|---------------|---------|
| `bg-primary`, `text-primary` | #1565C0 |
| `bg-secondary`, `text-secondary` | #FF8F00 |
| `bg-background` | #F5F7FA |
| `bg-surface` | #FFFFFF |
| `text-text-primary` | #1A1A2E |
| `text-text-secondary` | #555770 |
| `bg-error`, `bg-success`, `bg-warning`, `bg-info` | Semantic colors |
| `font-sans` | Montserrat |
| `rounded-default`, `rounded-card` | 8px, 12px |
| `shadow-card`, `shadow-appbar` | Project shadows |

---

## [PRE-ALPHA v0.5.1.3 | 2026-02-26 ~21:00] — Extract Inline Styles to Separate Files

**What changed:** Extracted all inline MUI `sx` styles from 5 React components into co-located `*.styles.ts` files using typed `SxProps<Theme>` exports. Enforces ground rule #8.

### New Style Files

| File | Exports |
|------|---------|
| `src/styles/common.styles.ts` | `centeredFullPage`, `centeredContentArea` — shared layout primitives |
| `src/pages/LoginPage.styles.ts` | 18 exports — blob helper, form panels, branding, buttons |
| `src/layouts/MainLayout.styles.ts` | 10 exports — sidebar, AppBar, page content, react-pro-sidebar props |
| `src/pages/NotFoundPage.styles.ts` | 3 exports — page root (re-export), error code, error message |
| `src/components/auth/ProtectedRoute.styles.ts` | 1 export — loading container (re-export) |
| `src/components/common/PageHeader.styles.ts` | 1 export — header container |

### Refactored Components

| Component | Inline `sx` removed | Pattern |
|-----------|---------------------|---------|
| `LoginPage.tsx` | 16+ | `import * as styles from './LoginPage.styles'` |
| `MainLayout.tsx` | 9+ | `import * as styles from './MainLayout.styles'` |
| `NotFoundPage.tsx` | 3 | `import * as styles from './NotFoundPage.styles'` |
| `ProtectedRoute.tsx` | 1 | `import * as styles from './ProtectedRoute.styles'` |
| `PageHeader.tsx` | 1 | `import * as styles from './PageHeader.styles'` |

---

## [PRE-ALPHA v0.5.1 | 2026-02-26 ~12:00] — Login Page + Authentication Flow

**What changed:** Added a full login page with dark-themed UI, authentication context with JWT token management, protected routes, and integration with the new backend `POST /api/v1/auth/login` endpoint.

### Changes Made

| File | Change | Why |
|---|---|---|
| `src/pages/LoginPage.tsx` (new) | Full-page login UI: dark background, decorative blobs panel, email/password form with validation, show/hide password toggle, error alerts | Matches reference design with WOMS branding and project color theme |
| `src/contexts/AuthContext.tsx` (new) | `AuthProvider` + `useAuth()` hook: token in localStorage, /me validation on mount, login/logout functions | Global auth state management; prevents flash of login on page reload |
| `src/components/auth/ProtectedRoute.tsx` (new) | Route guard: redirects to /login if not authenticated, shows spinner while loading | Protects all dashboard routes from unauthenticated access |
| `src/types/auth.ts` (new) | `LoginRequest`, `LoginResponse`, `AuthUser` TypeScript interfaces | Type safety for auth API interactions |
| `src/api/auth.ts` (new) | `login()` and `getMe()` API functions | Axios calls to backend auth endpoints |
| `src/api/client.ts` | Activated Bearer token injection; added 401 redirect handler | Token auto-injected; expired tokens trigger login redirect via `window.location.hash` |
| `src/main.tsx` | Wrapped App in `<AuthProvider>` inside HashRouter | Auth context needs router hooks; available to all components |
| `src/App.tsx` | `/login` route outside MainLayout; all others wrapped in `<ProtectedRoute>` | Login has no sidebar; dashboard requires auth |

### Design Decisions

- **Dark background (#1A1A2E)** for login page matches project text.primary color
- **Decorative blobs** use primary (#1565C0) and secondary (#FF8F00) from theme
- **HashRouter** — login redirect uses `window.location.hash` from Axios interceptor (outside React context)
- **localStorage** for token storage — simpler than cookies for SPA + Vite proxy setup
- **"Forgot Password" and "Request Account"** are placeholder buttons (not functional yet)

---

## [PRE-ALPHA v0.5.0 | 2026-02-25 ~15:00] — Frontend Project Scaffold

**What changed:** Created the `frontend/` directory with a complete React + Vite + TypeScript scaffold, including MUI theming, routing, sidebar layout, API client layer, type definitions, and placeholder pages.

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `frontend/` | New Vite + React + TypeScript project scaffold | Monorepo structure prepared in v0.4.0; this is the frontend sibling to `backend/` |
| `frontend/vite.config.ts` | Proxy `/api` to `http://localhost:8000`, base `./` for Electron compat | Dev proxy avoids CORS issues; relative base enables Electron file:// loading |
| `frontend/index.html` | Montserrat font via Google Fonts CDN, updated title | User-specified font; descriptive page title |
| `frontend/src/theme/theme.ts` | MUI theme: Montserrat, custom palette, button/checkbox/alert overrides | Light-mode theme with scalable ThemeProvider for future dark mode |
| `frontend/src/main.tsx` | StrictMode + ThemeProvider + CssBaseline + HashRouter | HashRouter for Electron compat; ThemeProvider for consistent styling |
| `frontend/src/App.tsx` | Route definitions: /, /orders/import, /reference, /ml, 404 | Maps all backend features to frontend pages |
| `frontend/src/layouts/MainLayout.tsx` | react-pro-sidebar with collapsible nav, responsive AppBar | Sidebar navigation with Material Icons, mobile-responsive |
| `frontend/src/api/client.ts` | Axios instance with base URL, response/request interceptors | Centralised HTTP client with error handling |
| `frontend/src/api/orders.ts` | `importOrders()` — multipart/form-data matching backend contract | Matches `POST /api/v1/orders/import` form fields exactly |
| `frontend/src/api/reference.ts` | `loadPlatforms()`, `loadSellers()`, `loadItems()` | Matches backend reference router form field names |
| `frontend/src/api/mlSync.ts` | `syncStaging()`, `initSchema()` | Matches backend ML sync router JSON contract |
| `frontend/src/api/health.ts` | `checkHealth()` | Simple health check endpoint |
| `frontend/src/types/*.ts` | TypeScript interfaces for all API contracts + JSONB columns | Type safety for all backend interactions |
| `frontend/src/services/dataService.ts` | Multi-DB toggle service layer (woms_db / ml_woms_db) | Forward-looking abstraction for database context switching |
| `frontend/src/hooks/useD3.ts` | D3 + useRef integration hook | Prevents D3/React virtual DOM conflicts |
| `frontend/src/components/common/PageHeader.tsx` | Reusable page header component | Consistent heading style across all pages |
| `frontend/src/pages/*.tsx` | 5 placeholder pages (Dashboard, OrderImport, Reference, MLSync, 404) | Skeleton pages ready for feature implementation |

### Packages Installed

| Package | Version | Purpose |
|---|---|---|
| `@mui/material` | 6.x | UI component library |
| `@emotion/react` | 11.x | MUI styling engine |
| `@emotion/styled` | 11.x | MUI styled components |
| `@mui/icons-material` | 6.x | Material Design icons |
| `react-router-dom` | 7.x | Client-side routing (HashRouter) |
| `react-pro-sidebar` | 1.x | Collapsible sidebar navigation |
| `axios` | 1.x | HTTP client for API calls |
| `@faker-js/faker` | 9.x | Mock data generation |
| `d3` | 7.x | Data visualization |
| `@types/d3` | 7.x | TypeScript definitions for D3 |

---
