# WOMS Version Update Log

Version scheme: `PRE-ALPHA vX.Y.Z`
- X — major milestone (0 = pre-alpha)
- Y — feature increment
- Z — fix / patch / minor addition

---

## [PRE-ALPHA v0.11.0 | 2026-03-25 00:00] — Enhanced Stock-In Verification: Print → Scan → Reconcile

**WHY:** The receiving workflow treated printing labels and scanning barcodes as interchangeable — printing could accidentally count items as "in stock." For serialized items, we need a verification gate that separates intent (print = "Pending Arrival") from action (scan = stock officially increases), with duplicate-scan blocking, void-scan rectification, and mandatory reconciliation before completion.

**New files:**
- `backend/app/services/stock_in_verification.py` — Core service: `generate_stock_lots()`, `verify_scan()`, `void_lot()`, `get_reconciliation()`, `bulk_void_pending_lots()`
- `backend/alembic/versions/20260325_0000_00_ef56g7h8i9j0_link_stock_lots_to_receiving.py` — Adds `receiving_session_id`, `receiving_line_id` FK columns + indexes to `stock_lots`
- `frontend/src/pages/warehouse/inventory/movements/PrintLabelsModal.tsx` — Generate labels with quantity + location, display barcodes for printing
- `frontend/src/pages/warehouse/inventory/movements/VoidScanModal.tsx` — Void specific StockLot with mandatory reason selection
- `frontend/src/pages/warehouse/inventory/movements/ReconciliationPanel.tsx` — Per-line printed vs scanned vs missing breakdown, completion gate
- `frontend/src/pages/warehouse/inventory/movements/StockLotTable.tsx` — Expandable table of individual StockLots with status badges + void action
- `frontend/src/pages/warehouse/inventory/movements/SerialScanFeedback.tsx` — Success/duplicate/voided visual feedback after serial scans

**Modified (backend):**
- `backend/app/models/warehouse.py` — Added `receiving_session_id`, `receiving_line_id` FK fields + indexes to `StockLot` model
- `backend/app/routers/receiving.py` — 5 new endpoints: `POST print-labels`, `POST scan-serial`, `POST lots/{id}/void`, `GET reconciliation`, `GET lots`; modified `POST scan` (auto-routes serialized items to verification), `PATCH complete` (serialized reconciliation gate, only verified lots count), `PATCH cancel` (bulk-voids pending lots), `PATCH count` (blocks manual edit for serialized items)
- `backend/app/schemas/receiving.py` — New schemas: `PrintLabelsRequest/Response`, `StockLotRead`, `SerialScanResponse`, `VoidScanRequest`, `ReconciliationLineRead/ReportRead`; added `is_serialized` to `ReceivingLineRead` and `ReceivingScanResponse`

**Modified (frontend):**
- `frontend/src/api/base_types/receiving.ts` — Added `StockLotRead`, `PrintLabelsRequest/Response`, `SerialScanResponse`, `VoidScanRequest`, `ReconciliationLine/Report`, `VerificationStatus` type; added `is_serialized` to `ReceivingLineRead` and `ReceivingScanResponse`
- `frontend/src/api/base/receiving.ts` — 5 new API functions: `printLabels()`, `scanSerialBarcode()`, `voidStockLot()`, `getReconciliation()`, `listSessionLots()`
- `frontend/src/pages/warehouse/inventory/movements/StockInPanel.tsx` — Serialized lines show "Print Labels" + "View Lots" instead of "Edit Count"; qty field disabled; serial scan feedback; reconciliation panel auto-shown for sessions with serialized items
- `frontend/src/pages/warehouse/inventory/MovementItemRow.tsx` — Qty field disabled (grayed out) for serialized items with tooltip
- `frontend/src/api/base_types/warehouse.ts` — Added `is_serialized?` to `MovementItemEntry`

---

## [PRE-ALPHA v0.10.0 | 2026-03-23 03:00] — Variation-Level Inventory Tracking & Barcode Resolution

**WHY:** Stock was tracked at the item level only — all variations shared a single pooled count per location. This made per-variation allocation, picking, and stock counts impossible. The domain rule states "variations are allocated individually to different locations." This release adds `variation_sku` to 7 inventory tables, a centralized barcode resolution service (item barcode + SKU + variation barcode via GIN-indexed JSONB query), and variation awareness across all schemas, routers, and frontend types.

**New:**
- `backend/app/services/barcode_resolver.py` — `resolve_barcode()`, `resolve_variation_label()`, `BarcodeResolution` schema
- `GET /items/resolve-barcode?barcode=XXX` — universal barcode lookup endpoint
- Migration `cd34e5f6g7h8` — adds `variation_sku VARCHAR(100)` to 7 tables with COALESCE-based unique indexes

**Modified (backend):** transfer.py, stock_check.py, disposal.py, warehouse.py (routers); transfer.py, warehouse.py, stock_check.py, receiving.py, disposal.py (schemas); warehouse.py, transfer.py, stock_check.py, receiving.py, disposal.py (models)

**Modified (frontend):** base_types/items.ts, base_types/warehouse.ts, base_types/transfer.ts, base_types/receiving.ts, base_types/disposal.ts, base/items.ts; MovementItemGrid, RecordMovementDrawer, InterWarehousePanel, ConditionPanel, CourierPanel, MovementItemRow, useMovementStateMachine

---

## [PRE-ALPHA v0.9.7 | 2026-03-22 00:00] — Inter-Warehouse Transfer Enhancements: Packing Gate, Discrepancy Reports, Print TO

**WHY:** The existing transfer system lacked operational rigor in two key areas: (1) no packing confirmation gate — anyone could ship a transfer without verifying all items were physically packed, leading to short-shipments; (2) discrepancies at the receiving end were captured only as free-text notes, making root-cause analysis and trend detection impossible. This release adds a structured packing confirmation checklist (all items must be checked off before shipping), per-line discrepancy reasons on receipt (damaged_in_transit, missing_from_shipment, etc.), a JSONB discrepancy report snapshot at completion, a printable Transfer Order document with barcode, an incoming transfer schedule page, and a full transfer detail page with status timeline.

**Backend — Migration (`20260322_0000_00_x9y0z1a2b3c4`):**
- `warehouse_transfers`: added `packing_confirmed` (BOOLEAN, default false), `packing_confirmed_by` (FK users.user_id), `packing_confirmed_at` (TIMESTAMP), `receiver_notes` (TEXT), `discrepancy_report` (JSON)
- `warehouse_transfer_lines`: added `discrepancy_reason` (VARCHAR 100)

**Backend — Model (`backend/app/models/transfer.py`):**
- `WarehouseTransfer`: added packing_confirmed, packing_confirmed_by, packing_confirmed_at, receiver_notes, discrepancy_report fields
- `TransferLine`: added discrepancy_reason field

**Backend — Schemas (`backend/app/schemas/transfer.py`):**
- Updated `TransferVerifyLine` with `discrepancy_reason`, `TransferCompleteRequest` with `receiver_notes`
- Updated `TransferLineRead` with `discrepancy_reason`, `TransferRead` with packing/receiver fields, `TransferDetailRead` with discrepancy_report
- New schemas: `TransferPackingConfirm`, `TransferPrintData`

**Backend — Router (`backend/app/routers/transfer.py`):**
- New: `PATCH /{id}/confirm-packing` — confirm packing (sets packing_confirmed=true, by, at)
- New: `GET /{id}/print-data` — returns structured data for printing Transfer Order document
- New: `GET /incoming/{warehouse_id}` — incoming transfer schedule (draft/shipped destined for warehouse)
- Modified: `ship_transfer` — now requires packing_confirmed=true (gate)
- Modified: `verify_transfer` — saves per-line discrepancy_reason
- Modified: `complete_transfer` — saves receiver_notes + builds discrepancy_report JSONB snapshot

**Frontend — Types (`frontend/src/api/base_types/transfer.ts`):**
- Added `TRANSFER_DISCREPANCY_REASONS` constant, `TransferDiscrepancyReason` type, `TRANSFER_DISCREPANCY_LABELS`
- Added `TransferPackingConfirmRequest`, `TransferPrintData` interfaces
- Updated all read interfaces with new fields

**Frontend — API (`frontend/src/api/base/transfer.ts`):**
- Added `confirmPacking()`, `getTransferPrintData()`, `getIncomingSchedule()` functions

**Frontend — New Files:**
- `transfers/TransferDetailPage.tsx` + `.css` — full detail page with status timeline, lines table, action buttons
- `transfers/PackingConfirmationStep.tsx` — inline checklist for confirming packing
- `transfers/TransferPrintView.tsx` + `.css` — printable Transfer Order with barcode (react-barcode)
- `transfers/TransferDiscrepancyReport.tsx` — structured discrepancy report display
- `transfers/ReceiverSchedulePage.tsx` — incoming transfer schedule

**Frontend — Modified Files:**
- `TransferReceiptPage.tsx` — per-line discrepancy reason dropdowns + receiver_notes textarea
- `InterWarehousePanel.tsx` — View link, Pack action, packing indicator icon on status badges
- `App.tsx` — 3 new routes: `/inventory/transfers/:id`, `/inventory/transfers/:id/print`, `/inventory/incoming`

**Dependencies:**
- `react-barcode` — barcode rendering for Transfer Order print view

---

## [PRE-ALPHA v0.9.6 | 2026-03-21 00:00] — Ghost Inventory: Found Item Capture & Resolution in Stock Checks

**WHY:** During physical stock checks, warehouse staff sometimes discover items that have no system record at that location — "ghost inventory." Without a way to capture these finds inline, staff had to use side-channel notes or skip them entirely, leading to inventory blind spots. This feature adds ghost item capture during counting and a structured resolution workflow (create record / flag for review / dispose) during reconciliation, ensuring every found item is accounted for before inventory adjustments are finalized.

**Backend — Migration (`20260321_0000_00_w8x9y0z1a2b3`):**
- `stock_check_lines`: added `is_ghost_inventory` (BOOLEAN, default false), `found_location_id` (FK inventory_location.id), `found_item_notes` (TEXT), `ghost_resolution` (VARCHAR 50), `ghost_resolved_at` (TIMESTAMP), `ghost_resolved_by` (FK users.user_id)
- New index: `idx_scl_ghost` on (stock_check_id, is_ghost_inventory)

**Backend — Model (`backend/app/models/stock_check.py`):**
- `StockCheckLine`: added `is_ghost_inventory`, `found_location_id`, `found_item_notes`, `ghost_resolution`, `ghost_resolved_at`, `ghost_resolved_by` fields

**Backend — Schemas (`backend/app/schemas/stock_check.py`):**
- `StockCheckLineRead`: added ghost fields + `found_location_code`, `ghost_resolved_by_name`
- New schemas: `GhostItemCapture`, `GhostItemBatchCapture`, `GhostResolutionAction`, `GhostResolutionBatch`

**Backend — Router (`backend/app/routers/stock_check.py`):**
- `POST /stock-check/{id}/ghost-items` — capture found items (is_ghost_inventory=true, system_quantity=0, status "counted")
- `POST /stock-check/{id}/resolve-ghosts` — batch resolve ghost items with create_record / flag_for_review / dispose
- `POST /stock-check/{id}/adjust-inventory` — now returns 409 if unresolved ghost items exist (ghost gate)
- `_build_line_read` updated to fetch found_location_code and ghost_resolved_by_name

**Frontend — Types (`frontend/src/api/base_types/warehouse.ts`):**
- Added `GhostResolution` type, `GhostItemCapture`, `GhostItemBatchCapture`, `GhostResolutionAction`, `GhostResolutionBatch` interfaces
- Updated `StockCheckLineRead` with ghost fields

**Frontend — API (`frontend/src/api/base/warehouse.ts`):**
- Added `captureGhostItems()`, `resolveGhostItems()` functions

**Frontend — Components:**
- New: `GhostItemEntryForm.tsx` — item search (debounced) + location picker + quantity + notes; amber-themed slide-down form
- New: `GhostItemBanner.tsx` — amber inline label for ghost lines showing found location, resolution status, notes
- New: `GhostItemActionSelect.tsx` — per-line resolution dropdown (Create Record / Flag for Review / Dispose)
- New: `GhostInventoryResolutionPanel.tsx` — resolution table in reconciliation page with batch resolve
- Modified: `EditorPage.tsx` — "Found Item" button in toolbar; GhostItemEntryForm slide-down; ghost lines with amber styling + left border + GhostItemBanner
- Modified: `ReconciliationPage.tsx` — GhostInventoryResolutionPanel before adjustment table; "Adjust Inventory" blocked when unresolved ghosts; warning message for unresolved state

---

## [PRE-ALPHA v0.9.5 | 2026-03-20 00:00] — Stock In Enhancements: Source Types, Unexpected Items, Discrepancy Gate

**WHY:** Inbound goods receiving needed to distinguish between different source types (supplier shipments, customer returns, inter-warehouse transfers), track unexpected items discovered during counting, and block session completion until discrepancies are acknowledged — ensuring data integrity and audit trail for inventory adjustments.

**Backend — Migration (`20260320_0000_00_u6v7w8x9y0z1`):**
- `receiving_sessions`: added `source_type` (VARCHAR 30, default 'supplier_shipment'), `linked_return_id` (FK order_returns.id), `discrepancy_resolved` (BOOLEAN, default false), `discrepancy_notes` (TEXT)
- `receiving_lines`: added `is_unexpected` (BOOLEAN, default false), `unexpected_notes` (TEXT)
- New index: `idx_receiving_sessions_source_type`

**Backend — Model (`backend/app/models/receiving.py`):**
- `ReceivingSession`: added `source_type`, `linked_return_id`, `discrepancy_resolved`, `discrepancy_notes` fields
- `ReceivingLine`: added `is_unexpected`, `unexpected_notes` fields

**Backend — Schemas (`backend/app/schemas/receiving.py`):**
- `ReceivingSessionCreate`: added `source_type`, `linked_return_id`
- `ReceivingSessionRead`: added `source_type`, `linked_return_id`, `discrepancy_resolved`, `discrepancy_notes`
- `ReceivingLineRead`: added `is_unexpected`, `unexpected_notes`
- `ReceivingLineAdd`: added `is_unexpected`, `unexpected_notes`
- New schemas: `UnexpectedLineCreate`, `DiscrepancyReportCreate`

**Backend — Router (`backend/app/routers/receiving.py`):**
- `POST /receiving/{id}/lines/unexpected` — add unexpected item (is_unexpected=true, expected_qty=0)
- `POST /receiving/{id}/discrepancy-report` — submit notes + accept discrepancies to unlock completion
- `PATCH /receiving/{id}/complete` — now returns 409 if unresolved discrepancies or unexpected items exist
- `create_receiving_session` now passes `source_type` and `linked_return_id`
- `_session_to_dict` and `_enrich_line` helpers updated with new fields

**Frontend — Types (`frontend/src/api/base_types/receiving.ts`):**
- Added `ReceivingSourceType` union type, `UnexpectedLineCreate`, `DiscrepancyReportCreate` interfaces
- Updated `ReceivingLineRead`, `ReceivingSessionRead`, `ReceivingSessionCreate`, `ReceivingLineAdd`

**Frontend — API (`frontend/src/api/base/receiving.ts`):**
- Added `createUnexpectedLine()`, `submitDiscrepancyReport()` functions

**Frontend — Components:**
- New: `StockInSourceSelector.tsx` — toggle between Supplier Shipment / Customer Return / Inter-Warehouse with color-coded buttons
- New: `DiscrepancyReportModal.tsx` — full-screen modal showing discrepancy summary, per-line table, notes input; submits resolution to unlock completion
- Modified: `StockInPanel.tsx` — integrated source selector in create form; source type badge in session header + list; unexpected item badge on lines; 409 handler opens discrepancy modal; source column in session list

---

## [PRE-ALPHA v0.9.4 | 2026-03-19 02:00] — Auth Resilience: Persistent SECRET_KEY + Refresh Tokens

**WHY:** After code updates or server restarts, users were forced to re-login because the SECRET_KEY was auto-generated on every startup (invalidating all existing JWTs). This update makes the key persistent, adds refresh tokens for long-lived sessions, and implements a silent-refresh flow so users are never interrupted.

**Backend — Config (`backend/app/config.py`):**
- New `_persist_secret_key(key)` helper: when a SECRET_KEY is auto-generated, it is immediately written back to `.env` so it survives restarts
- Updated `generate_secret_key_if_missing` validator to call `_persist_secret_key()` on generation
- Startup log line in `main.py` confirms whether SECRET_KEY is persistent or ephemeral

**Backend — Database:**
- New table: `refresh_tokens` (id, token_hash SHA-256, user_id FK, expires_at, created_at, revoked_at, replaced_by)
- 3 indexes: `idx_refresh_tokens_user_id`, `idx_refresh_tokens_expires_at`, unique on `token_hash`
- New model: `RefreshToken` in `backend/app/models/users.py`
- Alembic migration: `20260319_0200_00_u6v7w8x9y0z1`

**Backend — Auth Service (`backend/app/services/auth.py`):**
- `create_refresh_token(user_id, session)` — generate + store hashed token
- `verify_refresh_token(token, session)` — validate, detect revoked-token reuse (security)
- `rotate_refresh_token(old_token, session)` — revoke old, issue new
- `revoke_user_refresh_tokens(user_id, session)` — bulk revoke (logout/password change)
- `cleanup_expired_refresh_tokens(session)` — delete expired rows (runs on startup)

**Backend — Auth Dependencies (`backend/app/dependencies/auth.py`):**
- `require_current_user` now returns distinct 401 codes: `"token_expired"` vs `"token_invalid"`
- Decodes JWT directly (no longer delegates to `decode_access_token` which swallows error types)

**Backend — Auth Endpoints (`backend/app/routers/auth.py`):**
- `POST /auth/login` — now returns `refresh_token` + `expires_in`; sets httpOnly cookie
- `POST /auth/refresh` — exchange refresh token for new access+refresh pair (no access token required)
- `POST /auth/logout` — revoke all refresh tokens + clear cookie
- Updated schemas: `TokenResponse` (+refresh_token, +expires_in), new `RefreshRequest`

**Frontend — API Client (`frontend/src/api/base/client.ts`):**
- Silent-refresh interceptor: on `"token_expired"` 401, automatically calls `/auth/refresh`
- Request queue pattern: concurrent failed requests are queued and replayed after refresh
- `"token_invalid"` 401 → immediate redirect to /login (can't recover)

**Frontend — Auth (`frontend/src/api/`):**
- Types: `LoginResponse` updated with `refresh_token` + `expires_in`
- API: added `refreshAccessToken()` and `logoutApi()` functions
- AuthContext: stores refresh_token in localStorage; `logout()` calls `/auth/logout` server-side

**Files created:**
- `backend/alembic/versions/20260319_0200_00_u6v7w8x9y0z1_add_refresh_tokens_table.py`

**Files modified:**
- `backend/app/config.py`, `backend/app/main.py`
- `backend/app/services/auth.py`, `backend/app/dependencies/auth.py`
- `backend/app/routers/auth.py`, `backend/app/schemas/auth.py`
- `backend/app/models/users.py`, `backend/app/models/__init__.py`
- `frontend/src/api/base/client.ts`, `frontend/src/api/base/auth.ts`
- `frontend/src/api/base_types/auth.ts`, `frontend/src/api/contexts/AuthContext.tsx`

---

## [PRE-ALPHA v0.9.3 | 2026-03-18 18:00] — Stock Location Management (Functional Zones + Occupancy Grid)

**WHY:** The warehouse location management needed server-side persistence for functional zone configurations (previously stored in localStorage) and a visual occupancy overview to help operators quickly identify bin utilization across the warehouse. This module adds the backend zone config table, occupancy API, and a visual grid view with slot management drawer.

**Backend — Database:**
- New table: `functional_zone_config` (id, warehouse_id FK, zone_key, zone_name, description, color, icon, mapped_sections JSONB, mapped_zones JSONB, is_active, sort_order, created_at, updated_at)
- UNIQUE constraint: `(warehouse_id, zone_key)`
- 2 indexes: `idx_fzc_warehouse`, `idx_fzc_active`
- Alembic migration: `20260319_0100_00_t5u6v7w8x9y0`
- New model: `FunctionalZoneConfig` in `backend/app/models/warehouse.py`
- Registered in `backend/app/models/__init__.py`

**Backend — API (3 new endpoints at `/api/v1/warehouse`):**
- `GET /{warehouse_id}/zones` — List functional zone configs
- `PUT /{warehouse_id}/zones` — Batch upsert (replace all) zone configs
- `GET /{warehouse_id}/locations/occupancy` — Per-location occupancy status (empty/reserved/occupied/full) with stock counts, slot counts, hierarchy info
- New schemas: `FunctionalZoneConfigCreate`, `FunctionalZoneConfigRead`, `FunctionalZoneConfigBatchRequest`, `LocationOccupancyRead`

**Frontend — Types + API:**
- `FunctionalZoneConfigCreate`, `FunctionalZoneConfigRead`, `OccupancyStatus`, `LocationOccupancyRead` types added to `warehouse.ts`
- `listFunctionalZones()`, `upsertFunctionalZones()`, `getLocationOccupancy()` API functions

**Frontend — Components:**
- `LocationOccupancyBadge.tsx` — Empty (gray) / Reserved (blue) / Occupied (green) / Full (amber)
- `LocationOccupancyGrid.tsx` — Visual card grid with filter tabs (all/occupied/reserved/empty/full), search, click-to-open drawer
- `LocationSlotDrawer.tsx` — Slide-over panel: slot assignments table, assign/remove item, item search, summary bar (stock/reserved/capacity)
- `FunctionalZoneConfig.tsx` — Migrated from localStorage to API (listFunctionalZones + upsertFunctionalZones), auto-save on toggle
- `LocationAllocationPage.tsx` — Added "Visual Grid" tab to existing view mode toggle, renders occupancy grid + slot drawer

**Files created:**
- `backend/alembic/versions/20260319_0100_00_t5u6v7w8x9y0_add_functional_zone_config.py`
- `frontend/src/pages/warehouse/inventory/shared/LocationOccupancyBadge.tsx`
- `frontend/src/pages/warehouse/locations/LocationOccupancyGrid.tsx`
- `frontend/src/pages/warehouse/locations/LocationSlotDrawer.tsx`

**Files modified:**
- `backend/app/models/warehouse.py`, `backend/app/models/__init__.py`
- `backend/app/schemas/warehouse.py`, `backend/app/routers/warehouse.py`
- `frontend/src/api/base_types/warehouse.ts`, `frontend/src/api/base/warehouse.ts`
- `frontend/src/pages/warehouse/inventory/allocation/FunctionalZoneConfig.tsx`
- `frontend/src/pages/warehouse/locations/LocationAllocationPage.tsx`

---

## [PRE-ALPHA v0.9.2 | 2026-03-18 16:00] — Disposal Module (Remove Stock Approval Workflow)

**WHY:** Warehouse operations needed a formal process for stock disposal (damaged goods, expired items, quality failures). The disposal module implements a two-step approval workflow: staff request → manager approval → execution (stock write-off). This prevents unauthorized stock removal and maintains a full audit trail.

**Backend — Database:**
- New table: `disposal_approvals` (id, warehouse_id, item_id, location_id, movement_id, quantity, reason, status, request_reference, requested_by, requested_at, approved_by, approved_at, disposed_at, notes, rejection_reason, edited_items JSONB, created_at, updated_at)
- 5 indexes: warehouse+status, requested_by, status, item, created_at
- Seeded `sys_sequence_config` row for `DISPOSAL_REQUEST` module
- Alembic migration: `20260319_0000_00_s4t5u6v7w8x9`
- New model: `DisposalApproval` in `backend/app/models/disposal.py`
- Registered in `backend/app/models/__init__.py`
- Added `DISPOSAL_REQUEST` to sequence service (`MODULE_TABLE_MAP`, `MODULE_DISPLAY_NAMES`, `ALLOWED_SEGMENTS`)

**Backend — API (7 endpoints at `/api/v1/disposal`):**
- `POST /` — Create disposal request (generates reference via sequence engine, validates stock)
- `GET /` — List disposals (paginated, filters: warehouse_id, status, requested_by)
- `GET /pending-approval` — Manager approval queue
- `GET /{id}` — Disposal detail with resolved names
- `POST /{id}/approve` — Approve (with optional qty adjustment) or reject (with reason)
- `POST /{id}/execute` — Execute approved disposal → creates Write Off movement + InventoryTransaction (outbound)
- `PATCH /{id}/cancel` — Cancel pending/rejected requests
- New schemas: `DisposalRequestCreate`, `DisposalApproveAction`, `DisposalApprovalRead` in `backend/app/schemas/disposal.py`

**Frontend — Types + API Client:**
- `frontend/src/api/base_types/disposal.ts` — TypeScript interfaces for all disposal types
- `frontend/src/api/base/disposal.ts` — 7 API functions matching backend endpoints

**Frontend — Pages:**
- `DisposalListPage.tsx` — DataTable with status filter tabs (All, Pending Approval, Approved, Disposed, Rejected, Cancelled), pagination, "New Disposal Request" button
- `DisposalRequestForm.tsx` — Item search (debounced), location selector, quantity, reason dropdown, notes textarea
- `DisposalDetailPage.tsx` — Full detail view with audit trail, manager actions (approve/reject/execute/cancel), quantity edit on approval, rejection modal
- Added `disposal` domain to `UnifiedStatusBadge` (5 statuses: pending_approval, approved, rejected, disposed, cancelled)
- Added "Remove Stock (Disposal)" card to `OperationsLandingPage` with live pending count badge

**Frontend — Routes (3 new):**
- `/inventory/operations/disposal` → DisposalListPage
- `/inventory/operations/disposal/new` → DisposalRequestForm
- `/inventory/operations/disposal/:id` → DisposalDetailPage

**Files created:**
- `backend/alembic/versions/20260319_0000_00_s4t5u6v7w8x9_add_disposal_approvals_table.py`
- `backend/app/models/disposal.py`, `backend/app/schemas/disposal.py`, `backend/app/routers/disposal.py`
- `frontend/src/api/base_types/disposal.ts`, `frontend/src/api/base/disposal.ts`
- `frontend/src/pages/warehouse/inventory/disposal/DisposalListPage.tsx`
- `frontend/src/pages/warehouse/inventory/disposal/DisposalRequestForm.tsx`
- `frontend/src/pages/warehouse/inventory/disposal/DisposalDetailPage.tsx`

**Files modified:**
- `backend/app/models/__init__.py`, `backend/app/services/sequence.py`, `backend/app/main.py`
- `frontend/src/App.tsx`, `frontend/src/pages/warehouse/inventory/shared/UnifiedStatusBadge.tsx`
- `frontend/src/pages/warehouse/inventory/operations/OperationsLandingPage.tsx`

---

## [PRE-ALPHA v0.9.1 | 2026-03-18 14:00] — Stock In: Document Upload + Quick Stock-In Form

**WHY:** Stock-in operations needed two enhancements: (1) the ability to attach supporting documents (invoices, delivery orders, packing lists, photos) to receiving sessions and inventory movements, and (2) a quick stock-in form for ad-hoc inbound stock without the full receiving session lifecycle.

**Backend — Database:**
- New table: `receiving_documents` (id, session_id, movement_id, file_name, original_name, file_path, file_size, mime_type, uploaded_by, uploaded_at)
- CHECK constraint: `chk_rcvdoc_parent` — at least one of session_id or movement_id must be set
- Indexes: `idx_rcvdoc_session`, `idx_rcvdoc_movement`
- Alembic migration: `20260318_0100_00_r3s4t5u6v7w8`
- New model: `ReceivingDocument` in `backend/app/models/receiving.py`
- Registered in `backend/app/models/__init__.py`

**Backend — API (5 new endpoints):**
- `POST /api/v1/receiving/{session_id}/documents` — Upload document to session
- `POST /api/v1/receiving/documents/movement/{movement_id}` — Upload document to movement
- `GET /api/v1/receiving/{session_id}/documents` — List session documents
- `GET /api/v1/receiving/documents/movement/{movement_id}` — List movement documents
- `DELETE /api/v1/receiving/documents/{document_id}` — Delete document (file + DB)
- File storage: local filesystem `backend/uploads/receiving/`, UUID-prefixed filenames, 10MB limit
- New schema: `ReceivingDocumentRead` in `backend/app/schemas/receiving.py`
- `ReceivingSessionDetailRead` now includes `documents` list
- Upload directory created in `backend/app/main.py`

**Frontend — Quick Stock In (`QuickStockInForm.tsx`):**
- New form accessible via "Quick Stock In" button on the Stock In panel
- Fields: destination location selector, reference number, item search + quantity table, notes, document upload
- Uses existing `POST /warehouse/movements/v2` (Receipt type) — no new stock logic
- After movement creation, uploads pending documents to the movement

**Frontend — Document Upload (`DocumentUploadZone.tsx`):**
- Drag-drop + click-to-browse file upload component
- Any file type, 10MB per-file limit, multiple files
- Two modes: pending (queue locally) and attached (server-side with download/delete)
- Integrated into session detail view and quick stock-in form

**Frontend — StockInPanel updates:**
- New `'quick'` view in PanelView union
- "Quick Stock In" button (amber, lightning bolt icon) in list header
- DocumentUploadZone added to session detail view (read-only when completed/cancelled)
- **New Receiving Session create form** now includes an item line picker — users can search and add expected items with quantities before creating the session (uses `ReceivingSessionCreate.lines` field)

**Files changed:**
- `backend/app/models/receiving.py`, `backend/app/models/__init__.py`
- `backend/alembic/versions/20260318_0100_00_r3s4t5u6v7w8_add_receiving_documents_table.py`
- `backend/app/schemas/receiving.py`, `backend/app/main.py`, `backend/app/routers/receiving.py`
- `frontend/src/api/base_types/receiving.ts`, `frontend/src/api/base/receiving.ts`
- `frontend/src/pages/warehouse/inventory/movements/DocumentUploadZone.tsx` (new)
- `frontend/src/pages/warehouse/inventory/movements/QuickStockInForm.tsx` (new)
- `frontend/src/pages/warehouse/inventory/movements/StockInPanel.tsx`

---

## [PRE-ALPHA v0.9.0 | 2026-03-18 12:00] — Bundle v2: Decoupled BOM + Variation-Level Components

**WHY:** Bundles were previously coupled to `PlatformSKU` + `ListingComponent` tables, requiring a platform/seller to create a bundle. This was architecturally wrong — bundles are a catalog/warehouse concept. Additionally, bundles could only reference whole items, not specific variations (e.g., "T-Shirt Red/M"). This release decouples bundles from platforms and adds variation-level component support.

**Backend — Database:**
- New table: `bundle_components` (id, bundle_item_id, component_item_id, variation_sku, quantity, sort_order, timestamps)
- UNIQUE constraint: `(bundle_item_id, component_item_id, variation_sku)` — same item can appear as whole + specific variations
- Indexes: `idx_bundle_comp_bundle`, `idx_bundle_comp_component`
- Alembic migration: `20260318_0000_00_q2r3s4t5u6v7` — creates table (data migration skipped: `platform_sku` has no `item_id` column)
- New model: `BundleComponent` in `backend/app/models/items.py`

**Backend — API Changes:**
- All 7 bundle endpoints rewritten to use `BundleComponent` instead of `PlatformSKU`/`ListingComponent`
- Removed: `platform_id`, `seller_id` from `BundleCreateRequest`
- Removed: `listing_id`, `platform_sku` from `BundleReadResponse`
- Added: `variation_sku` to `BundleComponentInput` (null = whole item, string = specific variation)
- Added: `variation_sku`, `variation_label`, `variation_barcode`, `image_url`, `sort_order`, `orphaned` to `BundleComponentRead`
- Variation validation: on create/update, verifies variation SKU exists in parent item's `variations_data` JSONB
- Orphan detection: on read, marks components whose variation SKU no longer exists in the parent item
- Bundle importer updated to use `BundleComponent` directly (no platform dependency)

**Frontend — ComponentSearch (variation picker):**
- When clicking an item with `has_variation: true`, shows inline variation picker panel
- Lists all variation combinations with label (e.g., "Color: Red / Size: M"), SKU, and barcode
- "Add whole item" option at top adds without specifying a variation
- Already-added variations shown as disabled with "Added" label
- Escape key / click outside dismisses picker
- `excludeIds` replaced with composite `excludeKeys` (`"item_id:variation_sku"`)

**Frontend — ComponentList:**
- Shows variation label beneath item name when `variation_sku` is set
- SKU column shows variation SKU when applicable
- Barcode column prefers `variation_barcode` over item barcode
- Warning badge for orphaned components ("Variation removed from parent item")

**Frontend — BundleFormPage:**
- `handleAddComponent` accepts `variationSku` parameter
- Component payload includes `variation_sku` field
- Edit mode loads full variation data from `BundleReadResponse`
- Removed `_existingListingId` state and all platform/seller references
- Validation uses composite keys for distinct component counting

**Frontend — BundlesListPage + ItemsListPage:**
- Expanded component rows show variation label, variation SKU, variation barcode, and orphaned warnings

**Files Changed:**
- `backend/app/models/items.py` — ADD `BundleComponent` model + Item relationships
- `backend/app/models/__init__.py` — IMPORT `BundleComponent`
- `backend/alembic/versions/20260318_0000_00_q2r3s4t5u6v7_*.py` — ADD migration
- `backend/app/schemas/items.py` — MODIFY bundle schemas
- `backend/app/routers/items.py` — REWRITE all 7 bundle endpoints + add helpers
- `backend/app/services/items_import/bundle_importer.py` — MODIFY to use BundleComponent
- `frontend/src/api/base_types/items.ts` — MODIFY bundle types
- `frontend/src/pages/bundles/ComponentSearch.tsx` — ADD variation picker
- `frontend/src/pages/bundles/ComponentList.tsx` — ADD variation display
- `frontend/src/pages/bundles/BundleFormPage.tsx` — MODIFY for v2 API
- `frontend/src/pages/bundles/BundlesListPage.tsx` — MODIFY expanded rows
- `frontend/src/pages/items/ItemsListPage.tsx` — MODIFY expanded rows

---

## [PRE-ALPHA v0.8.2 | 2026-03-16 22:00] — Inventory UX Simplification: 6 Nav Items → 3

**WHY:** The inventory section had 6 sidebar nav items pointing to separate pages, creating navigation fatigue. Simplified to 3 items (Stock Overview, Operations, Stock Checks) while preserving all features. Configuration pages moved to Settings.

**Frontend — New Pages:**
- `StockOverviewPage.tsx`: Unified dashboard merging stock levels table + active alerts + recent activity timeline in collapsible sections
- `OperationsLandingPage.tsx`: Card-grid launcher with 4 operation cards (Stock In, Stock Out, Transfers, Adjustments) with live count badges
- `StockInPage.tsx`, `StockOutPage.tsx`, `TransfersPage.tsx`, `AdjustmentsPage.tsx`: Page shells wrapping existing panels with breadcrumb navigation
- `InventorySettingsTab.tsx`: New Settings tab with 3 accordion sections (Allocation Rules, Alert Triggers, Data Export)

**Frontend — Modified Files:**
- `nav.config.tsx`: Inventory section reduced from 6 children to 3 (Stock Overview, Operations, Stock Checks)
- `App.tsx`: 8 new routes + 8 legacy redirect routes for backward compatibility
- `SettingsPage.tsx`: Added 'inventory' tab + URL ?tab= parameter support

**No backend changes. No database changes. No features removed.**

---

## [PRE-ALPHA v0.8.1 | 2026-03-16 26:00] — Inventory Workflow Restructure: Inbound/Outbound

**WHY:** The Movement Hub's 4 generic tabs (Inter-Warehouse, Intra-Warehouse, Courier/Shipping, Condition-Based) didn't map to real warehouse operations. Restructured to match actual workflow: Inbound (Stock In) and Outbound (Stock Out), with a new ReceivingSession backend model for goods verification.

**Bug Fixes:**
- Fixed React crash from Pydantic 422 validation errors rendered as JSX children (`client.ts` — normalize `detail` array to string)
- Bug 1 (Inter-Warehouse 500) and Bug 2 (blank Auto-Allocation page) were already applied in v0.7.0

**Database Changes (Migration `o0p1q2r3s4t5`):**
- CREATE `receiving_sessions`: Inbound goods verification sessions (title, supplier, PO ref, status FSM, summary stats)
- CREATE `receiving_lines`: Per-item expected/received quantities with discrepancy status
- Total tables: 52 → 54

**Backend (10 new endpoints):**
- Models: `ReceivingSession`, `ReceivingLine` in `backend/app/models/receiving.py`
- Router: `backend/app/routers/receiving.py` — full lifecycle (create, list, get, start, cancel, complete, count line, scan barcode, add line, discrepancy report)
- Completion auto-creates Receipt movements + updates InventoryLevel

**Frontend — Movement Hub Tab Restructure:**
- Old tabs: Inter-Warehouse | Intra-Warehouse | Courier/Shipping | Condition-Based
- New tabs: **Stock In** | **Stock Out** | Inter-Warehouse | **Adjustments**
- `StockInPanel.tsx`: Session list → Create session → Barcode scan + manual count → Discrepancy report → Complete
- `StockOutPanel.tsx`: Pending orders → Generate pick list → Verify stock (YES/NO per item) → Record shipment
- `AdjustmentsPanel.tsx`: Merged bin-to-bin relocation + condition adjustments with mode toggle
- `MovementHubPage.tsx`: Updated tab config, imports, and default tab
- `useMovementStateMachine.ts`: Updated `MovementCategory` type union
- `UnifiedStatusBadge.tsx`: Added `receiving` and `receiving_line` domains

**Frontend API Layer:**
- `frontend/src/api/base_types/receiving.ts`: 10+ TypeScript interfaces
- `frontend/src/api/base/receiving.ts`: 9 API functions (CRUD + lifecycle + scan + report)

**Files Changed:** 4 backend new, 3 backend modified, 3 frontend new, 5 frontend modified, 2 frontend API new

---

## [PRE-ALPHA v0.8.0 | 2026-03-16 25:00] — Stock Check (Cycle Count) V2 — Full Redo

**WHY:** The original stock check module was a monolithic 935-line page with no re-count workflow, no role-based UI separation, no audit trail, no structured discrepancy reasons, no manual adjustment stage, no threshold-based approvals, and no financial impact visibility. This redo transforms it into a professional-grade cycle count system with progressive disclosure, re-count loops, persisted multi-level approvals, manual inventory adjustments with manager confirmation, and clean role separation.

**Database Changes (Migration `n9o0p1q2r3s4`):**
- ALTER `stock_checks`: added `blind_count_enabled`, `recount_requested_at/by`, widened `status` VARCHAR(20→30)
- ALTER `stock_check_lines`: added `first_count`, `second_count`, `final_accepted_qty`, `discrepancy_reason`, `counted_by`, `recounted_by`, `is_reconciled`, `recount_requested`, `line_status`
- CREATE `stock_check_approvals`: L1/L2/L3 approval chain per check with status tracking
- CREATE `stock_check_threshold_config`: configurable per-warehouse approval thresholds (L1 always, L2 at 10/5, L3 at 50)
- CREATE `stock_check_line_history`: audit trail for every action on every line
- Total tables: 49 → 52

**Backend (15 endpoints — 8 modified, 7 new):**
- Models: `StockCheck`, `StockCheckLine` (expanded), `StockCheckApproval`, `StockCheckThresholdConfig`, `StockCheckLineHistory`
- New endpoints: `POST /{id}/approval`, `POST /{id}/recount-request`, `POST /{id}/recount`, `POST /{id}/adjust-inventory`, `GET /{id}/history`, `GET /thresholds/{wh_id}`, `PUT /thresholds/{wh_id}`
- Modified: `POST /` (accepts blind_count_enabled), `POST /{id}/count` (stores first_count + audit), `PATCH /{id}/review` (creates approval chain), `POST /{id}/reconcile` (REPLACED — sets final_accepted_qty, no inventory update)
- Status flow: DRAFT → IN_PROGRESS → PENDING_REVIEW ↔ RECOUNT_REQUESTED → COMPLETED / CANCELLED

**Frontend (role-based UI decomposition):**
- `StockCheckDetailShell.tsx`: route shell with status-driven rendering (replaces monolithic StockCheckDetailPage)
- `editor/EditorPage.tsx`: counter workspace — barcode scanning, progressive disclosure, blind count, guided count mode, re-count mode, focus mode, section filtering, audio feedback
- `editor/DiscrepancyReasonSelect.tsx`, `editor/RecountBanner.tsx`: editor sub-components
- `approver/ApproverPage.tsx`: review portal — exception-first filter, approval chain panel, cost impact columns, bulk actions (approve zero-variance, flag for re-count), line history drawer
- `manager/ReconciliationPage.tsx`: stock adjustment form — per-line final_accepted_qty + reason codes, summary (inbound/outbound/net), confirmation with checkbox + modal, two-step API (reconcile → adjust-inventory)
- `shared/ConfirmationModal.tsx`, `shared/VarianceFooterBar.tsx`, `shared/LineHistoryDrawer.tsx`: shared components
- `UnifiedStatusBadge.tsx`: added `recount_requested` status (purple)
- `StockCheckListPage.tsx`: added `recount_requested` tab, `blind_count_enabled` toggle in create modal, Mode column
- `App.tsx`: route updated to `StockCheckDetailShell`
- API client: 8 new functions (submitApproval, requestRecount, submitRecounts, reconcileLines, adjustInventory, getStockCheckHistory, getThresholdConfig, updateThresholdConfig)
- Types: 12+ new interfaces/types (StockCheckApprovalRead, StockCheckLineHistoryRead, StockCheckThresholdConfigRead, RecountRequest, RecountSubmission, ApprovalAction, LineReconcileAction, etc.)

---

## [PRE-ALPHA v0.7.1 | 2026-03-16 23:30] — Variation Barcodes + Bundle Component Barcode Display

**WHY:** The barcode generation system only supported parent item barcodes. Items with variations (e.g. Color/Size combinations) had no per-variation barcode, and bundle component lists didn't display their items' barcodes. This update extends the Reference Number Engine to generate unique barcodes for each variation combination (stored in JSONB) and exposes component barcodes throughout the bundle UI.

**Changes:**

- Backend `SequenceService`: added `generate_for_variation()` (JSONB `jsonb_set` update per combination) and `generate_variation_barcodes()` (batch helper); `bulk_generate()` now includes a second pass for variation barcodes on ITEMS module; `get_module_stats()` counts variation combinations missing barcodes
- Backend `items.py` router: `create_item()` and `update_item()` auto-generate variation barcodes when convention has `auto_apply_on_create`; all 4 bundle component queries (`get_bundle`, `create_bundle`, `update_bundle`, `restore_bundle`) now include `Item.barcode` in SELECT and pass it to `BundleComponentRead`
- Backend `items.py` schemas: `BundleComponentRead` gains `barcode: Optional[str]`
- Frontend `VariationBuilder.types.ts`: `VariationCombination` gains `barcode: string | null`
- Frontend `VariationBuilder.utils.ts`: `syncCombinations()` initializes new combos with `barcode: null`; `migrateOldFormat()` preserves existing barcodes
- Frontend `VariationBuilder.tsx`: read-only Barcode column in CombinationTable (monospace display or "Auto-generated" placeholder)
- Frontend `items.ts` types: `BundleComponentRead` gains `barcode: string | null`
- Frontend `BundlesListPage.tsx`: expanded component rows show Barcode column
- Frontend `BundleFormPage.tsx` + `ComponentList.tsx`: component list includes Barcode column; barcode passed from search and API load

---

## [PRE-ALPHA v0.7.0 | 2026-03-16 22:00] — Inventory Management System Overhaul

**WHY:** The inventory section operated as disconnected pages with duplicated utility code (extractErrorMessage in 6+ files, STATUS_BADGE maps in 4+ files) and inconsistent UX patterns. This overhaul transforms it into a unified warehouse orchestration system with Movement Hub (4 transaction types), enhanced reconciliation (blind count, ABC classification, multi-level approval), auto-allocation rule builder, configurable alert triggers, and analytics with d3 charts and ML-ready data export.

**Changes (33 new files, 5 modified):**

- Foundation: 3 shared hooks (barcode listener, movement FSM, virtualized list), 2 shared utilities (UnifiedStatusBadge, extractErrorMessage), react-window dependency
- Navigation: sidebar restructured to 6 items, legacy route redirects
- Movement Hub: 4-tab interface (Inter-Warehouse, Intra-Warehouse scan workflow, Courier manifest, Condition-Based) + history table
- Reconciliation: blind count toggle, ABC badges, approval gate (L1/L2/L3), variance summary; integrated into StockCheckDetailPage + StockCheckListPage (status filter tabs)
- Auto-Allocation: trigger-action rule builder, functional zone config (6 zone types), affinity slotting placeholder
- Alert Triggers: threshold config panel (CRUD with localStorage), alert dashboard (live feed, severity groups, quick-resolve)
- Analytics: event timeline (unified stream), d3 trend charts (movement volume, variance), CSV data export for ML pipelines

See `frontend-development-progress.md` for full file listing and technical details.

---

## [PRE-ALPHA v0.6.5 | 2026-03-16 12:00] — Items Barcode Auto-Generation Integration

**WHY:** The `barcode` field was added to the `items` table in v0.6.2 as part of the Reference Number Engine, but it was completely invisible to the application — missing from API schemas, responses, router logic, and the entire frontend. Items could not receive auto-generated barcodes on creation, and users had no way to see barcodes in the UI.

**Changes:**

Backend (2 files modified):
- Added `barcode` field to `ItemRead` and `BundleListItem` response schemas
- Exposed `barcode` in `_item_to_read()` helper function
- Added `SequenceService` auto-generation calls in `create_item()`, `create_bundle()`, `import_items_bulk()`, and `import_bundles_bulk()` — triggers when ITEMS convention has `auto_apply_on_create` enabled
- Generation is best-effort (try/except) — item creation succeeds even if no convention is active

Frontend (3 files modified):
- Added `barcode: string | null` to `ItemRead` TypeScript interface
- Added Barcode column to `ItemsListPage` DataTable (monospace, after Item column)
- Added read-only barcode display in `ItemFormPage` edit mode (above form fields, system-generated label)

---

## [PRE-ALPHA v0.6.4 | 2026-03-15 23:30] — Scan-to-Verify: Inter-Warehouse Transfers + Focus Mode

**WHY:** The warehouse had no way to ship stock between sites, generate a manifest, and verify receipt with discrepancy detection. Warehouse staff doing rapid barcode scanning also lacked a distraction-free scanning interface. This release adds a complete inter-warehouse transfer lifecycle (DRAFT → SHIPPED → RECEIVED → COMPLETED) with barcode-scannable manifests, a scan-to-verify receipt page with real-time expected-vs-scanned comparison, and a Focus Mode for the existing Stock Check page with audio feedback and dark theme.

**Changes:**

Backend (4 new files, 4 modified):
- New `WarehouseTransfer` + `TransferLine` models with full lifecycle state machine
- 8 REST endpoints under `/api/v1/transfers` (create, list, detail, by-reference lookup, ship, verify, complete, cancel)
- Ship deducts source stock; complete adds to destination inventory; cancel reverses if shipped
- Sequence engine extended with TRANSFER module for auto-generated reference numbers
- "Inter-Warehouse Transfer" movement type seeded
- Alembic migration `m8n9o0p1q2r3` creates both tables + indexes

Frontend (9 new files, 5 modified):
- `TransferListPage` — transfer dashboard with direction/status filters and status-based actions
- `TransferReceiptPage` — two-phase scan-to-verify (scan reference → scan items with real-time comparison)
- `VerificationGrid`, `TransferManifestHeader`, `DiscrepancyBadge` — supporting components
- `RecordMovementDrawer` extended — "Inter-Warehouse Transfer" type creates draft with target warehouse picker
- `StockCheckDetailPage` Focus Mode — fullscreen toggle, dark theme CSS, audio feedback (Web Audio API), dynamic re-sorting
- Routes + nav item added for `/inventory/transfers` and `/inventory/transfers/receive`

---

## [PRE-ALPHA v0.6.2 | 2026-03-15 20:00] — Configurable Reference Number Generation Engine

**WHY:** The WOMS system had no standardized, configurable reference number generation. Reference fields across tables were either manually entered or came from external platforms. This created inconsistent identifiers, no embedded metadata for barcode scanning, and no audit trail for numbering conventions. This engine provides centralized, segment-based reference number generation with individual configuration per module.

**Changes:**

Backend:
- Created `sys_sequence_config` table — versioned, segment-based convention registry with atomic counters (FOR UPDATE row lock), Absolute ID + Offset reset strategy, and per-module configuration
- Added `barcode` (VARCHAR 200, UNIQUE) to `items` table
- Added `internal_order_ref` (VARCHAR 100, UNIQUE) to `orders` table — only populated for manual/internal orders (not platform-imported)
- Added `trip_number` (VARCHAR 100, UNIQUE) to `delivery_trips` table
- Added `reference_number` (VARCHAR 100, UNIQUE) to `stock_checks` table
- Added `prevent_master_sku_update()` trigger — blocks master_sku changes after creation (SKU immutability)
- Created `SequenceService` — segment resolver, check digit computation (GS1 Mod-10), bulk generation
- Created 10 REST endpoints under `/api/v1/sequence` (modules, convention CRUD, preview, generate, bulk, reset)
- Seeded 9 default convention templates (ITEMS, ORDER, GRN, PO, DELIVERY, INVENTORY_MOVEMENT, STOCK_LOT_BATCH, STOCK_LOT_SERIAL, STOCK_CHECK)

Frontend:
- Added "Reference Numbers" tab (4th tab) to Settings page
- Module selector pill strip for 9 module configs
- Segment builder with drag-and-drop reorder, type dropdown (16 segment types), live configuration
- Live preview bar with debounced API calls and segment breakdown
- Convention version history with rollback
- Counter stats display with reset and bulk generate actions
- GS1 configuration section (conditional, shown for GS1-128/SSCC-18 formats)

**Modules:** ITEMS, ORDER, GRN, PO, DELIVERY, INVENTORY_MOVEMENT, STOCK_LOT_BATCH, STOCK_LOT_SERIAL, STOCK_CHECK
**Files created:** 16 new files (backend: system.py, sequence schemas/service/router, migration; frontend: types, API client, 8 UI components)
**Files modified:** items.py, orders.py, delivery.py, stock_check.py, triggers.py, main.py, SettingsPage.tsx, database_structure.md, web-api.md

---

## [PRE-ALPHA v0.6.1 | 2026-03-14 23:00] — Frontend File Reorganization

**WHY:** Page files and sub-components were not consistently grouped by function. Root-level pages (Dashboard, Login, etc.) lacked domain subfolders, the warehouse module mixed location and inventory concerns in a flat folder, and dashboard card components lived in `components/dashboard/` despite being used only by DashboardPage. This reorganization enforces the project's file organization rule: every page and its page-specific sub-components must live inside a dedicated subfolder under `pages/`.

**Changes:**
- Moved 7 root-level pages into domain subfolders: `pages/auth/`, `pages/dashboard/`, `pages/data/`, `pages/errors/`, `pages/common/`, `pages/orders/`
- Moved 4 dashboard card components from `components/dashboard/` to `pages/dashboard/` (page-specific, not shared)
- Split `pages/warehouse/` into `warehouse/locations/` (LocationSetupPage, LocationGeneratorPage, location_generator/) and `warehouse/inventory/` (InventoryLevelsPage, InventoryMovementsPage, InventoryAlertsPage, StockCheck*, RecordMovementDrawer, MovementItemGrid/Row)
- Deleted orphaned files: `pages/warehouse/WarehouseSelector.tsx` (zero imports), `pages/warehouse/WarehouseListPage.tsx` (zero imports), `components/hooks/useD3.ts` (unused)
- Updated all import paths in `App.tsx` (12 changes) and all moved files

**Files modified:** `App.tsx`, all moved page files (import path fixes)
**Files deleted:** 3 orphaned/unused files
**Files moved:** 25+ files into proper domain subfolders

---

## [PRE-ALPHA v0.6.0 | 2026-03-14 20:00] — Stock Movement v2, Stock Check & Location Allocation

**WHY:** The warehouse module needed three critical capabilities: (1) multi-item stock movements — the existing modal only supported one item per transaction, making bulk receipts/shipments tedious; (2) stock check (cycle count) — no way to verify physical inventory accuracy with a structured workflow; (3) location allocation (slotting) — no way to assign items to designated locations, enforce placement rules, or track capacity. These three features together form the foundation for an efficient, auditable warehouse operation.

**Feature A — Multi-Item Stock Movement (v2):**
- New `POST /api/v1/warehouse/movements/v2` endpoint accepting multiple items per movement
- Movement type rules: Receipt (dest only, inbound), Shipment (source only, outbound), Transfer (both, 2 txn/item), Adjustment, Return, Write Off
- Stock sufficiency validation for outbound movements
- Frontend: RecordMovementDrawer (520px slide-over), MovementItemGrid, MovementItemRow with debounced item search, available stock badges, quantity validation
- Replaced single-item modal in InventoryMovementsPage

**Feature B — Stock Check (Cycle Count):**
- New models: `StockCheck` (session), `StockCheckLine` (per-item-location line)
- Lifecycle: DRAFT → IN_PROGRESS → PENDING_REVIEW → COMPLETED / CANCELLED
- 8 endpoints under `/api/v1/stock-check`: create, list, detail, start (snapshot), count (batch), review, reconcile, cancel
- Reconciliation creates a "Cycle Count" InventoryMovement with transactions for accepted variances
- Frontend: StockCheckListPage (DataTable + create modal with scope filters), StockCheckDetailPage (counting grid with inline edits, variance review with accept/reject toggles, reconcile confirmation)
- Alembic migration: `k6l7m8n9o0p1`

**Feature C — Location Allocation (Slotting):**
- New model: `LocationSlot` — many-to-many item↔location mapping with is_primary, max_quantity, priority
- ML-ready fields: velocity_score, allocation_source (manual/ml_suggested/ml_auto), last_optimized_at
- Capacity fields on InventoryLocation: max_capacity, current_utilization
- 8 endpoints under `/api/v1/warehouse/{wh_id}/slots`: list, create, update, delete, by-item, by-location, bulk, capacity overview
- **Enforcement**: inbound movements (Receipt, Return, Transfer dest) blocked if no active LocationSlot exists for item+destination; slot max_quantity and location max_capacity validated
- Frontend: LocationAllocationPage with dual views (By Location / By Item), assign/edit/delete modals, capacity utilization bars
- Allocation hints integrated into RecordMovementDrawer destination dropdown ("Assigned" tags)

**Backend files created:**
- `backend/app/models/stock_check.py` — StockCheck + StockCheckLine models
- `backend/app/schemas/stock_check.py` — Request/response schemas
- `backend/app/routers/stock_check.py` — 8 endpoints with reconciliation logic
- `backend/alembic/versions/20260314_0000_00_k6l7m8n9o0p1_add_stock_check_and_location_slot_tables.py`

**Backend files modified:**
- `backend/app/models/warehouse.py` — Added LocationSlot model, max_capacity/current_utilization on InventoryLocation
- `backend/app/schemas/warehouse.py` — Added MovementLineItem, MultiItemMovementCreate, LocationSlot CRUD schemas, CapacityOverviewItem
- `backend/app/routers/warehouse.py` — Added location_id filter, POST /movements/v2, 8 slot endpoints, allocation enforcement
- `backend/app/main.py` — Registered stock_check router

**Frontend files created:**
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx`
- `frontend/src/pages/warehouse/MovementItemGrid.tsx`
- `frontend/src/pages/warehouse/MovementItemRow.tsx`
- `frontend/src/pages/warehouse/StockCheckListPage.tsx`
- `frontend/src/pages/warehouse/StockCheckDetailPage.tsx`
- `frontend/src/pages/warehouse/LocationAllocationPage.tsx`

**Frontend files modified:**
- `frontend/src/api/base_types/warehouse.ts` — Added StockCheck, LocationSlot, Movement v2 types
- `frontend/src/api/base/warehouse.ts` — Added 16 new API functions
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` — Replaced modal with drawer
- `frontend/src/App.tsx` — Added stock-check, stock-check/:id, allocation routes
- `frontend/src/components/layout/nav.config.tsx` — Added Location Allocation nav item

---

## [PRE-ALPHA v0.5.50 | 2026-03-14 12:00] — Unified Location Generator: streamlined single-view interface

**WHY:** The Site Generator page had a split personality — the left panel (BulkCreationWizard) managed existing/new modes with its own location tables, edit mode, drawers, and staging, while the right panel showed a separate read-only view. This made the workflow disjointed. The new architecture provides a streamlined single-view interface: left panel is purely a configuration sidebar for bulk generation; right panel is THE unified table showing all locations (saved + staged) with inline editing, row-level add/delete actions, duplicate detection, and a commit bar.

**Architecture:**
- New component directory: `frontend/src/pages/warehouse/location_generator/`
- `BulkCreationWizard.tsx` left untouched — still serves `LocationManagementSection` in Settings

**New files:**
- `frontend/src/pages/warehouse/location_generator/types.ts` — `UnifiedLocationRow` model, `RowStatus`, conversion helpers (`fromDbLocation`, `fromPreview`, `blankRow`, `recomputeCode`, `markDuplicates`)
- `frontend/src/pages/warehouse/location_generator/helpers.ts` — Extracted generator logic: `PreviewLocation`, `locationCode`, `LevelState`, `IntLevelState`, `buildPreviewSample`, `generateValues`, `toSegmentRange`, level constants
- `frontend/src/pages/warehouse/location_generator/ConfigPanel.tsx` — Left sidebar: LevelCards + IntLevelCards with checkbox/prefix/range/values config, Create Locations button, Reset. No splash screen, no mode toggle
- `frontend/src/pages/warehouse/location_generator/SectionAccordion.tsx` — Section accordion with inline-editable table rows, row-level trash/undo actions, "Add Row" button, duplicate warning tooltips, status-based row styling (saved/staged/edited/deleted)
- `frontend/src/pages/warehouse/location_generator/CommitBar.tsx` — Sticky bottom bar: pending change summary (new/edited/deleted counts), Save All + Discard buttons
- `frontend/src/pages/warehouse/location_generator/UnifiedLocationTable.tsx` — Right panel: search filter, stats bar, section accordions, commit bar

**Rewritten file:**
- `frontend/src/pages/warehouse/LocationGeneratorPage.tsx` — Full rewrite: unified state management (`dbLocations`, `stagedRows`, `editedFields`, `deletedIds`), `useMemo`-derived `unifiedRows` with duplicate detection, sequential save flow (create → update → delete), resizable split pane preserved

**Key features:**
1. No "Start Configuration" splash — config panel renders immediately
2. Generator injects staged rows into the unified table with "NEW" badges
3. All cells editable inline (transparent inputs with focus ring)
4. Row-level trash icon (hover-visible) + undo for deleted rows
5. "Add Row" button per section for manual row insertion
6. Real-time duplicate detection across all rows (red highlight + warning tooltip)
7. CommitBar appears when pending changes exist, summarizes counts
8. Save All: creates staged → updates edited → soft-deletes deleted → refreshes

---

## [PRE-ALPHA v0.5.45 | 2026-03-12 04:00] — Standardize display_code format: L/P prefixes for level/position

**WHY:** The previous code format joined all 6 hierarchy fields with `-` but rendered level and position as plain integers (e.g. `SEC-01-Z01-A01-B05-2-10`). This is ambiguous — a code with no bay but with a level could be misread. The new canonical format is `{section}-{zone}-{aisle}-{bay}-L{level}-P{position}` (e.g. `SEC-01-Z01-A01-B05-L2-P10`), matching the product specification example. The `L` and `P` prefixes make integer axes unambiguous at every truncation depth.

**Files modified — Backend:**
- `backend/app/models/triggers.py` — `generate_location_display_code()` updated: plain `NULLIF(level::text,'')` → `CASE WHEN NEW.level IS NOT NULL THEN 'L' || NEW.level::text ELSE NULL END` (same for position with `P` prefix); wrapped outer in `NULLIF(...,'')` for all-null case
- `backend/app/routers/warehouse.py` — All 3 Python display_code recalculation blocks updated: `str(loc.level)` → `f"L{loc.level}"`, `str(loc.position)` → `f"P{loc.position}"` (update_location, bulk_update_locations, rename_level endpoints)
- `backend/alembic/versions/20260312_0200_00_j5k6l7m8n9o0_standardize_display_code_format.py` — Migration: CREATE OR REPLACE trigger function + UPDATE all existing rows; applied to live DB

**Files modified — Frontend:**
- `frontend/src/pages/settings/warehouse_locations/BulkCreationWizard.tsx` — `locationCode()`: separator `.` → `-`; level as `L${n}`, position as `P${n}`
- `frontend/src/pages/settings/LocationManagementSection.tsx` — `computeCode()`: separator `.` → `-`; level as `L${level}`, position as `P${position}`

---

## [PRE-ALPHA v0.5.44 | 2026-03-12 03:00] — Phase 3 UI Labels: Warehouse Site tab, 7-column Preview Table, Rack/Bin purge

**WHY:** Final UI label pass for the hierarchy rename. The Settings "Warehouse" tab needed renaming to "Warehouse Site" to match the renamed DB table. The PreviewAccordion table in LocationManagementSection was still showing only 4 columns (Code/Zone/Aisle/Bay); it now shows all 7 (Code/Section/Zone/Aisle/Bay/Level/Position). The CsvLocationImport `rack`/`Rack` column alias was removed — all imports must now use the canonical `bay` column name.

**Files modified:**
- `frontend/src/pages/settings/SettingsPage.tsx` — TABS entry: `'Warehouse'` → `'Warehouse Site'`
- `frontend/src/pages/settings/LocationManagementSection.tsx` — PreviewAccordion table headers updated from `['Code','Zone','Aisle','Bay']` to `['Code','Section','Zone','Aisle','Bay','Level','Position']`; table rows extended with Section, Level, Position cells
- `frontend/src/pages/settings/warehouse_locations/CsvLocationImport.tsx` — Removed `raw['rack'] ?? raw['Rack']` fallback from `bay` field in `validateRow()`; canonical `bay` column is now the only accepted name

---

## [PRE-ALPHA v0.5.43 | 2026-03-12 02:00] — Full 6-level Generator: level + position in BulkCreationWizard & API

**WHY:** With `level` and `position` columns now in the DB, the bulk generation system and frontend wizard needed to fully expose these two integer axes. The backend generator was rewritten to handle both string segments (warehouse_section/zone/aisle/bay) and integer segments (level/position) in a single 6-axis Cartesian product. The frontend wizard gained two new `IntLevelCard` controls wired into live preview, request building, and reset logic.

**Files modified — Backend:**
- `backend/app/schemas/warehouse.py` — Added `IntegerRange` Pydantic model with `start`/`end` (ge=1, le=9999), `validate_range` (start≤end, max 500 values), and `expand() → list[int]`; extended `BulkGenerateRequest` with `level: Optional[IntegerRange]` and `position: Optional[IntegerRange]`; updated `at_least_one_range` validator to include both
- `backend/app/services/location_generator.py` — Full rewrite: `_STRING_SEGMENTS`/`_INT_SEGMENTS`/`_ALL_SEGMENTS` constants; `expand_ranges()` handles both string (SegmentRange) and integer (IntegerRange) axes with unified `itertools.product` over all 6; `bulk_generate_locations()` passes `level`/`position` as int|None to InventoryLocation; VARCHAR validation only on string segments
- `backend/app/routers/warehouse.py` — `list_locations`: added 7 Query params (warehouse_section, zone, aisle, bay, level, position, is_active), dynamic filter conditions, ORDER BY all 6 levels; `list_inventory_levels`: added 6 hierarchy drill-down params, extended search to match display_code

**Files modified — Frontend:**
- `frontend/src/api/base_types/warehouse.ts` — Added `IntegerRangeInput { start: number; end: number }`; extended `BulkGenerateRequest` with `level?: IntegerRangeInput` and `position?: IntegerRangeInput`
- `frontend/src/api/base/warehouse.ts` — `ListLocationsParams` extended with 7 filter fields; `listLocations()` accepts full params; `ListInventoryParams` extended with 6 hierarchy drill-down fields
- `frontend/src/pages/settings/warehouse_locations/BulkCreationWizard.tsx` — Added `IntLevelState`/`emptyIntLevel`/`IntAxis`/`INT_AXES`/`INT_AXIS_LABELS`; `buildPreviewSample` rewritten to handle separate string + integer Cartesian axes; `locationCode` extended for level/position; component gains `intLevels` state + `setIntLevel` callback; `anyEnabled`, `useMemo`, both `useEffect`s, `buildRequest`, and reset button all updated for integer axes; `IntLevelCard` component added; two `IntLevelCard` instances wired into JSX below Bay

---

## [PRE-ALPHA v0.5.42 | 2026-03-12 01:00] — Location Hierarchy Extended: level + position columns

**WHY:** The 4-level string hierarchy (warehouse_section → zone → aisle → bay) was insufficient for precise bin-level addressing. Two new integer columns (`level`, `position`) extend the hierarchy to 6 levels without adding more VARCHAR columns. `level` identifies the shelf tier within a bay (1=bottom); `position` identifies the slot within a level (1=leftmost). Both are optional — NULL means "not assigned at that depth".

**Files modified — Backend:**
- `backend/app/models/warehouse.py` — Added `level: Optional[int]` and `position: Optional[int]` fields to `InventoryLocation`; updated `uq_location_address` index expression to include `COALESCE(level::text,'')` and `COALESCE(position::text,'')`; updated `full_location_code` property to include integer levels
- `backend/app/schemas/warehouse.py` — Added `level`/`position` (Optional[int], ge=1) to `InventoryLocationCreate`, `InventoryLocationUpdate`, `InventoryLocationRead`, `LocationSummary`, `BulkLocationUpdateItem`
- `backend/app/models/triggers.py` — `generate_location_display_code()` updated with `NULLIF(level::text,'')` and `NULLIF(position::text,'')`
- `backend/app/routers/warehouse.py` — 3 display_code recalc blocks, 4 InventoryLocationRead constructors, `_location_summary`, and `duplicate_warehouse` INSERT...SELECT all updated for level/position
- `backend/alembic/versions/20260312_0100_00_i4j5k6l7m8n9_add_level_position_to_inventory_location.py` — Migration: ADD COLUMN level/position, DROP+RECREATE uq_location_address (6-column COALESCE), CREATE OR REPLACE trigger function

**Files modified — Frontend:**
- `frontend/src/api/base_types/warehouse.ts` — Added `level: number | null` / `position: number | null` to `InventoryLocationCreate`, `InventoryLocationUpdate`, `InventoryLocationRead`, `LocationSummary`, `BulkLocationUpdateItem`
- `frontend/src/pages/settings/LocationManagementSection.tsx` — `Draft` interface, `toDraft`, `isDirty`, `computeCode`, PATCH payload, table headers/cells updated for level/position
- `frontend/src/pages/settings/warehouse_locations/CsvLocationImport.tsx` — `CSV_TEMPLATE` extended to 7 columns; `ParsedRow` interface, `validateRow`, dedup key, API payload, preview table all updated

**Files modified — Docs:**
- `docs/official_documentation/database_structure.md` — `inventory_location` table schema updated: new columns, new index expression, updated trigger description, new example codes

---

## [PRE-ALPHA v0.5.41 | 2026-03-12 00:00] — Warehouse→Site Rename & Location Hierarchy Refactor

**WHY:** The `warehouse` table name was overloaded and the old 5-level hierarchy (`section > zone > aisle > rack > bin`) had an ambiguous `section` level. This update renames the DB table to `warehouse_site`, collapses the hierarchy to 4 levels (`warehouse_section > zone > aisle > bay`), removing `bin` entirely, and propagates the change throughout the full stack.

**Files modified — Backend:**
- `backend/app/models/warehouse.py` — `Warehouse.__tablename__` → `warehouse_site`; `InventoryLocation`: `section`→`warehouse_section`, `rack`→`bay`, removed `bin`; FK references updated; index names updated
- `backend/app/schemas/warehouse.py` — All DTOs updated: `section`→`warehouse_section`, `rack`→`bay`, `bin` removed; `RenameLevelRequest` valid levels updated; `BulkGenerateRequest` validator message updated
- `backend/app/routers/warehouse.py` — Duplicate SQL, all `InventoryLocationRead` constructors, `display_code` calcs, subtree params, rename level dict, `_location_summary` — all updated to 4-level hierarchy
- `backend/app/models/triggers.py` — `trg_warehouse_timestamp` trigger now references `warehouse_site`; `generate_location_display_code` uses `warehouse_section`, `zone`, `aisle`, `bay`
- `backend/app/services/location_generator.py` — `_SEGMENTS` updated to 4 levels; `InventoryLocation` constructor updated
- `backend/app/services/location_tree.py` — Full rewrite for 4-level hierarchy; aisle nodes use `__bays`; format functions updated
- `backend/app/services/inventory_guard.py` — `_HIERARCHY_LEVELS` updated; `warehouse_section`/`bay` field refs updated
- `backend/alembic/versions/20260312_0000_00_h3i4j5k6l7m8_rename_warehouse_to_site_and_location_hierarchy.py` — Pre-written migration (RENAME TABLE, column renames, DROP COLUMN bin, index rebuild)

**Files modified — Frontend:**
- `frontend/src/api/base_types/warehouse.ts` — All interfaces updated: `warehouse_section`, `bay`, no `bin`; `LocationTreeNode.type` and `HierarchyLevel` unions updated
- `frontend/src/api/base/warehouse.ts` — `LocationSubtreeFilter` updated to 4-level fields
- `frontend/src/pages/settings/LocationManagementSection.tsx` — `Draft` interface, column headers, `computeCode`, grouping, API payload, search updated
- `frontend/src/pages/settings/warehouse_locations/BulkCreationWizard.tsx` — `Level` type, `LEVELS`, `LEVEL_LABELS`, `locationCode`, `buildRequest`, JSX labels, reset logic all updated to 4-level hierarchy
- `frontend/src/pages/settings/warehouse_locations/CsvLocationImport.tsx` — `CSV_TEMPLATE`, `ParsedRow` interface, `validateRow`, dedup key, `createLocation` payload, table headers/cells updated
- `frontend/src/components/layout/nav.config.tsx` — "Pattern Generator" → "Site Generator"
- `frontend/src/pages/settings/WarehouseSettingsTab.tsx` — Sub-tab label "Location Setup" → "Site Setup"

**Files modified — Docs:**
- `docs/planning_phase/Backend/10_warehouse_rename_hierarchy_refactor.plan.md` — Status: PENDING → COMPLETED

---

## [PRE-ALPHA v0.7.0 | 2026-03-11 26:00] — Order Details & Mass Ship Frontend + Backend Enhancements

**WHY:** The Orders section of the sidebar had only placeholder pages. Warehouse staff had no way to browse, search, or inspect orders from the frontend, and no way to perform bulk shipping operations. This update delivers two fully functional pages — Order Details (browse/search/filter/inspect orders with a slide-out drawer) and Mass Ship (3-step wizard for bulk fulfillment with tracking assignment). The backend was also enhanced with richer list queries (JOINs for platform/store names, date range filtering, warehouse filtering, sorting) and a new bulk-ship endpoint.

**Files created:**
- `frontend/src/pages/orders/OrderDetailsPage.tsx` — Order list page with DataTable, search, filters, row selection, drawer integration
- `frontend/src/pages/orders/OrderDetailsPage.css` — Page-specific styles
- `frontend/src/pages/orders/OrderViewDrawer.tsx` — Slide-out drawer for single order detail
- `frontend/src/pages/orders/OrderViewDrawer.css` — Drawer styles
- `frontend/src/pages/orders/OrderLineItemsTable.tsx` — Line items sub-table for drawer
- `frontend/src/pages/orders/OrderStatusBadge.tsx` — Order status + cancellation badge
- `frontend/src/pages/orders/FulfillmentStatusBadge.tsx` — Fulfillment status badge
- `frontend/src/pages/orders/PlatformBadge.tsx` — Platform identity badge
- `frontend/src/pages/orders/OrderFilters.tsx` — Filter bar component
- `frontend/src/pages/orders/OrderFilters.css` — Filter bar styles
- `frontend/src/pages/orders/MassShipPage.tsx` — 3-step wizard container
- `frontend/src/pages/orders/MassShipPage.css` — Wizard styles
- `frontend/src/pages/orders/ShipmentSelectionStep.tsx` — Step 1: order selection
- `frontend/src/pages/orders/TrackingAssignmentStep.tsx` — Step 2: tracking assignment
- `frontend/src/pages/orders/ReviewConfirmStep.tsx` — Step 3: review & confirm
- `docs/planning_phase/Frontend/08_order_details_mass_ship_plan.plan.md` — Planning document

**Files modified:**
- `backend/app/routers/orders.py` — Enhanced GET /orders with date/warehouse/sort params, platform/store JOINs, detail aggregates. Added POST /orders/bulk-ship
- `backend/app/schemas/orders.py` — Added enriched fields to OrderListItem
- `frontend/src/api/base_types/orders.ts` — Full type definitions for order domain
- `frontend/src/api/base/orders.ts` — All order API functions
- `frontend/src/App.tsx` — Registered order routes

---

## [PRE-ALPHA v0.6.9 | 2026-03-11 25:00] — Phase 3 Complete: Inventory Intelligence & Analytics (Steps 3.0–3.7)

**WHY:** After Phases 1 and 2 gave warehouse staff the ability to record multi-item movements and manage movement lifecycles, the system still lacked two critical capabilities: (1) real-time visibility into inventory health — staff had no way to quickly see which items are critically low, overstocked, or healthy, nor could they adjust threshold values without editing the database directly; (2) historical analytics — managers had no charts or trend data to understand movement patterns, identify top-moving items, or assess overall stock health. Phase 3 closes both gaps: inline threshold editing on the levels page puts control in warehouse operators' hands, while the analytics dashboard provides the data-driven insights needed for demand planning and operational decisions.

**Files created:**
- `frontend/src/pages/warehouse/useInventorySync.ts` — NEW: Custom hook wrapping `queryClient.invalidateQueries()` for keys: inventory-levels, inventory-alerts, inventory-movements, inventory-analytics. Ensures all inventory views stay in sync after any lifecycle change (approve, complete, cancel) or new movement recording.
- `frontend/src/pages/warehouse/DailyMovementChart.tsx` — NEW: d3 stacked bar chart (X=date, Y=count, color by movement type). Renders daily movement volume with hover tooltips.
- `frontend/src/pages/warehouse/MovementTypeBreakdown.tsx` — NEW: d3 donut chart with percentage legend showing distribution of movement types over the selected date range.
- `frontend/src/pages/warehouse/TopMovedItemsList.tsx` — NEW: Pure Tailwind ranked list with relative progress bars showing top N items by total quantity moved.
- `frontend/src/pages/warehouse/StockHealthSummary.tsx` — NEW: d3 donut chart using StockStatusBadge colour palette, with centre total label showing item count per stock status category.
- `frontend/src/pages/warehouse/InventoryAnalyticsPage.tsx` — NEW: 2x2 grid layout hosting all 4 chart cards. Date range selector with presets (7d, 30d, 90d, YTD, Custom). 3 parallel useQuery calls with TanStack React Query. Loading skeletons, empty states, warehouse selection guard.

**Files modified:**
- `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` — UPDATED: Added stock-status row colouring via ROW_TINT map (low=yellow/30, critical=red/30, out_of_stock=gray, overstock=blue/30). Added InlineNumberCell component for click-to-edit threshold fields (reorder_point, safety_stock, max_stock) with green flash on save. Integrated `useInventorySync` hook.
- `frontend/src/components/common/DataTable.tsx` — UPDATED: Added `rowClassName` prop for dynamic row styling (accepts row data, returns CSS class string).
- `frontend/src/api/base_types/warehouse.ts` — UPDATED: Added `MovementPerDay`, `TopMovedItem`, `StockHealthEntry`, `AnalyticsDateRange` types. Added `InventoryLevelUpdatePayload` type.
- `frontend/src/api/base/warehouse.ts` — UPDATED: Added `getMovementsPerDay()`, `getTopItems()`, `getStockHealth()` API functions. Added `updateInventoryLevel()` function.
- `backend/app/routers/warehouse.py` — UPDATED: Added 3 analytics endpoints (`GET /{warehouse_id}/analytics/movements-per-day`, `GET /{warehouse_id}/analytics/top-items`, `GET /{warehouse_id}/analytics/stock-health`). Added `PATCH /inventory-levels/{level_id}` endpoint.
- `backend/app/schemas/warehouse.py` — UPDATED: Added `MovementPerDayRead`, `TopMovedItemRead`, `StockHealthEntry`, `InventoryLevelUpdate` schemas.
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx` — UPDATED: Integrated `useInventorySync` hook for post-save cache invalidation.
- `frontend/src/pages/warehouse/MovementActionMenu.tsx` — UPDATED: Integrated `useInventorySync` hook for post-action cache invalidation.
- `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` — UPDATED: Integrated `useInventorySync` hook for post-resolve cache invalidation.
- `frontend/src/layout/nav.config.tsx` — UPDATED: Added "Analytics" nav entry under Inventory section (BarChartIcon, path `/inventory/analytics`).
- `frontend/src/App.tsx` — UPDATED: Added route `<Route path="/inventory/analytics" element={<InventoryAnalyticsPage />} />`.

---

## [PRE-ALPHA v0.6.8 | 2026-03-11 24:00] — Phase 2 Complete: MovementActionMenu, Status Tabs, Expandable Rows (Steps 2.7–2.9)

**WHY:** Phase 2 closes the loop on movement lifecycle UX. Staff could already see movement status (badge) and drill into details (expanded row), but had no way to act on movements — no approve, complete, or cancel buttons. The movements list also showed all statuses in one flat list with no way to filter. This update adds contextual lifecycle actions via a kebab dropdown menu, status filter tabs for quick list filtering, expandable rows with chevron indicators, and a backend `status` filter parameter — completing the full read + act workflow for movement lifecycle management.

**Files created:**
- `frontend/src/pages/warehouse/MovementActionMenu.tsx` — NEW: Kebab dropdown menu with contextual lifecycle actions (approve/complete/cancel) based on current movement status. Uses confirm dialogs before executing transitions. Portal-rendered to avoid table overflow clipping.

**Files modified:**
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` — UPDATED: Added status filter tabs (All/Pending/In Transit/Completed/Cancelled) that set the `status` query param. Added expandable rows with chevron toggle indicators and `MovementExpandedRow` integration. Added Status column with `MovementStatusBadge`. Added Actions column with `MovementActionMenu`. Refactored data fetching to include `status` filter parameter.
- `backend/app/routers/warehouse.py` — UPDATED: `GET /{warehouse_id}/movements` now accepts optional `status` query parameter to filter movements by lifecycle status (pending, in_transit, completed, cancelled). WHY: Without server-side filtering, the frontend would need to fetch all movements and filter client-side — wasteful for large datasets and incorrect with pagination.
- `frontend/src/api/base_types/warehouse.ts` — UPDATED: `ListMovementsParams` interface gains optional `status` field to pass the filter to the backend.

---

## [PRE-ALPHA v0.6.7 | 2026-03-11 23:55] — Movement Item Detail Frontend: Types, StatusBadge, ExpandedRow (Steps 2.5–2.6)

**WHY:** With the backend returning per-item transaction details for a movement (v0.6.6), the frontend needs types to consume the response, a status badge to visually distinguish movement states at a glance, and an expandable row component so users can drill into any movement row to see exactly which items moved between which locations — without leaving the movements table.

**Files created:**
- `frontend/src/pages/warehouse/MovementStatusBadge.tsx` — NEW: Colored pill component mapping movement status to visual cues (pending=yellow, in_transit=blue, completed=green, cancelled=gray). Extracted as a standalone component because status display is needed in both the movement list and the expanded detail row.
- `frontend/src/pages/warehouse/MovementExpandedRow.tsx` — NEW: Fetches `GET /movements/{id}/items` on mount, renders per-item transaction detail with item name, master SKU, location codes, quantity, and directional arrows for transfers. Handles loading spinner, error state, and empty state.

**Files modified:**
- `frontend/src/api/base_types/warehouse.ts` — UPDATED: added `MovementItemDetail` interface (item_id, item_name, master_sku, location_from, location_to, quantity, is_inbound)
- `frontend/src/api/base/warehouse.ts` — UPDATED: added `getMovementItems(id)` function calling `GET /warehouse/movements/{id}/items`

---

## [PRE-ALPHA v0.6.6 | 2026-03-11 23:45] — Movement Item Detail Endpoint (Steps 2.3–2.4)

**WHY:** The movements list shows one row per movement, but warehouse staff need to see exactly which items are in each movement and which locations they moved between. A dedicated endpoint returns enriched transaction details with location codes and item names, grouping outbound/inbound transfer pairs into single rows so transfers don't appear as two confusing separate entries.

**Files changed:**
- `backend/app/schemas/warehouse.py` — UPDATED: added `MovementItemDetailRead` schema (item_id, item_name, master_sku, location_from, location_to, quantity, is_inbound)
- `backend/app/routers/warehouse.py` — UPDATED: added `GET /warehouse/movements/{id}/items` endpoint; queries `InventoryTransaction` joined with `Item` and `InventoryLocation` for human-readable location codes; groups outbound/inbound pairs for transfer movements into single rows with both source and destination

**Key decisions:**
- Transfer grouping: outbound and inbound transactions for the same item are merged into one row with `location_from` + `location_to` populated — clearer than showing two separate rows
- Location codes returned instead of IDs for display convenience — avoids extra lookups on the frontend
- 404 if movement not found (consistent with lifecycle endpoints)

---

## [PRE-ALPHA v0.6.5 | 2026-03-11 23:30] — Movement Lifecycle Transition Endpoints + Frontend API

**WHY:** With movements now created as "pending" (v0.6.4), the system needs explicit lifecycle transition endpoints so warehouse staff can approve, complete, or cancel movements. Stock-level changes are tied to these transitions — outbound stock is deducted on approval (pending→in_transit), inbound stock is added on completion (in_transit→completed), and reversals happen on cancellation. This ensures inventory accuracy by linking stock mutations to deliberate human actions rather than automatic creation-time side effects.

**Files changed:**
- `backend/app/routers/warehouse.py` — UPDATED: added 3 PATCH endpoints: `/{id}/approve` (pending→in_transit, deducts outbound stock), `/{id}/complete` (in_transit→completed, adds inbound stock), `/{id}/cancel` (pending|in_transit→cancelled, reverses outbound deduction if already approved)
- `frontend/src/api/base/warehouse.ts` — UPDATED: added `approveMovement(id)`, `completeMovement(id)`, `cancelMovement(id)` API functions

**Key decisions:**
- Approve deducts outbound immediately so stock is reserved during transit
- Complete adds inbound so receiving warehouse sees stock only after physical receipt
- Cancel from in_transit reverses the outbound deduction (stock returns to source)
- Cancel from pending is a no-op on stock (nothing was deducted yet)

---

## [PRE-ALPHA v0.6.4 | 2026-03-11 23:00] — Movement Lifecycle: Pending Status on Create

**WHY:** Previously, `POST /warehouse/movements` immediately updated stock levels on creation. This is incorrect for a real warehouse workflow — movements should go through a lifecycle (pending → in_transit → completed) with stock changes tied to each transition. Setting status="pending" on creation means no stock is moved until the movement is explicitly approved, preventing premature inventory mutations.

**Files changed:**
- `backend/app/routers/warehouse.py` — UPDATED: `POST /warehouse/movements` now sets `status="pending"` on creation and no longer calls stock-level update logic; stock changes are deferred to the lifecycle transition endpoints (approve/complete/cancel)

---

## [PRE-ALPHA v0.6.3 | 2026-03-11 22:05] — Phase 1 Complete: Multi-Item Movement Drawer (Steps 1.6–1.7)

**WHY:** Wire the drawer into the live page and finalize Phase 1. The old single-item modal is removed entirely — users now record movements via the multi-item slide-over drawer.

**Files changed:**
- `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` — Removed: all modal state (showModal, formTypeId, formItemId, formItemSearch, itemResults, formRef, formNotes, txRows, saving, formError), modal handlers (openRecord, updateTx, addTxRow, removeTxRow, handleSubmit), modal JSX, and unused imports (CloseIcon, DeleteIcon, createMovement, listMovementTypes, listLocations, listItems, InventoryMovementCreate, InventoryTransactionCreate, InventoryLocationRead, MovementTypeRead, ItemRead). Added: `drawerOpen` state, `<RecordMovementDrawer>` with `onSuccess={fetchMovements}`.

**Phase 1 deliverable — complete feature set:**
- Multi-item movement drawer with zod cross-field validation
- Movement-type-aware location fields (Receipt/Shipment/Transfer/Adjustment)
- Product autocomplete searching inventory levels at the selected location
- Duplicate-item prevention, source ≠ destination validation
- Paired transfer transactions (outbound source + inbound dest)
- `tsc --noEmit` passes with zero errors

---

## [PRE-ALPHA v0.6.2 | 2026-03-11 21:40] — RecordMovementDrawer (Step 1.5)

**WHY:** This is the main UI surface for recording multi-item inventory movements. It replaces the old single-item modal with a slide-over drawer that supports movement-type-aware field visibility, multi-item rows, and paired transfer transactions.

**Files created:**
- `frontend/src/pages/warehouse/RecordMovementDrawer.tsx` — Slide-over drawer component: `FormProvider` + `useForm<MovementFormValues>` with zod resolver; fetches movement types + locations on open; movement-type-aware visibility (Receipt → destination only, Shipment → source only, Transfer → both, etc.); iterates items to create one `POST /warehouse/movements` per item; handles paired transactions for transfers (outbound from source + inbound to destination); loading spinner, error display, form reset on close
- `frontend/src/pages/warehouse/RecordMovementDrawer.css` — Backdrop overlay, right-slide panel (560px, cubic-bezier animation), header/body/footer layout, responsive location grid, button styles

**Key decisions:**
- One API call per item row (backend only supports single `item_id` per movement) — acceptable for typical 1–10 item movements; batch endpoint can be added later if performance matters
- `activeLocationId` passed to `MovementItemGrid` switches between source/destination depending on movement type — Receipt uses destination, everything else uses source
- Hidden location fields cleared via `useEffect` when type changes to prevent stale values from passing zod validation
- Drawer blocks close during submission to prevent accidental data loss

---

## [PRE-ALPHA v0.6.1 | 2026-03-11 21:10] — Inventory Enhancement Phase 1 (Steps 1.3–1.4)

**WHY:** Build the core UI components for the multi-item movement drawer — the item row (product autocomplete, stock display, quantity input) and the dynamic grid that manages rows via `useFieldArray`.

**Files created:**
- `frontend/src/pages/warehouse/MovementItemRow.tsx` — Single row component: debounced product search (300ms) against `listInventoryLevels` with `location_id` filter, selected-item chip display, available stock badge, quantity input with max validation, remove button
- `frontend/src/pages/warehouse/MovementItemRow.css` — Row styles: selected chip, search dropdown, stock badge pill
- `frontend/src/pages/warehouse/MovementItemGrid.tsx` — Grid container using `useFieldArray` for dynamic add/remove rows, table header, "Add Item" dashed button, minimum-1-row enforcement, form-level error display from zod superRefine
- `frontend/src/pages/warehouse/MovementItemGrid.css` — Grid styles: table wrapper, thead, add button

**Key decisions:**
- Each row manages its own search/dropdown state independently to avoid tangled indexed state arrays at the grid level
- `selectedItemIds` Set passed down so dropdown can visually disable already-picked items (prevents duplicates before zod catches them)
- `useWatch` on `items` array feeds the `selectedItemIds` memoized set — reactive without re-rendering every row
- CSS in separate files per ground rules (no inline styles)

---

## [PRE-ALPHA v0.6.0 | 2026-03-11 20:35] — Inventory Enhancement Phase 1 (Steps 1.0–1.2)

**WHY:** Begin implementing the multi-item movement drawer. This batch covers dependency setup, a backend API enhancement for location-filtered inventory, and the TypeScript form types + zod validation schema that will drive the drawer form.

**Files changed:**
- `frontend/package.json` — Added `zod` (v4.3.6) and `@hookform/resolvers` (v5.2.2) for cross-field form validation
- `backend/app/routers/warehouse.py` — Added optional `location_id` query param to `GET /{warehouse_id}/inventory`; when provided, filters to that location and `quantity_available > 0`
- `frontend/src/api/base/warehouse.ts` — Added `location_id` to `ListInventoryParams` interface
- `frontend/src/pages/warehouse/movement.types.ts` — NEW: `MovementFormValues`, `MovementItemEntry`, zod schema with cross-row validation (no duplicate items, source ≠ destination, qty > 0), `movementFormResolver` for react-hook-form
- `docs/official_documentation/web-api.md` — Updated inventory endpoint docs with `location_id` param
- `docs/official_documentation/frontend-development-progress.md` — Logged Phase 1 Steps 1.0–1.2

**Key decisions:**
- Using zod v4 (latest) with `zod/v4` import path
- `location_id` filter also enforces `quantity_available > 0` so the drawer only shows items with stock at that location
- Meta fields (item_name, master_sku, current_stock) are TypeScript-only display props, not part of the zod schema — keeps validation clean

---

## [PRE-ALPHA v0.6.0-PLAN | 2026-03-11 17:00] — Inventory System Enhancement Planning Document

**WHY:** The current inventory system has basic movement recording (single-item modal) and flat history tables. This planning document outlines a 3-phase enhancement to transform it into a full lifecycle management platform with multi-item movements, approval workflows, and analytics.

**Files changed:**
- `docs/planning_phase/Frontend/07_inventory_system_enhancement_plan.plan.md` — NEW: comprehensive planning document covering Phase 1 (multi-item drawer with useFieldArray), Phase 2 (movement lifecycle status + expandable rows + action menus), Phase 3 (intelligent stock levels + analytics dashboard). Includes component architecture, backend schema changes, migration strategy, risk assessment, and implementation order.

**Key decisions documented:**
- Drawer over modal for movement entry (users can reference background table)
- Movement lifecycle: Pending → In-Transit → Completed (with Cancel from any pre-complete state)
- Stock changes tied to lifecycle transitions (not on creation)
- Analytics uses d3 (already installed) over recharts
- zod + @hookform/resolvers needed for cross-row validation
- Default existing movements to `completed` status in migration

---

## [PRE-ALPHA v0.5.54 | 2026-03-11 16:00] — Bundle Mass Upload (backend + frontend)

**WHY:** Users need to create bundles in bulk from CSV/Excel files. Each row represents one component of a bundle; rows sharing the same `bundle_sku` are grouped into a single bundle. The backend validates component SKU existence, FK resolution, and bundle composition rules before creating bundles with their PlatformSKU listings and ListingComponent records.

**Files changed:**
- `backend/app/services/items_import/bundle_importer.py` — NEW: parses CSV/Excel, groups rows by `bundle_sku`, resolves FKs (category/brand/uom), validates component SKUs against existing items, enforces bundle composition rules (>1 items or qty > 1), creates Item + PlatformSKU + ListingComponent records per bundle
- `backend/app/routers/items.py` — UPDATED: added `POST /items/bundles/import` endpoint (file upload, max 10 MB, returns ImportResult)
- `frontend/src/api/base/items.ts` — UPDATED: added `importBundles()` API function
- `frontend/src/pages/items/BundlesMassUploadPage.tsx` — NEW: full upload page with CSV template download, drag-drop file picker, SheetJS preview, result display with per-row errors
- `frontend/src/pages/items/CatalogUploadPage.tsx` — UPDATED: Bundles tab now renders BundlesMassUploadPage (was placeholder)

**CSV format:** `bundle_name, bundle_sku, component_sku, component_qty, [sku_name, description, category, brand, uom, is_active]`

---

## [PRE-ALPHA v0.5.53 | 2026-03-11 15:00] — Tabbed Create & Upload pages (Item / Bundle tabs)

**WHY:** Instead of separate pages for creating items vs bundles, and separate upload pages, users now get a single "Create New" page and a single "Mass Upload" page — each with Item/Bundle tabs. This reduces nav clutter and keeps creation flows unified.

**Files changed:**
- `frontend/src/pages/items/CatalogCreatePage.tsx` — NEW: wrapper page with Item/Bundle segmented tabs; renders ItemFormPage or BundleFormPage based on selected tab; supports `?type=bundle` query param for deep-linking
- `frontend/src/pages/items/CatalogUploadPage.tsx` — NEW: wrapper page with Items/Bundles segmented tabs; renders ItemsMassUploadPage or "coming soon" placeholder for bundle upload
- `frontend/src/pages/items/ItemFormPage.tsx` — UPDATED: added `hideHeader` prop to conditionally hide page chrome when embedded in wrapper
- `frontend/src/pages/bundles/BundleFormPage.tsx` — UPDATED: added `hideHeader` prop; back button now navigates to `/catalog/items` instead of `/catalog/bundles`
- `frontend/src/pages/items/ItemsMassUploadPage.tsx` — UPDATED: added `hideHeader` prop
- `frontend/src/pages/items/ItemsListPage.tsx` — UPDATED: "Create Bundle" dropdown option now navigates to `/catalog/items/new?type=bundle`
- `frontend/src/App.tsx` — UPDATED: `/catalog/items/new` renders CatalogCreatePage; `/catalog/items/upload` renders CatalogUploadPage; `/catalog/bundles/new` redirects to `/catalog/items/new`
- `frontend/src/components/layout/nav.config.tsx` — UPDATED: "Create New Item" renamed to "Create New"; isActive covers `/catalog/bundles/new`

---

## [PRE-ALPHA v0.5.52 | 2026-03-11 14:00] — Unified "My Items" page (Items + Bundles merged)

**WHY:** Streamline navigation and reduce context-switching by merging the separate Items and Bundles list pages into a single unified "My Items" page. Users can now manage all catalog items — regular items and bundles — from one place with primary tabs (All/Items/Bundles), secondary status tabs (All/Live/Unpublished/Deleted), a dropdown "Add New" button, visual Bundle badges, and expandable rows for both variations and bundle components.

**Files changed:**
- `frontend/src/pages/items/ItemsListPage.tsx` — REWRITTEN: unified page with dual-tab system (primary: All/Items/Bundles; secondary: All/Live/Unpublished/Deleted), dropdown Add New (Create Item / Create Bundle), Bundle badge in Item Type column, expandable rows for bundle components and item variations, smart API dispatch (listItems vs listBundles), combined status counts
- `frontend/src/components/layout/nav.config.tsx` — UPDATED: removed separate "Bundles" and "Create Bundle" nav entries under Catalog; renamed "Items" to "My Items"; extended isActive to cover `/catalog/bundles` paths; removed unused LayersIcon import
- `frontend/src/App.tsx` — UPDATED: `/catalog/bundles` route now redirects to `/catalog/items` (unified page); removed BundlesListPage import; added Navigate import; bundle create/edit routes preserved

---

## [PRE-ALPHA v0.5.51 | 2026-03-09 22:00] — Add is_online boolean to Platform table

**WHY:** Differentiate between online marketplaces (Shopee, Lazada, TikTok) and offline/physical stores within the same platform table. Defaults to `true` since all existing platforms are online.

**Files changed:**
- `backend/app/models/orders.py` — UPDATED: added `is_online: bool` field to `Platform` model (default `True`)
- `backend/app/schemas/platform.py` — UPDATED: added `is_online` to `PlatformCreate`, `PlatformUpdate`, and `PlatformRead` schemas
- `backend/app/routers/platforms.py` — UPDATED: all `PlatformRead` constructions include `is_online`; `GET /platforms` accepts `is_online` query filter
- `backend/alembic/versions/20260309_1000_00_g2h3i4j5k6l7_add_is_online_to_platform.py` — NEW: Alembic migration adds `is_online` column with `server_default=TRUE`
- `docs/official_documentation/database_structure.md` — UPDATED: platform table schema + ER diagrams

---

## [PRE-ALPHA v0.5.50-PLAN | 2026-03-09 21:30] — Bundle v2 Planning Document

**WHY:** The current bundle implementation is coupled to PlatformSKU/listing_component, requiring platform_id and seller_id to create a bundle. Bundles are a catalog/warehouse concept and should be platform-independent. This planning doc outlines the decoupled architecture.

**Files changed:**
- `docs/planning_phase/Backend/08_bundle_v2_plan.plan.md` — NEW: comprehensive planning document covering schema (new `bundle_components` table), 7 revised API endpoints, frontend type updates, items/bundles page separation rules, 4-phase implementation plan. Supersedes `07_bundle_sku_inventory_plan.plan.md`.

**Key decisions documented:**
- New `bundle_components` table replaces PlatformSKU+ListingComponent coupling
- Bundle validity: must have >1 distinct components OR any component with qty > 1
- Items page excludes Bundle-type items; Bundles page shows only valid bundles
- No nested bundles, pricing, or ATP in this iteration

---

## [PRE-ALPHA v0.5.46 | 2026-03-09 18:00] — My Bundles Dashboard + Bundle API Endpoints

**Files changed:**
- `backend/app/schemas/items.py` — UPDATED: added `BundleListItem` schema (extends ItemRead with `component_count`, `total_quantity`)
- `backend/app/routers/items.py` — UPDATED: added 3 new endpoints: `GET /items/bundles` (paginated list with component counts), `GET /items/bundles/counts` (tab counts), `GET /items/bundles/{item_id}` (single bundle with full components)
- `frontend/src/api/base_types/items.ts` — UPDATED: added `BundleListItem` interface
- `frontend/src/api/base/items.ts` — UPDATED: added `listBundles()`, `getBundleCounts()`, `getBundle()` API functions + `ListBundlesParams` interface
- `frontend/src/pages/bundles/BundlesListPage.tsx` — NEW: full bundles dashboard mirroring ItemsListPage (tabs, filters, DataTable, component counts, expand-to-view components, soft-delete/restore, status toggle)
- `frontend/src/pages/bundles/BundleFilters.tsx` — NEW: filter bar (search, category, brand) for bundles list
- `frontend/src/pages/bundles/BundleFormPage.tsx` — UPDATED: replaced `updateBundle(id, {})` workaround with proper `getBundle(id)` for edit-mode data loading
- `frontend/src/App.tsx` — UPDATED: `/catalog/bundles` route now renders `BundlesListPage` instead of `PlaceholderPage`

**What was done:**
1. **Backend — 3 new bundle read endpoints:**
   - `GET /items/bundles` — paginated list of Bundle-type items with `component_count` and `total_quantity` computed via LEFT JOIN on listing_component/platform_sku; supports search, is_active, category, brand, include_deleted filters
   - `GET /items/bundles/counts` — tab badge counts (all/live/unpublished/deleted) scoped to Bundle type
   - `GET /items/bundles/{item_id}` — single bundle with full `BundleReadResponse` (item + components); replaces the PATCH-with-empty-body workaround
2. **Frontend — BundlesListPage:** Card with header ("My Bundles" + "+ Create New Bundle"), 4 tabs with counts, BundleFilters (search + category + brand), DataTable with columns: Bundle (thumbnail + name + SKU + expand chevron), Components (badge: "3 Items" + total qty), Category, Status (toggle switch), Brand, Actions (edit/delete/restore); row expand fetches and displays component breakdown table
3. **Frontend — BundleFilters:** Reusable filter bar identical to ItemFilters with bundle-specific search placeholder
4. **BundleFormPage fix:** Edit mode now uses `GET /items/bundles/{id}` instead of `PATCH /items/bundles/{id}` with empty body

**WHY:** Completes the bundles management UI — users can now list, search, filter, toggle status, soft-delete, restore, and inspect bundle components from a dedicated dashboard that mirrors the established Items page UX.

---

## [PRE-ALPHA v0.5.45 | 2026-03-09 16:30] — Bundle Soft Delete & History Logging

**Files changed:**
- `backend/app/models/triggers.py` — UPDATED: added trigger #11 `insert_items_history_on_update()` + `trg_items_history_on_update` (AFTER UPDATE on items); detects UPDATE / SOFT_DELETE / RESTORE operations, captures old+new state in JSONB snapshot_data with `previous_values`; uses `app.current_user_id` session variable for user tracking
- `backend/app/routers/items.py` — UPDATED: added `DELETE /bundles/{item_id}` (soft-delete bundle + deactivate PlatformSKU listing) and `POST /bundles/{item_id}/restore` (restore + re-activate listing); added `SET LOCAL app.current_user_id` before all item update/delete/restore flushes so the trigger records the authenticated user
- `frontend/src/api/base/items.ts` — UPDATED: added `deleteBundle()` and `restoreBundle()` API functions
- `docs/official_documentation/web-api.md` — UPDATED: documented DELETE /bundles/{item_id} and POST /bundles/{item_id}/restore endpoints
- `docs/official_documentation/database_structure.md` — UPDATED: documented trigger #11 and function `insert_items_history_on_update()`

**What was done:**
1. **Soft Delete:** `DELETE /items/bundles/{item_id}` sets `deleted_at`/`deleted_by` on the items row and deactivates the PlatformSKU listing; listing_component rows are preserved for restore
2. **Restore:** `POST /items/bundles/{item_id}/restore` clears soft-delete fields and re-activates the PlatformSKU listing; returns full BundleReadResponse
3. **History on UPDATE:** PostgreSQL trigger `trg_items_history_on_update` fires AFTER UPDATE on items, auto-detects operation type (UPDATE/SOFT_DELETE/RESTORE), captures full before/after snapshot in JSONB
4. **User attribution:** All item mutation endpoints now set `SET LOCAL app.current_user_id` before flush so the trigger can record `changed_by_user_id` even for non-delete operations

**WHY:** Maintains data integrity by never hard-deleting bundle data — soft-delete preserves recoverability. History trigger provides a complete audit trail for every item mutation (create, update, soft-delete, restore), storing the full before/after state in JSONB for compliance and debugging.

---

## [PRE-ALPHA v0.5.44 | 2026-03-09 15:00] — Bundle Form Page (Create / Edit)

**Files changed:**
- `frontend/src/pages/bundles/BundleFormPage.tsx` — NEW: main bundle form (create + edit)
- `frontend/src/pages/bundles/ComponentSearch.tsx` — NEW: searchable item picker dropdown
- `frontend/src/pages/bundles/ComponentList.tsx` — NEW: dynamic component table with quantity steppers
- `frontend/src/api/base_types/items.ts` — UPDATED: added 5 bundle TypeScript interfaces
- `frontend/src/api/base/items.ts` — UPDATED: added `createBundle()` and `updateBundle()` functions
- `frontend/src/App.tsx` — UPDATED: added `/catalog/bundles/new` and `/catalog/bundles/:id/edit` routes
- `frontend/src/components/layout/nav.config.tsx` — UPDATED: added "Create Bundle" nav entry
- `docs/official_documentation/frontend-development-progress.md` — UPDATED: documented all changes

**What was done:**
1. **BundleFormPage**: Full create/edit form with react-hook-form, dropdown options, image upload, platform/seller (create-only), bundle composition validation
2. **ComponentSearch**: Debounced search against `/items` API, excludes Bundle-type items and already-added items, thumbnail + name + SKU results
3. **ComponentList**: Inline quantity stepper, delete per row, summary bar
4. **API layer**: `createBundle()` → `POST /items/bundles`, `updateBundle()` → `PATCH /items/bundles/{id}`
5. **Routes**: `/catalog/bundles/new` and `/catalog/bundles/:id/edit` registered in App.tsx

**WHY:** Provides the full frontend UI for the bundle creation/editing workflow, integrating with the backend endpoints from v0.5.42-v0.5.43.

---

## [PRE-ALPHA v0.5.43 | 2026-03-09 14:00] — Bundle Update Endpoint

**Files changed:**
- `backend/app/routers/items.py` — ADDED: `PATCH /items/bundles/{item_id}` endpoint; imported `delete` from sqlalchemy and `BundleUpdateRequest` from schemas
- `backend/app/schemas/items.py` — ADDED: `BundleUpdateRequest` schema (all fields optional, components triggers delete-and-reinsert)
- `docs/official_documentation/web-api.md` — UPDATED: added PATCH endpoint to table + full documentation with data integrity notes

**What was done:**
1. **`PATCH /api/v1/items/bundles/{item_id}`**: Update bundle metadata and/or replace components in a single transaction
2. **SKU change safety**: changing `master_sku` only updates the bundle's item row + syncs `platform_sku.platform_sku`; component item SKUs are never modified
3. **Delete-and-reinsert strategy**: when `components` is provided, all existing `listing_component` rows for this listing are deleted then new rows inserted — guarantees final state matches exactly what the client sent
4. **Field sync**: `item_name` → `platform_seller_sku_name`, `is_active` → `platform_sku.is_active` — kept in sync automatically
5. **Validation**: verifies item is Bundle type, new SKU uniqueness, component existence, bundle composition rules

**WHY:** Enables modification of existing bundles (SKU rename, component add/remove/reorder) while preserving data integrity — component item records are never altered by bundle-level changes.

---

## [PRE-ALPHA v0.5.42 | 2026-03-09 13:00] — Bundle Creation Endpoint

**Files changed:**
- `backend/app/routers/items.py` — ADDED: `POST /items/bundles` endpoint; imports for `ListingComponent`, `PlatformSKU`, bundle schemas
- `backend/app/schemas/items.py` — ADDED: `BundleComponentInput`, `BundleCreateRequest`, `BundleComponentRead`, `BundleReadResponse` schemas
- `docs/official_documentation/web-api.md` — UPDATED: added `POST /items/bundles` to endpoint table + full endpoint documentation; removed stale bundle BOM endpoints from v0.5.17 (dropped in v0.5.27)

**What was done:**
1. **`POST /api/v1/items/bundles`**: Atomic endpoint that creates a bundle item + listing components in a single transaction
2. **Transaction flow**: (a) validate master_sku uniqueness, (b) validate bundle composition (>1 items or qty>1), (c) verify all component item_ids exist, (d) resolve "Bundle" item_type_id, (e) insert into `items`, (f) create `platform_sku` listing, (g) insert components into `listing_component`
3. **Audit trail**: The `trg_items_history_on_insert` trigger (from v0.5.41) fires automatically on the items INSERT — no explicit audit code needed
4. **Validation**: 409 on duplicate SKU, 422 on invalid composition or missing component items, 500 if Bundle type not seeded

**WHY:** Provides a single atomic API call to create bundles with full validation, leveraging the existing `listing_component` table architecture and the v_bundles view for subsequent queries.

---

## [PRE-ALPHA v0.5.41 | 2026-03-09 12:00] — Bundle Detection View + Items Audit Trail Trigger

**Files changed:**
- `backend/app/models/views.py` — ADDED: `v_bundles` view (view #13) identifying bundle listings from `listing_component` using multi-item or qty>1 criteria
- `backend/app/models/triggers.py` — ADDED: `insert_items_history_on_create()` trigger function + `trg_items_history_on_insert` trigger (AFTER INSERT on items) for automatic audit trail
- `backend/app/models/seed.py` — ADDED: "Bundle" to `_ITEM_TYPES` seed data (7th item_type)
- `backend/app/migrations/006_bundles_view_and_audit.sql` — ADDED: SQL reference script (not executed at runtime; Python modules are canonical)
- `docs/official_documentation/database_structure.md` — UPDATED: added v_bundles view docs, trg_items_history_on_insert trigger docs, "Bundle" in item_type seed

**What was done:**
1. **v_bundles view**: CTE-based view that identifies bundles from `listing_component` — a listing qualifies as a bundle if it has >1 unique `item_id` OR a single `item_id` with `quantity > 1`; joins to `platform_sku`, `platform`, `seller` for full context
2. **Audit trail trigger**: `trg_items_history_on_insert` fires AFTER INSERT on `items` and auto-creates an `items_history` record with `operation = 'INSERT'` and a JSONB snapshot of all key fields
3. **"Bundle" item_type**: Added to seed data so items can be classified as bundles via `item_type_id`
4. **master_sku constraint**: Verified existing UNIQUE NOT NULL constraint on `items.master_sku` (no change needed — already enforced at model level)

**WHY:** Prepares the database layer to formally distinguish individual items from bundles, provides automatic audit trail for all new item creations, and adds the "Bundle" classification to the type system.

---

## [PRE-ALPHA v0.5.40.1 | 2026-03-07 13:00] — Warehouse Settings Tab Visual Redesign

**Files changed:**
- `frontend/src/pages/settings/WarehouseSettingsTab.tsx` — REDESIGNED: two sub-tabs ("warehouse list" / "location setup"); iOS-style teal toggle for status; pill "Manage" button per row; filter as underline tabs; Batch Upload toolbar; Country column; proper pagination

**What was done:**
1. **Sub-tabs**: "warehouse list" | "location setup" with black-underline active style
2. **Status column**: iOS-style toggle switch (accent-teal when active)
3. **Manage column**: Pill button ("▶ Manage") switches to Location Setup sub-tab scoped to that warehouse; kebab (⋮) for Edit/Duplicate/Delete
4. **Filter**: "All / Active / Inactive" rendered as underline-tab pills
5. **Toolbar**: "Batch Upload" (grey outline) + "+ Add Warehouse" (secondary orange)
6. **Country field**: Added to form and address columns
7. **Pagination**: 20 items/page with proper page state

**WHY:** Redesigned to match reference screenshot showing sub-tab navigation, toggle switches, pill Manage buttons, and tab-style filters.

---

## [PRE-ALPHA v0.5.40 | 2026-03-07 12:00] — Warehouse Overview & Location Management in Settings

**Files changed:**
- `frontend/src/pages/settings/WarehouseSettingsTab.tsx` — NEW: embedded warehouse table with full CRUD (add/edit/toggle/duplicate/soft-delete), expandable location management panel per warehouse
- `frontend/src/pages/settings/warehouse_locations/BulkCreationWizard.tsx` — NEW: pattern-based location generator (prefix + numeric range or explicit values, Cartesian product preview)
- `frontend/src/pages/settings/warehouse_locations/CsvLocationImport.tsx` — NEW: CSV/Excel import (template download, SheetJS parse, client-side validation, duplicate detection, row-by-row batch create with progress bar)
- `frontend/src/pages/settings/warehouse_locations/LocationTree.tsx` — NEW: hierarchical tree rendering (Section → Zone → Aisle → Rack → Bin) with expand/collapse, hover edit/delete actions
- `frontend/src/pages/settings/warehouse_locations/PreviewTable.tsx` — NEW: preview table for generated locations (first 100 shown)
- `frontend/src/pages/settings/warehouse_locations/EditNodeModal.tsx` — NEW: rename modal for individual tree nodes
- `frontend/src/pages/settings/warehouse_locations/LocationManagementPage.css` — NEW: CSS for tree/content panel layout
- `frontend/src/pages/settings/LocationManagementSection.tsx` — UPDATED: added `overrideWarehouseId`/`overrideWarehouseName` props (bypasses global context for embedded use); added "Pattern Generator | CSV/Excel Import" tab switcher in right panel
- `frontend/src/pages/settings/SettingsPage.tsx` — UPDATED: Warehouse tab now renders `<WarehouseSettingsTab />` instead of placeholder
- `frontend/src/api/base_types/warehouse.ts` — UPDATED: added `is_active` and `sort_order` to `InventoryLocationCreate` and `InventoryLocationUpdate`

**What was done:**
1. **Warehouse Overview Table** — compact table listing all warehouses (Name, ID, Primary Location, Locations count, Status). Columns: Add Warehouse button, filter by status, search. Each row has a "Manage" toggle that expands an inline location panel.
2. **Full warehouse CRUD** — Add/Edit modal, status toggle, duplicate (deep clone), soft delete — all carried over from WarehouseListPage into the settings-embedded tab.
3. **Hierarchical Location Tree** — `LocationTree` renders Section → Zone → Aisle → Rack → Bin with auto-expand (first 2 levels), type badges, location count pills, and hover edit/delete actions per node.
4. **Pattern Generator tab** — `BulkCreationWizard` lets users enable any hierarchy level, set a prefix + numeric range (with zero-padding) or explicit CSV values, preview the full Cartesian product, then submit to `POST /bulk-generate`.
5. **CSV/Excel Import tab** — `CsvLocationImport` supports drag-drop or click-to-browse, parses .csv/.xlsx/.xls via SheetJS, validates each row (empty location, field length, in-file duplicates), shows a preview table with invalid rows highlighted, imports valid rows row-by-row with a live progress bar.
6. **Type safety** — `InventoryLocationCreate/Update` now includes `is_active` and `sort_order` to match backend schema.

**WHY:** The Settings Warehouse tab was a placeholder. This implements the full warehouse management UX as specified: warehouse table with CRUD, location tree, bulk generator, and file import — all in one cohesive settings panel without requiring navigation to separate pages.

---

## [PRE-ALPHA v0.5.39 | 2026-03-07 00:00] — Warehouse Settings Grid Refactor

**Files changed:**
- `frontend/src/pages/settings/WarehouseCard.tsx` — REFACTORED: responsive grid, always-visible CTA card, create form above grid, empty state, StatusBadge extracted, CreateWarehouseCard extracted

**What was done:**
1. **Responsive Grid:** Changed breakpoints from `sm:cols-2 lg:cols-3 xl:cols-4` to `cols-1 | md:cols-2 | lg:cols-4` as specified.
2. **Primary Action Card (slot 0):** `CreateWarehouseCard` is now always rendered as the first grid item — never replaced by the form. When `creating` is active the card shows a rotated icon and "Cancel" label (toggle behaviour). Clicking again closes the form.
3. **Create Form above grid:** `WarehouseFormPanel` now renders outside and above the grid so the CTA card stays in position 0 at all times.
4. **Warehouse Card layout:** Name field changed to `font-bold`. StatusBadge extracted as its own component. Action bar retained: Edit button (left) + `StandardActionMenu` kebab (right, exposes Deactivate/Activate + Delete only).
5. **Empty State:** Dedicated `EmptyState` component renders below the grid when `warehouses.length === 0` — shows inbox icon + instructional copy.
6. **useCallback on openCreate:** prevents unnecessary re-renders on the toggle handler.

**WHY:** The previous layout hid the CTA card while the form was open, violated the "always first" grid contract, used incorrect breakpoints (sm/xl), and had no dedicated empty state. This refactor aligns the component with the design specification.

---

## [PRE-ALPHA v0.5.38 | 2026-03-06 23:00] — Inventory Guard & Recursive Soft-Delete

**Files changed:**
- `backend/app/services/inventory_guard.py` — ENHANCED: added `get_location_children_ids()` for recursive child lookup; added `soft_delete_location()` service that cascades soft-delete to all children + runs inventory guard against full subtree; added `_get_location_level()` helper
- `backend/app/routers/warehouse.py` — `DELETE /locations/{id}` now uses recursive `soft_delete_location()` service (cascades to children); `PATCH /locations/{id}` adds inventory guard when `is_active=false`; `PATCH /{id}/toggle-status` adds inventory guard when toggling to inactive; all inventory guard errors changed from `409 Conflict` to `400 Bad Request` with message `"Cannot delete: Location contains active stock."`
- `backend/app/services/location_tree.py` — orphan management: locations with `section=NULL` grouped under virtual "Unassigned" node (`type: "unassigned"`, `is_virtual: true`, `is_orphan: true`) at end of warehouse children; normal sections counted separately in summary

**What was done:**
1. **Recursive Soft-Delete:** `soft_delete_location(location_id)` determines hierarchy level of target location, finds all children sharing the same prefix (Section→Zone→Aisle→Rack→Bin), checks inventory guard against the FULL subtree, then bulk soft-deletes all in one UPDATE
2. **Inventory Guard (enhanced):** Before any DELETE or PATCH (is_active=false), the guard queries InventoryLevel for ALL affected locations (including recursive children). If any SKU count > 0, returns HTTP 400 with "Cannot delete: Location contains active stock." — now protects 6 endpoints total
3. **Orphan Management:** GET `/locations/hierarchy` groups locations with section=NULL under a virtual "Unassigned" node at the end of the warehouse's children. This node has `type: "unassigned"`, `is_virtual: true` for distinct frontend rendering

**WHY:** Prevents data integrity issues — deleting a parent node (e.g. Section) previously left orphaned child locations. The inventory guard now covers all destructive operations. Orphan management gives the frontend a clean contract for rendering unassigned locations.

---

## [PRE-ALPHA v0.5.37 | 2026-03-06 XX:XX] — Warehouse Management Enhancements — 5 features

**Files changed:**
- `backend/app/services/inventory_guard.py` — NEW: stock guard service (check_stock_at_locations, get_warehouse_location_ids, get_subtree_location_ids)
- `backend/app/routers/warehouse.py` — guard checks on 4 delete/deactivate endpoints; rename-level endpoint; location_count in list/get warehouses
- `backend/app/schemas/warehouse.py` — RenameLevelRequest/Response schemas; location_count on WarehouseRead
- `backend/app/services/location_tree.py` — orphan management: "(unnamed)" → "Unassigned", is_orphan flag
- `frontend/src/api/base_types/warehouse.ts` — is_orphan, location_count, RenameLevelRequest/Response types
- `frontend/src/api/base/warehouse.ts` — renameLevel() API function
- `frontend/src/pages/settings/warehouse_locations/EditNodeModal.tsx` — NEW: rename hierarchy node modal
- `frontend/src/pages/settings/warehouse_locations/LocationTree.tsx` — orphan styling (italic + warning), edit pencil icon
- `frontend/src/pages/settings/LocationManagementSection.tsx` — edit modal state wiring

**What was done:**
1. Inventory Guard: DELETE/PATCH warehouse and location endpoints now check InventoryLevel for stock (qty_available > 0 OR reserved_qty > 0) and return 409 if stock exists
2. Hierarchical Soft Delete: Already implemented — documented cascade behavior
3. Orphan Management: Locations with missing hierarchy levels show as "Unassigned" with italic/warning styling and is_orphan flag
4. Edit Modal: Bulk rename hierarchy nodes via PATCH /{warehouse_id}/locations/rename-level; frontend EditNodeModal with pencil icon in tree
5. Multi-Warehouse Location Count: WarehouseRead now includes location_count via LEFT JOIN subquery

**WHY:** Prevents accidental deletion of stocked locations, provides CRUD for hierarchy nodes, and improves UX for orphaned/unassigned locations.

---

## [PRE-ALPHA v0.5.36 | 2026-03-06 18:00] — Standardize all delete operations to soft-delete

**What changed:** Converted all hard-delete endpoints (ItemType, Category, Brand, BaseUOM) to soft-delete by adding `deleted_at` columns with partial indexes. Added restore endpoints for all soft-deletable entities: reference data (4 endpoints), Warehouse (with cascade restore), and InventoryLocation. Fixed `commit()`→`flush()` inconsistency in `soft_delete_warehouse()`.

**Why:** The project ground rule mandates "soft delete only" — data must never be permanently removed from the database. Previously, the four reference lookup tables used hard-delete (`session.delete()`), which permanently destroyed rows. This change ensures all delete operations are recoverable via restore endpoints, and the delete/restore pattern is consistent across all domains.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/models/items.py` | Modified | Added `deleted_at: Optional[datetime]` + partial index to ItemType, Category, Brand, BaseUOM |
| `backend/app/schemas/items.py` | Modified | Added `deleted_at: Optional[datetime]` to ItemTypeRead, CategoryRead, BrandRead, BaseUOMRead |
| `backend/app/routers/items.py` | Modified | Converted 4 hard-delete endpoints to soft-delete; added `deleted_at IS NULL` filter to 4 list queries; added 4 restore endpoints |
| `backend/app/routers/warehouse.py` | Modified | Fixed `commit()`→`flush()`; added restore endpoints for Warehouse (cascade) and InventoryLocation |
| `backend/alembic/versions/20260306_1200_00_f1a2b3c4d5e6_...` | Created | Migration: adds `deleted_at` + partial indexes to 4 reference tables |

### New API Endpoints (6 restore endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/items/types/{id}/restore` | Restore soft-deleted item type |
| POST | `/api/v1/items/categories/{id}/restore` | Restore soft-deleted category |
| POST | `/api/v1/items/brands/{id}/restore` | Restore soft-deleted brand |
| POST | `/api/v1/items/uoms/{id}/restore` | Restore soft-deleted UOM |
| POST | `/api/v1/warehouse/{id}/restore` | Restore warehouse + cascade-restore locations |
| POST | `/api/v1/warehouse/locations/{id}/restore` | Restore single inventory location |

---

## [PRE-ALPHA v0.5.35 | 2026-03-06 16:00] — Move Location Management into Settings page

**What changed:** Moved Location Management UI from standalone `/inventory/locations` page into **Settings > Warehouse > Locations & Sections** sub-tab, replacing the previous `WarehouseLocationCard`. Created `LocationManagementSection.tsx` wrapper in `pages/settings/` that imports the reusable tree/wizard/preview components from `pages/warehouse/locations/`. Removed standalone route and nav item. Deleted `LocationManagementPage.tsx` (dead code).

**Why:** Location management is an administrative/configuration concern, not a day-to-day inventory operation. Placing it under Settings > Warehouse keeps the Inventory nav focused on operational pages (levels, movements, alerts) while giving warehouse admins a natural location for scaffolding and viewing locations.

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/pages/settings/LocationManagementSection.tsx` | Created | Settings-embedded wrapper — border styling (no nested cards), uses `useWarehouse()` context |
| `frontend/src/pages/settings/SettingsPage.tsx` | Modified | Replaced `WarehouseLocationCard` import/usage with `LocationManagementSection` |
| `frontend/src/App.tsx` | Modified | Removed `/inventory/locations` route and `LocationManagementPage` import |
| `frontend/src/components/layout/nav.config.tsx` | Modified | Removed "Locations" nav item from Inventory section |
| `frontend/src/pages/warehouse/locations/LocationManagementPage.tsx` | Deleted | Dead code after move |

### Documentation Changes

| File | Action | Notes |
|------|--------|-------|
| `docs/official_documentation/frontend-development-progress.md` | Modified | v0.5.35 entry |
| `docs/official_documentation/version_update.md` | Modified | This entry |

---

## [PRE-ALPHA v0.5.34 | 2026-03-06 15:00] — Warehouse Location Management frontend page

**What changed:** Built `LocationManagementPage` at `/inventory/locations` with Location Tree sidebar (accordion hierarchy), Bulk Creation Wizard (range inputs per hierarchy level), and Preview Table (Cartesian product preview before save). Added TanStack Query (`@tanstack/react-query`) and Lucide icons (`lucide-react`). Wrapped App in `QueryClientProvider`. Added nav item under Inventory.

**Why:** Closes the frontend loop for the bulk-generate (v0.5.32) and hierarchy (v0.5.33) backend endpoints. Warehouse managers need a visual tool for location exploration and mass scaffolding.

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/pages/warehouse/locations/LocationManagementPage.tsx` | Created | Main page with TanStack Query |
| `frontend/src/pages/warehouse/locations/LocationTree.tsx` | Created | Recursive accordion tree |
| `frontend/src/pages/warehouse/locations/BulkCreationWizard.tsx` | Created | Range/values inputs per level |
| `frontend/src/pages/warehouse/locations/PreviewTable.tsx` | Created | Paginated preview table |
| `frontend/src/pages/warehouse/locations/LocationManagementPage.css` | Created | Panel layout + scrollbar |
| `frontend/src/App.tsx` | Modified | QueryClientProvider + /inventory/locations route |
| `frontend/src/components/layout/nav.config.tsx` | Modified | Locations nav item |
| `frontend/src/api/base_types/warehouse.ts` | Modified | +5 types (LocationTreeNode, SegmentRangeInput, BulkGenerate*) |
| `frontend/src/api/base/warehouse.ts` | Modified | +2 API functions |
| `frontend/package.json` | Modified | +@tanstack/react-query, +lucide-react |
| `docs/official_documentation/frontend-development-progress.md` | Modified | v0.5.34 entry |
| `docs/official_documentation/version_update.md` | Modified | This entry |

---

## [PRE-ALPHA v0.5.33 | 2026-03-06 14:00] — Location hierarchy tree endpoint + rewritten tree builder

**What changed:** Rewrote `location_tree.py` with true O(n) single-pass tree construction (was O(k * levels) due to repeated key scans). Added `total_locations` count at every node and improved summaries (e.g. "Aisle A01 contains 20 locations" with total leaf count, not just direct children). Added `GET /api/v1/warehouse/{id}/locations/hierarchy` endpoint.

**Why:** The frontend needs a nested tree for warehouse location navigation (expandable drill-down). The previous implementation scanned all keys per depth level per recursive call. The rewrite uses `setdefault`-based dict nesting (Phase 1) + bottom-up leaf count propagation (Phase 2) + single format walk (Phase 3) — all O(n).

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/services/location_tree.py` | Rewritten | 3-phase O(n) algorithm: setdefault tree build → bottom-up total_locations count → JSON format. Leaf nodes include `location_id`, `display_code`, `is_active`, `sort_order` |
| `backend/app/routers/warehouse.py` | Modified | Added `GET /{warehouse_id}/locations/hierarchy` endpoint; imports `build_location_tree` |

### Documentation Changes

| File | Action | Notes |
|------|--------|-------|
| `docs/official_documentation/web-api.md` | Modified | Added hierarchy endpoint to table |
| `docs/official_documentation/version_update.md` | Modified | This entry |

---

## [PRE-ALPHA v0.5.32 | 2026-03-06 13:00] — Bulk-generate inventory locations endpoint

**What changed:** Added `POST /api/v1/warehouse/{id}/locations/bulk-generate` endpoint with range-based Cartesian product generation. New service module `location_generator.py` expands `SegmentRange` specs (prefix+range or explicit values list) into location tuples and bulk-inserts with SAVEPOINT-per-row duplicate handling.

**Why:** Warehouse managers need to scaffold hundreds of locations at once (e.g. "sections A1-A5, aisles 01-10, racks R1-R8, bins B01-B04") rather than creating them individually. The Cartesian product approach with per-segment range specs is the standard warehouse addressing pattern.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/services/location_generator.py` | Created | `expand_ranges()` (pure Cartesian product) + `bulk_generate_locations()` (async DB insert with SAVEPOINT per-row) |
| `backend/app/schemas/warehouse.py` | Modified | Added `SegmentRange` (range/values modes), `BulkGenerateRequest`, `BulkGenerateError`, `BulkGenerateResponse` |
| `backend/app/routers/warehouse.py` | Modified | Added `POST /{warehouse_id}/locations/bulk-generate` endpoint after single-location CRUD |

### Documentation Changes

| File | Action | Notes |
|------|--------|-------|
| `docs/official_documentation/web-api.md` | Modified | Added bulk-generate endpoint + request/response type docs |
| `docs/official_documentation/version_update.md` | Modified | This entry |

---

## [PRE-ALPHA v0.5.32 | 2026-03-06 14:00] — Warehouse grid layout + location tree delete + wizard improvements

**What changed:** Four coordinated improvements to the Warehouse Management module in Settings.

1. **Warehouse Grid** — `WarehouseCard.tsx` fully rewritten from a plain list to a responsive card grid (1–4 columns). First tile is a dedicated "+ Create Warehouse" CTA; each warehouse card shows name, address, status badge, with an Edit button and a `StandardActionMenu` kebab offering Activate/Deactivate and soft-delete.

2. **Location Tree Delete** — `LocationTree.tsx` redesigned to track the hierarchy path through recursive props. Every non-root node shows a `Trash2` icon on hover that fires `onDeleteNode(node, path)`. `LocationManagementSection.tsx` shows a confirmation modal stating how many sub-locations will be soft-deleted. Single bin → `DELETE /warehouse/locations/{id}`; parent node → `DELETE /warehouse/{id}/locations/subtree?section=…`.

3. **Wizard Help Tooltip** — `BulkCreationWizard.tsx` adds a `HelpCircle` toggle with an inline panel explaining Range/Values modes, cartesian-product behaviour, and the 10,000 limit. Save button is gated behind a preview: disabled until "Generate Preview" is clicked, resets whenever segment config changes.

4. **Safety** — all delete paths use `deleted_at` soft-delete; no hard deletes exposed in UI.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/routers/warehouse.py` | Modified | `DELETE /locations/{location_id}` (single bin soft-delete); `DELETE /{warehouse_id}/locations/subtree` (bulk soft-delete by hierarchy prefix) |

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/api/base/warehouse.ts` | Modified | Added `deleteLocation`, `deleteLocationSubtree`, `LocationSubtreeFilter` |
| `frontend/src/pages/settings/WarehouseCard.tsx` | Rewritten | Responsive card grid; `WarehouseItemCard` + `WarehouseFormPanel`; `StandardActionMenu` kebab |
| `frontend/src/pages/settings/warehouse_locations/LocationTree.tsx` | Modified | `HierarchyPath` exported; path accumulation through tree; `Trash2` icon on hover; `onDeleteNode` prop |
| `frontend/src/pages/settings/warehouse_locations/BulkCreationWizard.tsx` | Modified | `HelpCircle` help panel; `previewGenerated` gates Save button |
| `frontend/src/pages/settings/LocationManagementSection.tsx` | Modified | Fixed import paths; `DeleteConfirmModal`; `handleDeleteNode` → `executeDelete` |
| `frontend/src/pages/settings/SettingsPage.tsx` | Modified | Warehouse Management tab renders `WarehouseCard` full-width |

---

## [PRE-ALPHA v0.5.31 | 2026-03-06 12:00] — Fix async relationship loading in items mutation endpoints

**What changed:** Replaced `session.refresh(item, attribute_names=["uom", "brand", "item_type", "category"])` with a proper `selectinload` re-fetch in `create_item`, `update_item`, and `restore_item`.

**Why:** In async SQLAlchemy, calling `session.refresh()` with relationship attribute names does not reliably hydrate those relationships — the attributes can remain in an expired lazy-load state, and any subsequent access (e.g. `item.uom.uom_id`) triggers a synchronous lazy load that fails with `MissingGreenlet` in an async context. This caused `update_item` (called by the status toggle and edit save) to return a 500 error, which the frontend displayed as "Operation failed." The fix is consistent with how `list_items` and `get_item` already use `selectinload`.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/app/routers/items.py` | Modified | `create_item`, `update_item`, `restore_item`: replaced `session.refresh()` with `select().options(selectinload())` after flush |

---

## [PRE-ALPHA v0.5.30 | 2026-03-06 10:00] — Enhance inventory_location: is_active, sort_order, display_code, composite unique

**What changed:** Added three new columns to `inventory_location` (`is_active`, `sort_order`, `display_code`), a composite UNIQUE index on `(warehouse_id, section, zone, aisle, rack, bin)`, and a BEFORE INSERT trigger that auto-generates `display_code` from the hierarchy segments.

**Why:** Locations needed an operational on/off toggle (`is_active`) separate from soft-delete (`deleted_at`), user-defined pick-path ordering (`sort_order`), a persisted human-readable code for SQL-level filtering (`display_code`), and a uniqueness constraint to prevent duplicate physical addresses within the same warehouse.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/alembic/versions/20260306_1000_00_d5e6f7a8b9c0_enhance_inventory_location.py` | Created | Alembic migration: adds 3 columns, composite UNIQUE index, partial active index, trigger function + trigger, backfills display_code |
| `backend/app/models/warehouse.py` | Modified | InventoryLocation: added `display_code`, `is_active`, `sort_order` fields + `__table_args__` with composite UNIQUE and partial active index |
| `backend/app/models/triggers.py` | Modified | Added trigger #9: `generate_location_display_code` (BEFORE INSERT, CONCAT_WS of hierarchy segments) |
| `backend/app/schemas/warehouse.py` | Modified | InventoryLocationCreate: added `is_active`, `sort_order`; InventoryLocationUpdate: added `is_active`, `sort_order`; InventoryLocationRead: added `display_code`, `is_active`, `sort_order` |
| `backend/app/routers/warehouse.py` | Modified | All 3 location endpoints return new fields; list_locations filters soft-deleted, sorts by sort_order; update_location recomputes display_code in Python |

### Documentation Changes

| File | Action | Notes |
|------|--------|-------|
| `docs/official_documentation/database_structure.md` | Modified | Updated 2 ERD diagrams + table spec with new columns, indexes, and trigger description |
| `docs/official_documentation/version_update.md` | Modified | This entry |

---

## [PRE-ALPHA v0.5.29 | 2026-03-06] — Layout restructure: full-width header + global warehouse context

**What changed:** Restructured MainLayout to match new wireframe — header now spans full width (fixed top) with logo, hamburger, search, account dropdown, and notification bell. Sidebar starts below header with a global warehouse selector. Created WarehouseContext for app-wide warehouse selection. Migrated inventory pages (Levels, Movements, Alerts) to use global context instead of per-page selectors.

**Why:** The previous layout had the logo inside the sidebar and the top bar nested inside the main content area (offset by sidebar width). The wireframe calls for a full-width header above both sidebar and content, with a global warehouse selector in the sidebar that broadcasts the selected warehouse to all pages.

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/api/contexts/WarehouseContext.tsx` | Created | Global warehouse selection context — fetches active warehouses, persists to localStorage, auto-selects first warehouse |
| `frontend/src/components/layout/WarehouseSelector.tsx` | Created | Pill-shaped sidebar dropdown — reads from WarehouseContext, adapts to collapsed state, outside-click close |
| `frontend/src/components/layout/MainLayout.tsx` | Modified | Extracted header to fixed full-width top bar (z-1300); moved logo from sidebar to header; added NotificationsNoneIcon placeholder; replaced sidebar brand with WarehouseSelector; sidebar now starts at top-64px with calc(100vh-64px) height |
| `frontend/src/App.tsx` | Modified | Wrapped MainLayout with WarehouseProvider inside ProtectedRoute |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Modified | Replaced local warehouseId state + WarehouseSelector with useWarehouse() context |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Modified | Same — uses global warehouse context |
| `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` | Modified | Same — uses global warehouse context |

### Layout architecture (new)

```
Header (fixed, full-width, z-1300, h-16)
  → Logo | Hamburger | Search | Spacer | Account | Notification Bell

Sidebar (fixed, top-16, z-1200, height: calc(100vh - 4rem))
  → WarehouseSelector (pill dropdown, collapse-aware)
  → SidebarNav (nav.config.tsx driven)
  → Logout button

Main content (margin-left for sidebar, pt-16 for header)
  → <Outlet />
```

---

## [PRE-ALPHA v0.5.28 | 2026-03-06] — Modular sidebar navigation component

**What changed:** Replaced the hardcoded inline nav in `MainLayout.tsx` with a modular, config-driven sidebar navigation system consisting of two new files.

**Why:** The previous sidebar encoded all routes, icons, and active-state logic directly inside `MainLayout.tsx`. Adding any new route required editing the layout component. The new architecture separates concerns — the nav config is a pure data file and `SidebarNav` is a pure render component, making it trivial to add/reorder/rename nav items without touching layout code.

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/components/layout/nav.config.tsx` | Created | TypeScript interfaces (`NavLeaf`, `NavSection`, `NavItem`), type guards, active-state helpers, and full `NAV_CONFIG` array (7 sections, 28 leaf routes) |
| `frontend/src/components/layout/SidebarNav.tsx` | Created | Accordion nav component; `collapsed`+`onNavigate` props; controlled `openSections` state with URL auto-open on route change; `menuItemStyles` identical to previous layout |
| `frontend/src/components/layout/MainLayout.tsx` | Modified | Replaced `<Menu>` block + `NAV_TOP`/`NAV_BOTTOM` arrays with `<SidebarNav>`; removed all unused icon imports; removed `useLocation` (now handled inside `SidebarNav`) |
| `frontend/src/App.tsx` | Modified | Added `/dashboard/*` catch-all; `/settings/*` wildcard for SettingsPage sub-paths |

### Navigation architecture

```
NAV_CONFIG (7 sections × ≤6 leaves)
  Dashboard     → Performance Metrics, System Alerts
  Catalog       → Items, Create New Item, Mass Upload/Import, Bundles, Translation, Item History
  Inventory     → Stock Level, Movements, Stock Check, Triggers
  Orders        → Order Details, Mass Ship, Cancellation, Returns & Exchanges
  Shipments     → Management, Group Order, Scheduling, Fleet Management
  Seller Mgmt   → Seller Profiles, Import Staging, Create New Order, Warehouse Allocation
  Settings      → Warehouse Setup, Users & Roles, Audit Logs, Platform Configurations
```

---

## [PRE-ALPHA v0.5.27 | 2026-03-06] — Remove Bundle sub-module entirely

**What changed:** Fully removed all Bundle SKU functionality from backend and frontend. The Bundle item type, BOM table, ATP calculation, and bundle fulfillment were all removed. Pages, API functions, types, routes, and nav links are cleaned up.

**Why:** Bundles were premature — the feature required a separate BOM table (`item_bundle_components`), virtual ATP logic, and a dedicated Catalog sub-section. These add complexity without immediate business need. Removing them simplifies the codebase significantly.

### Backend Changes

| File | Action | Notes |
|------|--------|-------|
| `backend/alembic/versions/20260305_…_drop_item_bundle_components.py` | Created | Drops `item_bundle_components` table |
| `backend/app/models/items.py` | Modified | Removed `ItemBundleComponent` model |
| `backend/app/schemas/items.py` | Modified | Removed `BundleComponentCreate/Update/Read`, `BundleATPRead`, `BundleMembershipRead` |
| `backend/app/routers/items.py` | Modified | Removed all `/bundle` endpoints + imports |
| `backend/app/services/bundle/` | Deleted | Removed `stock.py`, `fulfillment.py`, `__init__.py` |
| `backend/app/models/seed.py` | Modified | Removed `"Bundle"` from `_ITEM_TYPES` |

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/pages/bundles/` | Deleted | Entire directory: `BundlesListPage`, `BundleBOMTable`, `BundleMassUpload` |
| `frontend/src/pages/catalog/` | Deleted | Entire directory: `BundleFormPage`, `CatalogBundlesPage` |
| `frontend/src/pages/items/BundleComponentsTab.tsx` | Deleted | Removed bundle BOM tab from ItemFormPage |
| `frontend/src/api/base/items.ts` | Modified | Removed bundle API functions |
| `frontend/src/api/base_types/items.ts` | Modified | Removed bundle type interfaces |
| `frontend/src/api/base/warehouse.ts` | Modified | Removed `fulfillBundle` function |
| `frontend/src/api/base_types/warehouse.ts` | Modified | Removed `BundleFulfillRequest` |
| `frontend/src/App.tsx` | Modified | Removed `/catalog/bundles/*` routes |
| `frontend/src/components/layout/MainLayout.tsx` | Modified | Removed Bundles nav item + `RedeemIcon` import |
| `frontend/src/pages/items/ItemFormPage.tsx` | Modified | Removed bundle tab, `bundleTypeId` logic, bundle navigation hint |
| `frontend/src/pages/items/ItemsListPage.tsx` | Modified | Removed `bundleTypeId` exclude filter from list + counts |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Modified | Removed `BundleATPLookup` component |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Modified | Removed bundle fulfillment mode from Record Movement modal |

---

## [PRE-ALPHA v0.5.26 | 2026-03-04] — Bundle Module Refactor: BundlesListPage, BundleBOMTable, Mass Upload Scaffold

**What changed:** Replaced the old `CatalogBundlesPage` with a purpose-built `BundlesListPage`; created `BundleBOMTable` as an improved BOM editor with inline qty stepper and optimistic UI; scaffolded `BundleMassUpload` modal; updated `BundleComponentRead` type.

**Why:** The previous bundles page included Brand (irrelevant — brand belongs to component items) and lacked Virtual ATP visibility and mass upload capability. The BOM editor used a plain number input — replaced with a [−/+] stepper for easier quantity adjustment. Deletes are now optimistic (immediate removal with revert on failure) for a faster, more responsive UX.

### Frontend Changes

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/api/base_types/items.ts` | Modified | Added `category_name?: string \| null` to `BundleComponentRead` |
| `frontend/src/pages/bundles/BundlesListPage.tsx` | Created | Replaces `CatalogBundlesPage`: no Brand column; Category column; Virtual ATP column per-warehouse; Mass Upload button; `StandardActionMenu` actions |
| `frontend/src/pages/bundles/components/BundleBOMTable.tsx` | Created | Enhanced BOM table: `[−] qty [+]` stepper, category column, optimistic delete + revert, per-row save spinner |
| `frontend/src/pages/bundles/components/BundleMassUpload.tsx` | Created | Scaffold modal with CSV dropzone placeholder and template download stub |
| `frontend/src/App.tsx` | Modified | Route `/catalog/bundles` now points to `BundlesListPage` |

---

## [PRE-ALPHA v0.5.25 | 2026-03-04] — Hotfix: Apply pending warehouse soft-delete migration

**What changed:** Applied the pending Alembic migration `b3c4d5e6f7a8` (`add_soft_delete_to_warehouse`) to the live database. The migration added `deleted_at` columns to `warehouse` and `inventory_location` tables.

**Why:** The `GET /api/v1/warehouse` endpoint queries `Warehouse.deleted_at.is_(None)`, which fails with a PostgreSQL column-not-found error when the migration has not been run. This caused the Settings → Warehouse → Management card to show "Failed to load warehouses." The migration script existed but was never executed against the DB.

**Fix:** Ran `python -m alembic upgrade head` from `backend/`. DB is now at revision `b3c4d5e6f7a8 (head)`.

---

## [PRE-ALPHA v0.5.24 | 2026-03-04] — Universal Action Menu + Warehouse Soft Delete & Duplication

**What changed:** Added soft-delete support to the `warehouse` and `inventory_location` tables via Alembic migration; introduced three new warehouse endpoints (`PATCH /{id}/toggle-status`, `DELETE /{id}`, `POST /{id}/duplicate`); created a reusable `StandardActionMenu` kebab component; upgraded `WarehouseListPage` to use the new actions with an optimistic UI.

**Why:** Hard deletes are destructive and break relational history (inventory levels, movement logs, alerts). Soft delete preserves data integrity while hiding deactivated records. The action menu is a generic pattern reusable across all entity types in the system.

### Database Changes

| Table | Change |
|-------|--------|
| `warehouse` | Added `deleted_at TIMESTAMP NULL`; added partial index `idx_warehouse_not_deleted` |
| `inventory_location` | Added `deleted_at TIMESTAMP NULL`; added partial index `idx_inventory_location_not_deleted` |

**Migration:** `backend/alembic/versions/20260304_1200_00_b3c4d5e6f7a8_add_soft_delete_to_warehouse.py`

### Backend Changes

| File | Change |
|------|--------|
| `backend/app/models/warehouse.py` | Added `deleted_at: Optional[datetime]` to `Warehouse` and `InventoryLocation`; added `idx_warehouse_not_deleted` index to `Warehouse.__table_args__` |
| `backend/app/schemas/warehouse.py` | Added `deleted_at` field to `WarehouseRead`; added `WarehouseDuplicateResponse` schema |
| `backend/app/routers/warehouse.py` | Updated `GET /` to exclude soft-deleted rows; updated `GET /{id}`, `PATCH /{id}` to return 404 for deleted warehouses; added `PATCH /{id}/toggle-status`, `DELETE /{id}` (soft delete + cascade locations), `POST /{id}/duplicate` (deep copy via single `INSERT...SELECT`) |

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/api/base_types/warehouse.ts` | Added `deleted_at: string \| null` to `WarehouseRead`; added `WarehouseDuplicateResponse` interface |
| `frontend/src/api/base/warehouse.ts` | Added `toggleWarehouseStatus`, `deleteWarehouse`, `duplicateWarehouse` functions |
| `frontend/src/components/common/StandardActionMenu.tsx` | **New** — reusable kebab menu (`⋮`) with Edit / Activate|Deactivate / Duplicate / Delete options; inline confirm step for delete; click-outside close; state machine (`closed → open → confirming`) |
| `frontend/src/pages/warehouse/WarehouseListPage.tsx` | Replaced inline toggle + row-click-edit pattern with `StandardActionMenu`; added `handleToggle`, `handleDelete`, `handleDuplicate` handlers with optimistic local state updates; added auto-dismissing success banner; removed full re-fetch on every action (local state mutation instead) |

---

## [PRE-ALPHA v0.5.23 | 2026-03-04] — Settings Module Expansion (Items Data, Warehouse Locations, Platforms)

**What changed:** Extended the Settings page into three distinct sections — Items Data, Warehouse, and Platforms. Added backend CRUD for inventory locations and registered the platform router. Created `PlatformCard` and `WarehouseLocationCard` page-local components.

**Why:** Operators need a single administrative surface to configure lookup tables, warehouse storage topology, and marketplace connections without modifying the database directly.

### Backend Changes

| File | Change |
|------|--------|
| `backend/app/schemas/warehouse.py` | Added `InventoryLocationCreate` and `InventoryLocationUpdate` Pydantic schemas |
| `backend/app/routers/warehouse.py` | Added `POST /{warehouse_id}/locations`, `PATCH /locations/{location_id}`, `DELETE /locations/{location_id}` endpoints; delete guard prevents removal of locations that have inventory levels assigned |
| `backend/app/main.py` | Registered `platforms_router` at prefix `/api/v1` (exposing `GET/POST/PATCH /platforms` and `GET/POST/PATCH /sellers`) |

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/api/base_types/platform.ts` | New — `PlatformRead`, `PlatformCreate`, `PlatformUpdate`, `SellerRead`, `SellerCreate`, `SellerUpdate` types |
| `frontend/src/api/base/platform.ts` | New — `listPlatforms`, `getPlatform`, `createPlatform`, `updatePlatform`, `listSellers`, `getSeller`, `createSeller`, `updateSeller` functions |
| `frontend/src/api/base_types/warehouse.ts` | Added `InventoryLocationCreate` and `InventoryLocationUpdate` types |
| `frontend/src/api/base/warehouse.ts` | Added `createLocation`, `updateLocation`, `deleteLocation` functions |
| `frontend/src/pages/settings/PlatformCard.tsx` | New — inline Add/Edit form card for platform CRUD (name, address, postcode, API endpoint, active toggle); no delete (deactivate via toggle) |
| `frontend/src/pages/settings/WarehouseLocationCard.tsx` | New — per-warehouse location CRUD card; warehouse selector loads active warehouses; grid form for section/zone/aisle/rack/bin; location displayed as formatted code (e.g. `A-Z1-01-R3-B2`) |
| `frontend/src/pages/settings/SettingsPage.tsx` | Reorganised into three sections: **Items Data** (Item Types, Categories, Brands, UOMs, Statuses), **Warehouse** (WarehouseLocationCard), **Platforms** (PlatformCard); section descriptions added |

### Design decisions
- **Platform router prefix** — mounted at `/api/v1` (not `/api/v1/platform`) because the router's own paths begin with `/platforms` and `/sellers`
- **Location delete guard** — backend returns HTTP 400 if the location has InventoryLevel rows to prevent orphaned stock data
- **No platform delete** — platforms are reference data linked to historical orders; deactivation via `is_active` toggle is the correct operation
- **Location code format** — `section-zone-aisle-rack-bin` with empty parts omitted; fallback to `LOC-{id}` if all fields blank

---

## [PRE-ALPHA v0.5.22 | 2026-03-04 16:00] — Bundle Image Upload + Delete

**What changed:** Added image upload to `BundleFormPage` and a delete action to `CatalogBundlesPage`. The Bundles list now also shows a thumbnail alongside each bundle name.

**Why:** Bundles are presented to operators alongside regular items; having no image meant they could not be visually differentiated in lists or exports. Delete was needed so operators can remove test/obsolete bundles without going through the DB directly.

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/pages/catalog/BundleFormPage.tsx` | Added `imageUrl`, `imageUploading` state and `fileInputRef`; image upload UI block (click-to-upload square with preview, remove button, hidden `<input type="file">`); `image_url` included in both `createItem` and `updateItem` payloads; edit-mode load sets `imageUrl` from `item.image_url` |
| `frontend/src/pages/catalog/CatalogBundlesPage.tsx` | Added `deleteItem` + `DeleteOutlineIcon` + `ImageIcon` imports; `deleting` state; `handleDelete()` with confirm dialog; Bundle Name column shows 10×10 thumbnail (`image_url` or placeholder); Actions column expanded to edit + delete icon pair |

### Design decisions
- **Same image upload pattern as ItemFormPage** — `uploadItemImage(file)` call, separate `imageUploading` spinner state, hidden `<input type="file">` cleared after each upload to allow re-selecting the same file
- **Thumbnail in list** — 10×10 rounded square consistent with `ItemsListPage`; placeholder shows `ImageIcon` in muted colour
- **Soft-delete aware** — Delete button disabled if `b.deleted_at` is already set (bundle already soft-deleted); consistent with items behaviour

---

## [PRE-ALPHA v0.5.21 | 2026-03-04 14:00] — Bundles Sub-Module (Catalog)

**What changed:** New Bundles sub-module under the Catalog section of the frontend. Allows operators to create and manage Bundle items (grouped products sold as a single unit) from a dedicated UI, separate from the general Items form.

**Why:** Bundles have a distinct creation workflow — they require selecting component items, setting per-component quantities, and either manually entering or auto-generating a composite SKU. Embedding this inside the general Item form would produce a confusing UX for non-bundle items. A dedicated sub-module gives bundle management a clear, purpose-built interface aligned with the backend's `ItemBundleComponent` BOM schema introduced in v0.5.17.

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/pages/catalog/CatalogBundlesPage.tsx` | NEW — Bundle list page: resolves Bundle type ID via `listItemTypes()`, filters `listItems({ item_type_id })`, DataTable with ID/Name/SKU/Category/Brand/Status/Actions columns; active toggle, search, pagination |
| `frontend/src/pages/catalog/BundleFormPage.tsx` | NEW — Create/edit form with two modes: **Create** uses local `PendingComponent[]` state → batch-submits (create item then loop `addBundleComponent`); **Edit** renders `BundleComponentsTab` for immediate API calls; auto-generate SKU toggle concatenates component SKUs; live total-qty indicator (min ≥ 2 validation) |
| `frontend/src/components/layout/MainLayout.tsx` | Added `RedeemIcon` import; added Bundles `MenuItem` under Catalog `SubMenu` with active path detection for `/catalog/bundles` and `/catalog/bundles/*` |
| `frontend/src/App.tsx` | Added imports for `CatalogBundlesPage` and `BundleFormPage`; added 3 routes: `/catalog/bundles`, `/catalog/bundles/new`, `/catalog/bundles/:id/edit` |

### Design decisions
- **Separate sub-module** — Bundles are Items with `item_type = "Bundle"` at the DB level, but their creation workflow (BOM, SKU generation, qty validation) is distinct enough to warrant a dedicated route/page rather than a conditional section in ItemFormPage
- **Bundle type ID resolution** — `listItemTypes()` is called on mount in `CatalogBundlesPage` to find the Bundle type ID; this ID drives the `item_type_id` filter for `listItems()` — avoids a new backend endpoint
- **SKU auto-generate** — `pendingComponents.map(c => c.item_sku).join('_')`; reactive via `useEffect` watching `generatedSku` and `autoSkuEnabled`; input goes read-only when toggled on
- **Min-qty ≥ 2 validation** — `sum(quantity_per_bundle)` computed live; colour-coded indicator (green ≥ 2, amber > 0 but < 2, neutral 0); submit disabled unless valid
- **Create vs Edit duality** — Create mode: local state + batch submit to minimise incomplete bundle states in DB; Edit mode: embeds `BundleComponentsTab` (immediate API calls, already proven from v0.5.20)

---

## [PRE-ALPHA v0.5.20 | 2026-03-04 10:00] — Bundle SKU Frontend UI

**What changed:** Frontend Phase 4 of the Bundle SKU module. Adds Bundle Component management to the Item Form, a Bundle ATP Lookup tool to Inventory Levels, and bundle-aware fulfillment mode to the Record Movement modal.

**Why:** The backend bundle API (v0.5.17–v0.5.19) was complete but had no frontend. This release closes the loop, allowing warehouse operators to: (1) define Bill-of-Materials for bundle items without touching the API directly, (2) look up live ATP for any bundle in a warehouse without running queries, and (3) record a bundle sale that atomically deducts all component stocks in a single transaction.

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/api/base_types/items.ts` | Added `BundleComponentRead`, `BundleComponentCreate`, `BundleComponentUpdate`, `BundleATPRead`, `BundleMembershipRead` types |
| `frontend/src/api/base/items.ts` | Added `listBundleComponents`, `addBundleComponent`, `updateBundleComponent`, `deleteBundleComponent`, `getBundleATP`, `getBundleMemberships` API functions |
| `frontend/src/api/base_types/warehouse.ts` | Added `reserved_quantity` to `InventoryLevelEnrichedRead`; added `ReserveRequest`, `ReserveResponse`, `ReleaseRequest`, `BundleFulfillRequest` types |
| `frontend/src/api/base/warehouse.ts` | Added `reserveStock`, `releaseStock`, `fulfillBundle` API functions; updated imports |
| `frontend/src/pages/items/BundleComponentsTab.tsx` | NEW — BOM management tab: lists components (name, SKU, qty/bundle, active toggle, inline confirm remove); item search autocomplete (300ms debounce); add form with validation |
| `frontend/src/pages/items/ItemFormPage.tsx` | Added tab strip (Details / Bundle Components) shown when `item_type = "Bundle"` in edit mode; renders `BundleComponentsTab` when active |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Added `BundleATPLookup` collapsible card — item search filters for Bundle type, calls `getBundleATP` + `listBundleComponents`, shows ATP with colour-coded value and component breakdown; `Qty` column now shows `reserved_quantity` as subtitle |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | When a Bundle item is selected, shows Bundle/Manual mode selector; Bundle Fulfillment mode replaces transaction rows with bundle qty + order reference fields; submits to `POST /warehouse/fulfill/bundle` |

---

## [PRE-ALPHA v0.5.17–v0.5.19 | 2026-03-04 01:00] — Bundle SKU & Component Inventory Management

**What changed:** Full backend implementation of Bundle SKU inventory management (Phases 1–3). Adds a Bill-of-Materials table, pessimistic stock reservation, atomic multi-component stock deduction, and a new set of API endpoints.

**Why:** Warehouse operations require selling grouped product sets (e.g., "3-pack T-Shirt") where multiple physical component items are deducted from stock in a single atomic transaction. Without this, concurrent orders can oversell shared component stock. The reservation pattern (`reserved_quantity`) prevents this race condition across both standalone and bundle sale paths.

### Schema Changes (v0.5.17)

| File | Change |
|------|--------|
| `backend/app/models/items.py` | Added `ItemBundleComponent` model — Bill-of-Materials join table; added `UniqueConstraint` import; no back-populate on `Item` to avoid dual-FK ambiguity |
| `backend/app/models/warehouse.py` | Added `reserved_quantity: int` column to `InventoryLevel`; updated `stock_status` property to use ATP (`quantity_available - reserved_quantity`); added `atp` property |
| `backend/app/models/seed.py` | Added `"Bundle"` to `_ITEM_TYPES` seed list (7th item type) |
| `backend/alembic/versions/20260304_0000_00_a2b3c4d5e6f7_add_bundle_tables.py` | New migration: creates `item_bundle_components` table + indexes + unique constraint; adds `reserved_quantity` column to `inventory_levels` |

### Bundle Service Layer (v0.5.18)

| File | Purpose |
|------|---------|
| `backend/app/services/bundle/__init__.py` | Package init |
| `backend/app/services/bundle/stock.py` | `compute_bundle_atp()` — real-time ATP = MIN(FLOOR(comp_ATP / qty_per_bundle)); `get_bundle_bom()` helper |
| `backend/app/services/bundle/fulfillment.py` | `reserve_inventory()`, `release_reservation()`, `deduct_bundle_stock()` — all use SELECT … FOR UPDATE for row-level locking; `InsufficientStockError`, `BundleNotFoundError` exceptions |

### API Endpoints (v0.5.19)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/items/{id}/bundle` | No | List all BOM rows for a bundle |
| `POST` | `/api/v1/items/{id}/bundle/components` | Yes | Add component to BOM |
| `PUT` | `/api/v1/items/{id}/bundle/components/{comp_id}` | Yes | Update component qty / active flag |
| `DELETE` | `/api/v1/items/{id}/bundle/components/{comp_id}` | Yes | Remove component from BOM |
| `GET` | `/api/v1/items/{id}/bundle/atp?warehouse_id=` | No | Compute virtual ATP for bundle |
| `GET` | `/api/v1/items/{id}/bundle/memberships` | No | List all bundles that contain this item |
| `POST` | `/api/v1/warehouse/reserve` | Yes | Reserve stock for a standalone item |
| `POST` | `/api/v1/warehouse/release` | Yes | Release reservation (cancellation) |
| `POST` | `/api/v1/warehouse/fulfill/bundle` | Yes | Atomic bundle stock deduction |

### Schema Updates

| File | Change |
|------|--------|
| `backend/app/schemas/items.py` | Added `BundleComponentCreate`, `BundleComponentUpdate`, `BundleComponentRead`, `BundleATPRead`, `BundleMembershipRead` |
| `backend/app/schemas/warehouse.py` | Added `reserved_quantity` field to `InventoryLevelRead` + `InventoryLevelEnrichedRead`; added `ReserveRequest`, `ReserveResponse`, `ReleaseRequest`, `BundleFulfillRequest` |

---

## [PRE-ALPHA v0.5.12.1 | 2026-03-04 00:00] — Warehouse Module Bug Fixes

**What changed:** Fixed two duplicate declarations introduced during warehouse module implementation.

**Why:** The previous session added a second `list_movement_types` endpoint function in `warehouse.py` (the original misplaced one was already there; the fixed one was prepended — leaving two identical route handlers). Similarly, `main.py` had the warehouse router registered twice. Both duplicates are now removed.

| File | Fix |
|------|-----|
| `backend/app/routers/warehouse.py` | Removed duplicate `list_movement_types` function (the original misplaced version after `list_warehouses`; the correct pre-`/{warehouse_id}` version is retained) |
| `backend/app/main.py` | Removed duplicate `app.include_router(warehouse_router)` call (was registered twice, causing duplicate route registration) |

---

## [PRE-ALPHA v0.5.12 | 2026-03-03 21:00] — Warehouse & Inventory Frontend Module

**What changed:** Full warehouse/inventory module — backend enrichments, frontend types, API layer, 4 new pages, sidebar Inventory submenu, and routing.

**Why:** The warehouse backend had been written but was disconnected from the frontend. This release activates the warehouse router, adds 4 missing endpoints (enriched inventory levels, movement types, movement history + creation, alert resolution), and builds the full frontend surface for warehouse operations.

### Backend Changes

| File | Change |
|------|--------|
| `backend/app/schemas/warehouse.py` | Added `LocationSummary`, `InventoryLevelEnrichedRead`, `MovementTypeRead`, `InventoryMovementRead`, `InventoryTransactionCreate`, `InventoryMovementCreate`, `AlertResolveRequest`; updated `InventoryAlertRead` with resolution fields |
| `backend/app/routers/warehouse.py` | Rewrote with 11 endpoints: enriched `GET /{id}/inventory` (joins Item + Location, computed stock_status), `GET /movement-types`, `GET /{id}/movements` (paginated, joins through transactions), `POST /movements` (creates movement + transactions, updates levels, prevents negative stock), `PATCH /alerts/{id}/resolve` |

### Frontend Changes

| File | Action |
|------|--------|
| `frontend/src/api/base_types/warehouse.ts` | Created — 13 TypeScript interfaces/types for all warehouse entities |
| `frontend/src/api/base/warehouse.ts` | Created — 11 API functions (warehouses, locations, inventory, alerts, movements) |
| `frontend/src/pages/warehouse/StockStatusBadge.tsx` | Created — color-coded badge for stock status (OK/Low/Critical/Out of Stock/Overstock) |
| `frontend/src/pages/warehouse/WarehouseSelector.tsx` | Created — reusable warehouse dropdown, loads active warehouses on mount |
| `frontend/src/pages/warehouse/WarehouseListPage.tsx` | Created — warehouse CRUD list with inline create/edit modal, active toggle |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Created — stock matrix with warehouse selector, summary chips, status filter tabs, search, DataTable |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Created — movement history with record modal (item autocomplete, multi-transaction support for transfers) |
| `frontend/src/pages/warehouse/InventoryAlertsPage.tsx` | Created — alert center with resolve modal, resolved/unresolved filter, summary chips |
| `frontend/src/App.tsx` | Added 4 routes: `/inventory/warehouses`, `/inventory/levels`, `/inventory/movements`, `/inventory/alerts` |
| `frontend/src/components/layout/MainLayout.tsx` | Added Inventory submenu with 4 nav items (Warehouses, Stock Levels, Movements, Alerts) |
| `docs/official_documentation/web-api.md` | Updated Warehouse section with 4 new endpoints and response types; added warehouse API functions to frontend table |

---

## [PRE-ALPHA v0.5.11 | 2026-03-03 16:00] — Items Mass Upload

**What changed:** Full end-to-end mass upload for the Items catalog. Users can upload a CSV or Excel file from the new `/catalog/items/upload` page. Client-side parsing (via `xlsx`) shows a 5-row preview before confirmation. The backend validates every row, resolves FK names (UOM/Brand/Category/Item Type) to IDs, rejects duplicates, and returns a structured result with per-row errors.

**Why:** Manual item creation one-by-one is impractical for large catalogs. Mass upload lets operators seed or refresh hundreds of items in a single operation, with transparent error feedback so bad rows can be fixed without re-uploading the entire file.

### Backend Changes

| File | Change |
|------|--------|
| `backend/app/schemas/items.py` | Added `ImportRowError` and `ImportResult` Pydantic models |
| `backend/app/services/items_import/__init__.py` | New service package (empty init) |
| `backend/app/services/items_import/parser.py` | `parse_file()` — reads CSV/Excel, normalises column aliases, returns `list[dict]` |
| `backend/app/services/items_import/validator.py` | `validate_and_resolve()` — validates required fields, lengths, no-spaces on SKU, FK name-to-ID resolution (1 SELECT per table), in-file + DB duplicate detection |
| `backend/app/services/items_import/importer.py` | `import_items()` — orchestrates parse → validate → bulk insert |
| `backend/app/routers/items.py` | Added `POST /import` endpoint (auth required, 10 MB limit, .csv/.xlsx/.xls only) |

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/src/api/base_types/items.ts` | Added `ImportRowError` and `ItemsImportResult` interfaces |
| `frontend/src/api/base/items.ts` | Added `importItems(file)` function (multipart FormData, same pattern as `uploadItemImage`) |
| `frontend/src/pages/items/ItemsMassUploadPage.tsx` | New page: instructions card, drag-and-drop drop zone, `xlsx` client-side parse + 5-row preview table, "Confirm & Upload" flow, result card with success/error summary and row-level error table |
| `frontend/src/App.tsx` | Added route `/catalog/items/upload` → `ItemsMassUploadPage` |
| `frontend/src/pages/items/ItemsListPage.tsx` | Wired "Mass Upload" button to navigate to `/catalog/items/upload`; replaced `KeyboardArrowDownIcon` with `UploadFileIcon` |

### npm dependency added
- `xlsx` (SheetJS) — client-side Excel/CSV parsing for preview

---

## [PRE-ALPHA v0.5.10.1 | 2026-03-03] — Documentation Sync

### Files Changed

#### `docs/official_documentation/frontend-development-progress.md`
**What:** Added progress entries for v0.5.3–v0.5.10; updated Rule 7 to the new file-organisation rule.
**Why:** Sync accumulated frontend work into the official progress log; clarify that page files and their page-specific items belong inside `src/pages/<page>/`, not in `src/components/`.

#### `docs/official_documentation/web-api.md`
**What:** Added full Items API documentation — 20+ endpoints (CRUD for items, types, categories, brands, UOMs, image upload, counts).
**Why:** All new endpoints added since v0.5.3 were undocumented in the API reference.

#### `docs/official_documentation/database_structure.md`
**What:** Minor cleanup of remaining local-dev notes not yet pushed.
**Why:** Keep schema reference clean; operational notes belong in README/setup guides.

---

## [PRE-ALPHA v0.5.10 | 2026-03-03 14:00] — Create Item: Toggle Switch, Validation & Backend Integrity

**What changed:** Hardened the Create/Edit Item form with a proper status toggle switch, comprehensive client-side validation (no-spaces rule on Master SKU, corrected field max-lengths), fixed select placeholder labels to "Select", and added backend 409 conflict handling for duplicate Master SKUs. Added a 15-test automated integration suite and a manual testing guide.

**Why:** The previous Status field was a `<select>` with string values requiring a coercion hack. A toggle switch is more appropriate UX for a boolean status. The `master_sku` had no uniqueness validation on the frontend, and the backend returned an uninformative 500 on duplicate. `sku_name` max-length (200) didn't match the backend schema (500). These changes make the form robust, the API self-documenting on conflict, and add test coverage.

### Backend Changes

| File | Change | Why |
|------|--------|-----|
| `backend/app/routers/items.py` | Import `IntegrityError` from SQLAlchemy; wrap `create_item` flush in try/except → 409 with detail message on duplicate `master_sku` | Duplicate SKU previously returned unhandled 500; now returns a clear 409 Conflict |

### Frontend Changes

| File | Change | Why |
|------|--------|-----|
| `frontend/src/pages/items/ItemFormPage.tsx` | Replace Status `<select>` with a CSS toggle switch using `watch('is_active')` + `setValue` | Boolean field needs boolean UI; removes string-to-bool coercion hack from onSubmit |
| `frontend/src/pages/items/ItemFormPage.tsx` | Add `validate: { noSpaces }` to `master_sku` registration | SKUs must not contain spaces; backend would reject them implicitly but UX is better with immediate feedback |
| `frontend/src/pages/items/ItemFormPage.tsx` | Fix `sku_name` maxLength 200 → 500 | Schema defines max_length=500; frontend was more restrictive than the backend |
| `frontend/src/pages/items/ItemFormPage.tsx` | Change select `<option value="">` labels from field names to "Select" | Consistent placeholder UX across all dropdowns |
| `frontend/src/pages/items/ItemFormPage.tsx` | Row 4 changed from 3-col (UOM/ItemType/Status) to 2-col (UOM/ItemType) + separate Status toggle section | Toggle needs its own row for visual clarity |
| `frontend/src/pages/items/ItemFormPage.tsx` | Add `disabled:cursor-not-allowed` to submit button | Clear disabled affordance when form is submitting |
| `frontend/src/pages/items/ItemFormPage.tsx` | Remove `typeof data.is_active === 'string'` coercion in `onSubmit` | Toggle always sets a real boolean; coercion was a workaround for the old select |

### Test Artefacts

| File | Description |
|------|-------------|
| `backend/tests/test_items_create.py` | 15 pytest integration tests (TC-01 to TC-15): happy path, validation, auth, conflict, response structure, timestamps |
| `docs/official_documentation/testing_items_create.md` | Manual testing guide: 6 sections (form validation, happy path, backend conflict, auth, image upload, automated run) |

---

## [PRE-ALPHA v0.5.9 | 2026-03-03 12:00] — VariationBuilder Redesign

**What changed:** Completely redesigned the `VariationBuilder` component UI and removed `price`/`stock` from variation combinations.

**Why:** The previous design used an auto-grow chip/input approach that didn't match the target e-commerce seller-centre style. The new design uses a 2-column option grid with character counters, drag-handle indicators, and per-option delete controls — matching the specified design reference. Price and stock are removed from variations as they will be managed elsewhere in the order/pricing module.

### Frontend Changes

| File | Change | Why |
|------|--------|-----|
| `frontend/src/pages/items/VariationBuilder.types.ts` | Removed `price` and `stock` from `VariationCombination` interface | Price/stock management removed from variation builder per design spec |
| `frontend/src/pages/items/VariationBuilder.utils.ts` | Updated `syncCombinations` (new combos omit price/stock) and `migrateOldFormat` (strips price/stock from old DB data) | Type alignment; backwards-compatible migration of existing saved data |
| `frontend/src/pages/items/VariationBuilder.tsx` | Full redesign: 2-column option grid with char counters (N/20), drag-handle icon per option, inline name counter (N/14), max 5 options per variation, `• Variations` section header; combination table now shows only Image + variation values + SKU (no Price/Stock columns) | Matches target design; simplifies the combination table |

### Design Specifications

- **Variation name input**: inline right-aligned counter `N/14` (max 14 chars), delete icon on far right
- **Options**: 2-column grid; each option has counter `N/20`, `DragIndicatorIcon` handle, close/delete button
- **Draft slot**: always visible "Input" placeholder with `0/20` counter until 5 options are reached
- **Max options**: 5 per variation
- **Max variations**: 2 (unchanged)
- **Combination table columns**: Image | [Variation names…] | SKU (Price and Stock removed)
- **Batch apply**: SKU-only (simplified from previous price+stock+SKU)

---

## [PRE-ALPHA v0.5.8 | 2026-03-02 21:00] — Item Main Image Upload

**What changed:** Added full image upload capability to the Item Create/Edit form. A new "Product Image" section at the top of the form card lets users click to upload an image (JPG/PNG/WebP/GIF, max 5 MB), previews it inline, and includes a "Remove image" action. Images are stored on the local filesystem at `backend/uploads/items/` and served via FastAPI StaticFiles.

**Why:** Items had no visual representation. E-commerce product management requires main product images for catalog display. The upload-first pattern (separate endpoint returns URL, URL included in item JSON payload) keeps the existing CRUD API simple while adding file handling.

### Backend Changes

| File | Change | Why |
|------|--------|-----|
| `backend/app/models/items.py` | Added `image_url` field (VARCHAR 500, nullable) | Store the path/URL of the uploaded main product image |
| `backend/app/schemas/items.py` | Added `image_url` to `ItemCreate`, `ItemUpdate`, `ItemRead` | Expose image URL through the API |
| `backend/app/routers/items.py` | Added `POST /items/upload-image` endpoint, updated `_item_to_read` | Handle multipart file upload with content-type/size validation, return URL |
| `backend/app/main.py` | Mounted `StaticFiles` at `/uploads`, auto-create `uploads/items/` directory | Serve uploaded images via HTTP |
| `backend/alembic/versions/20260302_..._f6a7b8c9d0e1` | Migration: add `image_url` column to `items` table | DB schema evolution |

### Frontend Changes

| File | Change | Why |
|------|--------|-----|
| `frontend/src/api/base_types/items.ts` | Added `image_url` to `ItemRead`, `ItemCreate`, `ItemUpdate` | TypeScript type alignment with backend |
| `frontend/src/api/base/items.ts` | Added `uploadItemImage()` function (FormData POST) | API client for image upload |
| `frontend/src/pages/ItemFormPage.tsx` | Added image upload area (click-to-upload, preview, remove), `imageUrl`/`imageUploading` state, wired into submit payload | Main UI for product image management |
| `frontend/vite.config.ts` | Added `/uploads` proxy rule | Dev server forwards image requests to backend |

### Upload Endpoint

- **Route:** `POST /api/v1/items/upload-image`
- **Auth:** JWT required
- **Input:** `multipart/form-data` with `file` field
- **Validation:** Content type (JPEG/PNG/WebP/GIF), max 5 MB
- **Storage:** `backend/uploads/items/{uuid}_{filename}`
- **Response:** `{ "url": "/uploads/items/{uuid}_{filename}" }`

### Build

- Production: 493.07 kB JS, 25.86 kB CSS (zero TypeScript errors)

---

## [PRE-ALPHA v0.5.7 | 2026-03-02 17:30] — VariationBuilder Component (Dynamic Variation Matrix)

**What changed:** Replaced the basic variation attribute rows in the Item Create/Edit form with a full e-commerce-style VariationBuilder. The new component has two parts: (1) a builder UI where users define up to 2 variation dimensions (e.g. "Colour", "Size") with auto-growing option inputs, and (2) a dynamically generated combination table showing every cartesian product row with per-variation SKU, Price, Stock, and image placeholder fields. Includes batch-apply functionality for mass-updating all rows.

**Why:** The previous variation section was text-only (attribute name + comma-separated values) with no way to assign per-variant SKUs, prices, or stock. E-commerce sellers need a matrix view to manage individual variation data before listing products on platforms like Shopee/Lazada.

### New Files

| File | Purpose | Why |
|------|---------|-----|
| `frontend/src/pages/items/VariationBuilder.types.ts` | Shared interfaces: `VariationsData`, `VariationAttribute`, `VariationCombination`, `VariationBuilderProps` | Separated from component to avoid circular imports when `ItemFormPage` needs the type |
| `frontend/src/pages/items/VariationBuilder.utils.ts` | Pure functions: `cartesianProduct()`, `syncCombinations()`, `migrateOldFormat()` | Testable utility logic independent of React |
| `frontend/src/pages/items/VariationBuilder.tsx` | Main component with two internal sub-components: `VariationLevel` (builder UI) and `CombinationTable` (matrix table) | Page-specific component per ground rule #7 |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/src/pages/ItemFormPage.tsx` | Removed old `VariationRow` type, `useFieldArray`, `variationsToFormRows`/`formRowsToVariationsData` helpers, and inline variations JSX. Added `useState<VariationsData>`, integrated `<VariationBuilder>` component, updated `onSubmit` to pass JSONB directly. | Old flat-row approach incompatible with the new nested matrix; controlled component pattern is cleaner than fighting `useFieldArray` with deeply nested data |

### JSONB Structure Change (backwards-compatible)

Old format (attributes only):
```json
{ "attributes": [{ "name": "Color", "values": ["Red", "Blue"] }] }
```

New format (attributes + combinations):
```json
{
  "attributes": [{ "name": "Color", "values": ["Red", "Blue"] }],
  "combinations": [
    { "values": ["Red"], "sku": "SKU-RED", "price": 29.99, "stock": 100, "image": null },
    { "values": ["Blue"], "sku": "SKU-BLU", "price": 29.99, "stock": 50, "image": null }
  ]
}
```

`migrateOldFormat()` auto-generates `combinations` from old-format data on load.

### Build

- Production: 491.28 kB JS, 25.68 kB CSS (zero TypeScript errors)

---

## [PRE-ALPHA v0.5.6.1 | 2026-03-02 16:00] — Move Item Type Filter to Tabs Row

**What changed:** Relocated the "Item Type" dropdown from the filter row (Search + Category + Brand + Item Type) to the tabs row (All | Live | Unpublished | Deleted). Item Type now sits on the far right of the tabs bar using `justify-between` flex layout, acting as a global workspace toggle rather than a minor search filter.

**Why:** Item Type (Outgoing Product, Raw Material, Office Supply) is a high-level workspace context — it should be visually elevated above the search/filter row to signal it controls the entire item view, not just one search dimension. This also frees space in the filter row for the remaining 3 controls.

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/src/pages/items/ItemFilters.tsx` | Removed `itemTypeId`/`onItemTypeChange` props, `itemTypes` state, `listItemTypes` import, and Item Type `<select>` | Item Type no longer belongs in the filter bar |
| `frontend/src/pages/ItemsListPage.tsx` | Added `itemTypes` state + `listItemTypes` fetch; moved Item Type `<select>` into tabs row with `flex flex-wrap items-center justify-between`; removed `itemTypeId`/`onItemTypeChange` from `<ItemFilters>` props | Tabs row now shows tabs on the left + Item Type dropdown on the right, with `flex-wrap` for responsive wrapping |

---

## [PRE-ALPHA v0.5.6 | 2026-03-02] — Items Page Redesign (List + Form)

**What changed:** Redesigned the Items list page and Create/Edit form to match reference design. Added tab-based status filtering, combined item column with image placeholder, checkbox selection, page-number pagination, and flattened the form from tabbed to single-card layout.

**Why:** The previous Items module was functional but lacked the polished UX expected for a production-ready catalog management interface. The redesign improves discoverability (tab counts show item distribution), filtering (inline search + dropdowns), and data density (combined columns, expandable rows).

### Backend Changes

| File | Change | Why |
|------|--------|-----|
| `backend/app/routers/items.py` | Added `GET /items/counts` endpoint returning `{all, live, unpublished, deleted}` | Tab labels need real-time counts without 4 separate list calls |
| `backend/app/routers/items.py` | Added `item_type_id` and `include_deleted` query params to `GET /items` | Enables Item Type filter dropdown and "Deleted" tab |
| `backend/app/routers/items.py` | Changed base query: `include_deleted=True` shows ONLY soft-deleted items | Clean separation: non-deleted vs deleted-only (not mixed) |
| `backend/app/routers/items.py` | Updated `_item_to_read` to pass `deleted_at` | Frontend needs `deleted_at` for "Deleted" status badge |
| `backend/app/schemas/items.py` | Added `deleted_at: Optional[datetime] = None` to `ItemRead` | Exposes soft-delete timestamp to frontend |

### Frontend Changes

| File | Change | Why |
|------|--------|-----|
| `frontend/src/api/base/items.ts` | Added `item_type_id`, `include_deleted` to `ListItemsParams`; added `getItemCounts()` | Supports new filters and tab count badges |
| `frontend/src/api/base_types/items.ts` | Added `deleted_at: string \| null` to `ItemRead` | Mirrors backend schema change |
| `frontend/src/components/common/DataTable.tsx` | Added `selectable`, `selectedIds`, `onSelectChange`, `noCard` props; page-number pagination with ellipsis | Checkbox selection for bulk actions; embeddable in parent card; better pagination UX |
| `frontend/src/pages/items/ItemFilters.tsx` | Moved from `components/items/`; added search input + Item Type dropdown; removed Active/Inactive filter | Follows page-specific component rule; tabs now handle status filtering |
| `frontend/src/pages/ItemsListPage.tsx` | Full redesign: card wrapper, tab bar (All/Live/Unpublished/Deleted), inline filters, combined Items column (image+name+SKU), status badges, expand/collapse variations | Matches reference design with improved data density and filtering |
| `frontend/src/pages/ItemFormPage.tsx` | Flattened tabs → single card; reordered fields (Name+SKU → Description → Category+Brand → UOM+Type+Status); inline variations section; orange Save button | Simpler form layout matching reference; all fields visible at once |

### Build

- Production: 489.60 kB JS, 24.55 kB CSS (zero TypeScript errors)

---

## [PRE-ALPHA v0.5.5.2 | 2026-03-02] — Remove product_number from Item Model

**What changed:** Removed the `product_number` column from the Item model, database, schemas, API, frontend types, and reference loader.

**Why:** The `product_number` field (Excel "No." column from item master upload) served no purpose in the WOMS system. It was a row counter from the Excel file, not a meaningful business attribute. Removing it simplifies the Item model.

### Files changed

| File | Change | Why |
|------|--------|-----|
| `backend/app/models/items.py` | Removed `product_number` field from `Item` class | Field not used by any business logic |
| `backend/app/schemas/items.py` | Removed `product_number` from `ItemRead` | Aligns schema with model |
| `backend/app/routers/items.py` | Removed `product_number` from `_item_to_read()` helper | Aligns router with schema |
| `backend/app/services/reference_loader/loader.py` | Removed `product_number` parsing from `load_item_master()` | No longer stored in DB |
| `frontend/src/api/base_types/items.ts` | Removed `product_number` from `ItemRead` interface | Mirrors backend schema |
| `docs/official_documentation/database_structure.md` | Removed `product_number` from both ERD sections | Keeps DB docs in sync |
| `docs/official_documentation/web-api.md` | Removed `product_number` from ItemRead schema table | Keeps API docs in sync |

### Database

- `ALTER TABLE items DROP COLUMN product_number` executed via `drop_product_number.py`

---

## [PRE-ALPHA v0.5.5.1 | 2026-03-02 HH:MM] — Database: Reset All Item Data

**What changed:** Cleared all item-related tables in `woms_db` and reset auto-increment sequences to 1 so items can be re-imported fresh.

**Why:** User requested a clean slate for item data — old data (499 items from previous master upload) needed to be removed before re-importing corrected item master data.

### Tables cleared

| Table | Rows removed | Sequence reset to |
|-------|-------------|-------------------|
| `items` | 499 | 1 |
| `items_history` | 0 | 1 |
| `status` | 5 | 1 |
| `item_type` | 5 (re-seeded: 6) | 7 (after re-seed) |
| `category` | 1 | 1 |
| `brand` | 0 | 1 |
| `base_uom` | 8 (re-seeded: 8) | 9 (after re-seed) |

**Method:** `reset_items.py` script — DELETE in FK-safe order + `setval()` to reset sequences. `item_type` and `base_uom` re-seeded from `seed.py` since the application depends on them.

**Note:** TRUNCATE RESTART IDENTITY was not possible because `woms_user` does not own the sequences; used DELETE + setval() as a workaround.

---

## [PRE-ALPHA v0.5.5 | 2026-03-02] — Items: Add is_active, Detach Status Table

**What changed:** Replaced the `status_id` FK (linked to `status` lookup table) on the Item model with a direct `is_active: bool` field. Removed all Status CRUD endpoints from the items router. Updated frontend to use Active/Inactive badge and filter instead of a status dropdown. Status table kept in DB but no longer referenced by Items.

### Backend

| File | Change | Why |
|------|--------|-----|
| `backend/app/models/items.py` | Removed `status_id` FK, removed `status` relationship, added `is_active: bool` field. Removed `Status.items` back_populates. | Simplifies item model — active/inactive is sufficient vs. a 5-value lookup table |
| `backend/app/schemas/items.py` | Removed `StatusRead`/`StatusCreate`/`StatusUpdate`. Replaced `status_id` with `is_active` in Item schemas. | Aligns schemas with new model |
| `backend/app/routers/items.py` | Removed all Status CRUD endpoints (4 endpoints). Changed `status_id` filter → `is_active` filter. Removed `selectinload(Item.status)`. | Eliminates unused status management; simplifies queries |
| `backend/app/models/seed.py` | Removed `_STATUSES` seed data and status INSERT block | Status table no longer seeded (table remains in DB) |

### Frontend

| File | Change | Why |
|------|--------|-----|
| `frontend/src/api/base_types/items.ts` | Replaced `status_id` → `is_active: boolean`. Removed `status` nested object. | Mirrors backend schema changes |
| `frontend/src/api/base/items.ts` | Removed `normaliseStatus()`, `listStatuses()`, `createStatus()`, `updateStatus()`, `deleteStatus()`. Changed `status_id` → `is_active` in params. | Removes unused status API functions |
| `frontend/src/components/items/ItemFilters.tsx` | Replaced status dropdown with All/Active/Inactive select | Simpler UX with boolean filter |
| `frontend/src/pages/ItemsListPage.tsx` | Updated filter state, column display (green Active / gray Inactive badge) | Visual clarity for item status |
| `frontend/src/pages/ItemFormPage.tsx` | Replaced status select with Active checkbox | Simple toggle instead of dropdown |

### Documentation

| File | Change |
|------|--------|
| `docs/official_documentation/web-api.md` | Removed Status endpoints, updated Items schemas to use `is_active` |
| `docs/official_documentation/database_structure.md` | Removed `status` entity from overview + module ER diagrams, removed `status ||--o{ items` relationship, removed `Table: status` section, replaced `status_id` with `is_active` in items table definition, updated `items_history` and `audit_log` JSONB examples, added `idx_items_is_active` B-tree index, updated table counts (47→46, Items 7→6) |

---

## [PRE-ALPHA v0.5.4 | 2026-03-02] — Items Module (Master Catalog)

**What changed:** Implemented the Items module frontend — a paginated, searchable, filterable master item catalog with full CRUD, variation support, and a multi-tab creation/edit form powered by `react-hook-form`. Added a reusable `DataTable` component. Activated the warehouse backend router (prep for future). Added Catalog sidebar navigation group.

### Dependencies Added
- `react-hook-form` — multi-tab form with dynamic field arrays for item variations

### Backend

| File | Change | Why |
|------|--------|-----|
| `backend/app/main.py` | Uncommented warehouse router registration | Activates 8 warehouse endpoints at `/api/v1/warehouse/` for future use |

### Frontend — New Files

| File | Purpose |
|------|---------|
| `frontend/src/api/base_types/items.ts` | Extended with `ItemRead`, `ItemCreate`, `ItemUpdate`, `PaginatedResponse<T>` types |
| `frontend/src/api/base/items.ts` | Extended with 5 item CRUD functions: `listItems`, `getItem`, `createItem`, `updateItem`, `deleteItem` |
| `frontend/src/components/common/DataTable.tsx` | Reusable paginated table: server-side pagination, search, row expansion, loading/error/empty states |
| `frontend/src/components/items/ItemFilters.tsx` | Filter bar with Status, Category, Brand dropdowns + clear button |
| `frontend/src/pages/ItemsListPage.tsx` | Master catalog page: DataTable + filters + search + row expansion for variations + edit/delete actions |
| `frontend/src/pages/ItemFormPage.tsx` | Create/Edit form: Tab 1 (Basic Info with 9 fields) + Tab 2 (Variations with dynamic field array + SKU preview grid) |

### Frontend — Modified Files

| File | Change | Why |
|------|--------|-----|
| `frontend/src/App.tsx` | Added 3 routes: `/catalog/items`, `/catalog/items/new`, `/catalog/items/:id/edit` | Catalog routing |
| `frontend/src/components/layout/MainLayout.tsx` | Added Catalog `SubMenu` with Items link; split NAV_ITEMS into NAV_TOP + NAV_BOTTOM | Sidebar navigation for new module |

### Build Result
- TypeScript: zero errors
- Production build: 488.06 kB JS, 24.11 kB CSS

---

## [PRE-ALPHA v0.5.3.2 | 2026-03-02 ~00:00] — Items & Warehouse Plan Review and Corrections

**What changed:** Reviewed `docs/planning_phase/Frontend/02_items_warehouse_modules.plan.md` against the actual backend code (models, schemas, routers) and corrected 9 errors that would have caused implementation failures.

### File Changed

| File | Change | Why |
|------|--------|-----|
| `docs/planning_phase/Frontend/02_items_warehouse_modules.plan.md` | Corrected 9 errors + restructured document | Plan had mismatches with actual backend that would block or break frontend implementation |

### Errors Corrected

| # | Error | Fix |
|---|-------|-----|
| 1 | Search field listed as `sku_name` | Backend searches `item_name` or `master_sku` — corrected |
| 2 | Item update listed as `PUT` | Backend uses `PATCH /api/v1/items/{item_id}` — corrected |
| 3 | Warehouse API paths used flat `/api/v1/inventory/...` | Backend nests under `/api/v1/warehouse/{warehouse_id}/...` — corrected all hooks |
| 4 | Location hierarchy listed "Warehouse → Zone → Aisle → Rack → Bin" | Backend model uses `section` → `zone` → `aisle` → `rack` → `bin` — corrected |
| 5 | `/catalog/attributes` route planned for attribute CRUD | Already implemented at `/settings` (v0.5.3) — removed duplicate route |
| 6 | Backend API Dependencies marked all as "To implement" | Items CRUD + all 5 attribute GETs are already implemented — updated statuses |
| 7 | Movement payload assumed `source_location_id` + `destination_location_id` | Backend uses separate `InventoryTransaction` records with `is_inbound` flag — corrected |
| 8 | Warehouse router activation not mentioned | Router exists but is commented out in `main.py` — added prerequisite note |
| 9 | No edit route for existing items | Added `/catalog/items/:id/edit` route |

---

## [PRE-ALPHA v0.5.3.1 | 2026-02-28 ~00:00] — Database Documentation Cleanup

### Files Changed

#### `docs/official_documentation/database_structure.md`
**What:** Removed "Connection Troubleshooting" section and its table of contents entry.

**Why:** Section was operational notes specific to local dev setup, not schema documentation.
Belongs in README or setup guides — not the canonical DB structure reference.

---

## [PRE-ALPHA v0.5.3 | 2026-02-27 ~00:30] — Settings Page with Item Attributes CRUD

**What changed:** Added a Settings page with full CRUD for 5 item-attribute lookup tables: **Status**, **ItemType**, **Category**, **Brand**, and **BaseUOM**. Each table supports create, inline edit, and delete via a reusable `AttributeCard` component.

### Backend

| File | Change | Why |
|------|--------|-----|
| `backend/app/schemas/items.py` | Added 10 Create/Update Pydantic schemas (2 per table) | Validate POST/PATCH request bodies; Update schemas use `Optional` fields for partial updates |
| `backend/app/routers/items.py` | Added 15 new endpoints: POST/PATCH/DELETE for each of 5 lookup tables | Full write API for item attributes; 201 on create, 409 on duplicate or FK violation, 204 on delete |
| `backend/app/main.py` | Registered `items_router` at `/api/v1/items` | Router existed but was not active — now mounted |

### Frontend

| File | Change | Why |
|------|--------|-----|
| `frontend/src/api/base_types/items.ts` | **New** — `AttributeItem` interface (`{ id, name }`) | Generic type for all 5 lookup tables |
| `frontend/src/api/base/items.ts` | **New** — 20 API functions + 5 normaliser helpers | 4 functions per table (list/create/update/delete); normalisers map backend field names to `{ id, name }` |
| `frontend/src/components/settings/AttributeCard.tsx` | **New** — reusable CRUD card component | Inline add/edit/delete with Enter/Escape keys, error handling, loading spinner |
| `frontend/src/pages/SettingsPage.tsx` | **New** — Settings page with responsive grid of 5 AttributeCards | `Promise.allSettled` loads all 5 tables; `makeHandlers` factory avoids CRUD callback repetition |
| `frontend/src/App.tsx` | Added `/settings` route inside protected group | Route to SettingsPage |
| `frontend/src/components/layout/MainLayout.tsx` | Added Settings nav item with `SettingsIcon` | Sidebar navigation entry |

### Build Result
- TypeScript: zero errors
- Production build: 425.02 kB JS, 16.62 kB CSS

---

## [PRE-ALPHA v0.5.1.6 | 2026-02-26 ~23:30] — Convert layouts/ + components/ to Tailwind CSS, remove MUI theme

**What changed:** Migrated MainLayout, ProtectedRoute, and PageHeader from MUI components to native HTML + Tailwind CSS. Created custom `useIsMobile` hook to replace MUI `useMediaQuery`. Removed MUI `ThemeProvider` and `theme.ts` — all design tokens now live in `index.css` `@theme`. Uninstalled `lucide-react`. MUI icons are retained as the only MUI dependency in use.

### New Files

| File | Purpose |
|------|---------|
| `src/hooks/useIsMobile.ts` | Custom hook using `window.matchMedia` — replaces MUI `useMediaQuery(theme.breakpoints.down('md'))` |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/layouts/MainLayout.tsx` | Replaced MUI Box, AppBar, Toolbar, Typography, IconButton, useMediaQuery, useTheme with native HTML + Tailwind. react-pro-sidebar styles inlined as plain objects using CSS variables. MUI icons (Menu, Dashboard, UploadFile, Storage, Sync) retained. | Tailwind migration — ground rule #10 |
| `src/components/auth/ProtectedRoute.tsx` | Replaced MUI Box + CircularProgress with div + CSS spinner (`animate-spin`) | Tailwind migration |
| `src/components/common/PageHeader.tsx` | Replaced MUI Box + Typography with div/h1/p + Tailwind | Tailwind migration |
| `src/main.tsx` | Removed `ThemeProvider` wrapper and `theme` import. Only `BrowserRouter` + `AuthProvider` + `App` remain. | No MUI components depend on theme anymore |

### Files Deleted

| File | Why |
|------|-----|
| `src/layouts/MainLayout.styles.ts` | Replaced by Tailwind classes + inlined react-pro-sidebar styles |
| `src/components/auth/ProtectedRoute.styles.ts` | Replaced by Tailwind classes |
| `src/components/common/PageHeader.styles.ts` | Replaced by Tailwind classes |
| `src/styles/common.styles.ts` | Shared MUI styles no longer needed (Tailwind utilities used instead) |
| `src/theme/theme.ts` | All design tokens migrated to `index.css` `@theme` block |

### Packages Changed

| Package | Action | Why |
|---------|--------|-----|
| `lucide-react` | Uninstalled | User chose to keep MUI icons instead |

### Remaining MUI Dependencies

`@mui/icons-material`, `@mui/material`, `@emotion/react`, `@emotion/styled` are still installed — `@mui/icons-material` is used in MainLayout.tsx (5 icons) and LoginPage.tsx (3 icons). `@mui/material` + Emotion are peer dependencies of `@mui/icons-material`.

### Build Impact

| Metric | Before (v0.5.1.5) | After | Change |
|--------|--------|-------|--------|
| JS bundle | 466.01 kB | 417.26 kB | **-48.75 kB** (removed MUI layout components + ThemeProvider) |
| CSS output | 14.71 kB | 15.61 kB | +0.90 kB (Tailwind utilities for layouts) |
| Modules | 397 | 379 | -18 modules |

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful (417.26 kB JS, 15.61 kB CSS)
- `npm run dev` — server starts cleanly, no console errors

---

## [PRE-ALPHA v0.5.1.5 | 2026-02-26 ~23:00] — Convert pages/ to Tailwind CSS

**What changed:** Migrated all 6 page components from MUI `sx` / MUI components to native HTML + Tailwind CSS utility classes. Removed MUI component imports (Box, Card, Typography, Button, Alert, Grid) from all pages. Deleted deprecated `.styles.ts` files. Extended `index.css` with login-specific CSS (blob decorations, form input styles).

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/pages/LoginPage.tsx` | Replaced all MUI components (Box, Card, TextField, Button, Typography, Alert, IconButton, InputAdornment, CircularProgress) with native HTML + Tailwind classes. Only MUI icons retained. | Tailwind migration — ground rule #10 |
| `src/pages/NotFoundPage.tsx` | Replaced Box, Typography, Button with div/h1/p/button + Tailwind | Tailwind migration |
| `src/pages/DashboardPage.tsx` | Replaced Box, Card, CardContent, Grid, Typography with div/p + Tailwind grid | Tailwind migration |
| `src/pages/OrderImportPage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/pages/ReferencePage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/pages/MLSyncPage.tsx` | Replaced Box, Alert with div + Tailwind info alert styling | Tailwind migration |
| `src/index.css` | Added login page tokens (`--color-login-bg`, `--color-login-panel`, `--shadow-login`), blob CSS classes (`.login-blob--*`), form input CSS (`.form-input`, `.form-label`, `.form-helper`) | Custom CSS for complex login UI that doesn't fit pure utility classes |

### Files Deleted

| File | Why |
|------|-----|
| `src/pages/LoginPage.styles.ts` | Replaced by Tailwind classes + index.css custom CSS |
| `src/pages/NotFoundPage.styles.ts` | Replaced by Tailwind classes |

### Build Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| JS bundle | 561.80 kB | 466.01 kB | **-95.79 kB** (removed MUI component imports) |
| CSS output | 6.51 kB | 14.71 kB | +8.20 kB (Tailwind utilities + custom CSS) |
| Chunk warning | Yes (>500 kB) | **No** | Under threshold |

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful, no chunk size warnings

---

## [PRE-ALPHA v0.5.1.4 | 2026-02-26 ~22:00] — Add Tailwind CSS v4 as base styling framework

**What changed:** Installed Tailwind CSS v4 with the Vite plugin, created a base CSS template (`src/index.css`) with project design tokens mapped to Tailwind's `@theme`, and added ground rule #10 establishing Tailwind as the styling standard going forward.

### New Files

| File | Purpose |
|------|---------|
| `frontend/src/index.css` | Tailwind v4 base template — imports Tailwind, defines `@theme` with all project colors (primary, secondary, semantic), typography (Montserrat), border radii, and shadows matching `theme.ts` |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/vite.config.ts` | Added `@tailwindcss/vite` plugin | Tailwind v4 uses a Vite plugin (no PostCSS config needed) |
| `frontend/src/main.tsx` | Added `import './index.css'`; removed `CssBaseline` import | Tailwind's preflight replaces MUI's CssBaseline for CSS resets |
| `frontend/package.json` | Added `tailwindcss`, `@tailwindcss/vite` | Tailwind CSS v4 dependencies |

### New Ground Rule

| # | Rule |
|---|------|
| 10 | **Tailwind CSS**: Use Tailwind CSS v4 as base styling framework — all new styling uses Tailwind utility classes; MUI `sx`/`.styles.ts` are deprecated (migration pending) |

### Design Decisions

- **Tailwind CSS v4** (not v3) — CSS-first config via `@theme`, no `tailwind.config.js` needed, native Vite plugin
- **Removed CssBaseline** — Tailwind's preflight handles browser CSS reset
- **Kept ThemeProvider + theme.ts** temporarily — existing MUI components still depend on them; will be removed when components are fully migrated to Tailwind
- **`@theme` tokens match `theme.ts`** — `bg-primary` = `#1565C0`, `text-secondary` = `#555770`, `font-sans` = Montserrat, etc.

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful (6.51 kB CSS output, 561.80 kB JS — slightly smaller than before CssBaseline removal)

---

## [PRE-ALPHA v0.5.1.3 | 2026-02-26 ~21:00] — Extract inline styles to separate files

**What changed:** Extracted all inline MUI `sx` styles from React components into co-located `*.styles.ts` files using typed `SxProps<Theme>` exports. This enforces frontend ground rule #8 (all CSS in separate files).

### New Files Created

| File | Exports | Why |
|------|---------|-----|
| `src/styles/common.styles.ts` | `centeredFullPage`, `centeredContentArea` | Shared layout primitives reused by multiple components |
| `src/pages/LoginPage.styles.ts` | 18 exports (static + factory functions + `blob()` helper) | Largest extraction — decorative blobs, form panels, branding, buttons |
| `src/layouts/MainLayout.styles.ts` | 5 static + 5 factory/function exports | Sidebar, AppBar, page content; includes non-sx react-pro-sidebar props |
| `src/pages/NotFoundPage.styles.ts` | `pageRoot` (re-export), `errorCode`, `errorMessage` | 404 page layout and typography |
| `src/components/auth/ProtectedRoute.styles.ts` | `loadingContainer` (re-export) | Loading spinner container |
| `src/components/common/PageHeader.styles.ts` | `headerContainer` | Page header margin |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `src/pages/LoginPage.tsx` | All 16+ inline `sx` → `import * as styles` | Ground rule #8 compliance |
| `src/layouts/MainLayout.tsx` | All 9+ inline `sx` + react-pro-sidebar props → styles imports | Ground rule #8 compliance |
| `src/pages/NotFoundPage.tsx` | 3 inline `sx` → styles imports | Ground rule #8 compliance |
| `src/components/auth/ProtectedRoute.tsx` | 1 inline `sx` → styles import | Ground rule #8 compliance |
| `src/components/common/PageHeader.tsx` | 1 inline `sx` → styles import | Ground rule #8 compliance |

### Design Decisions

- **SxProps<Theme> style files** (not CSS Modules) — project uses MUI responsive breakpoints, spacing multipliers, and palette references extensively; CSS Modules would require rewriting all of this as raw CSS
- **Factory functions** for dynamic styles (e.g., `mainContent(isMobile, sidebarWidth)`, `emailHelperText(isValid)`) — runtime values require function calls
- **`import type`** for Theme/SxProps — `verbatimModuleSyntax: true` in tsconfig requires it
- **Re-exports from common** — `centeredFullPage` and `centeredContentArea` are shared patterns, imported by ProtectedRoute and NotFoundPage respectively

### Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `npm run build` — successful production build (563 kB bundle, unchanged from before extraction)

---

## [PRE-ALPHA v0.5.1.2 | 2026-02-26 ~20:00] — Frontend ground rules + BrowserRouter

**What changed:** Added 3 new frontend ground rules (component architecture, separate CSS files, BrowserRouter) and switched routing from HashRouter to BrowserRouter.

### New Ground Rules Added

| # | Rule | Why |
|---|------|-----|
| 7 | Dedicated component section (`src/components/`) for reusable functions (e.g., printing) | Establishes convention for shared UI components |
| 8 | All CSS in separate files — no inline or in-component styles | Consistent styling approach, easier maintenance |
| 9 | Use BrowserRouter for routing | Standard SPA routing with clean URLs (no `#/` prefix) |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `frontend/src/main.tsx` | `HashRouter` → `BrowserRouter` | Ground rule #9: clean URL paths |
| `frontend/src/api/client.ts` | 401 redirect: `window.location.hash = '#/login'` → `window.location.href = '/login'` | BrowserRouter uses pathname, not hash |
| `docs/official_documentation/frontend-development-progress.md` | Added "Frontend Ground Rules" section with all 9 rules | Canonical location for frontend conventions |

---

## [PRE-ALPHA v0.5.1.1 | 2026-02-26 ~19:30] — Auth endpoint bugfixes + DB provisioning

**What changed:** Fixed two bugs that prevented the login endpoint from working during end-to-end testing. Also provisioned `woms_user` in PostgreSQL and granted table-level permissions.

### Bugs Fixed

| # | Error | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | `permission denied for table users` | `woms_user` was created as DB owner but had no table-level `GRANT` on tables created by `postgres` | Ran `GRANT ALL ON ALL TABLES/SEQUENCES IN SCHEMA public TO woms_user` + `ALTER DEFAULT PRIVILEGES` |
| 2 | `can't subtract offset-naive and offset-aware datetimes` | `last_login` column is `TIMESTAMP WITHOUT TIME ZONE`; `datetime.now(timezone.utc)` returns tz-aware datetime; asyncpg rejects the mismatch | Added `.replace(tzinfo=None)` in `routers/auth.py` line 49 |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `backend/app/routers/auth.py` | `datetime.now(timezone.utc).replace(tzinfo=None)` | Strip timezone for `TIMESTAMP WITHOUT TIME ZONE` column |
| `fix_db_password.py` (new, temp) | Helper script to sync `.env` password with PostgreSQL | One-time DB provisioning tool |

### Test Results

| Test | Result |
|------|--------|
| `GET /health` | `{"status":"healthy","database":"connected"}` |
| `POST /api/v1/auth/login` (admin@admin.com / Admin123) | 200 — JWT token + user info returned |
| `GET /api/v1/auth/me` (Bearer token) | 200 — user profile returned |
| Vite proxy `/api` -> backend | Working (login via port 5173 succeeds) |
| Frontend dev server (localhost:5173) | Running, serves login page |

---

## [PRE-ALPHA v0.5.2 | 2026-02-26 ~18:00] — Full CRUD API for all domains

**What changed:** Built the complete REST API layer covering all 6 domains with 50+ endpoints. Includes Pydantic schemas (Create/Read/Update per entity), paginated list endpoints with search/filter, JWT-protected write operations, and a standard response envelope (`PaginatedResponse`, `ErrorResponse`). Also simplified Alembic migration naming by dropping the revision hash and seconds from filenames.

### New Files Created

| File | Purpose |
|------|---------|
| `backend/app/schemas/common.py` | `PaginatedResponse[T]`, `ErrorResponse`, `MessageResponse` |
| `backend/app/schemas/items.py` | ItemCreate, ItemRead, ItemUpdate + lookup reads |
| `backend/app/schemas/orders.py` | OrderCreate, OrderRead, OrderUpdate, OrderDetailCreate/Read/Update, OrderListItem |
| `backend/app/schemas/platform.py` | PlatformCreate/Read/Update, SellerCreate/Read/Update |
| `backend/app/schemas/warehouse.py` | WarehouseCreate/Read/Update, InventoryLevelRead, InventoryAlertRead |
| `backend/app/schemas/delivery.py` | DeliveryTripCreate/Read/Update, DriverCreate/Read/Update |
| `backend/app/schemas/users.py` | UserCreate/Read/Update, RoleRead |
| `backend/app/routers/items.py` | Items CRUD + lookup endpoints (statuses, types, categories, brands, UOMs) |
| `backend/app/routers/orders.py` | Order CRUD + order detail updates |
| `backend/app/routers/platforms.py` | Platform + Seller CRUD |
| `backend/app/routers/warehouse.py` | Warehouse CRUD, locations, inventory levels, alerts |
| `backend/app/routers/delivery.py` | Delivery trips + drivers CRUD |
| `backend/app/routers/users.py` | User CRUD + roles listing |

### Files Modified

| File | Change | Why |
|------|--------|-----|
| `backend/app/main.py` | Mounted 6 new routers, removed future-routers comment block | Activate all CRUD endpoints |
| `backend/app/schemas/__init__.py` | Re-export all new schema classes | Centralized schema imports |
| `backend/alembic.ini` | Simplified `file_template` (dropped `%%(second)` and `%%(rev)s`) | Cleaner migration filenames |

### Endpoint Summary (50+ routes)

| Domain | Endpoints | Auth Required |
|--------|-----------|---------------|
| Auth | POST /login, GET /me | Login: no, Me: yes |
| Orders | GET list, GET/:id, POST, PATCH/:id, PATCH/:id/details/:id | Write: yes |
| Order Import | POST /import | No |
| Items | GET list, GET/:id, POST, PATCH/:id, DELETE/:id + 5 lookup GETs | Write: yes |
| Platforms | GET list, GET/:id, POST, PATCH/:id | Write: yes |
| Sellers | GET list, GET/:id, POST, PATCH/:id | Write: yes |
| Warehouse | GET list, GET/:id, POST, PATCH/:id, locations, inventory, alerts | Write: yes |
| Delivery | Drivers: GET/POST/PATCH, Trips: GET/POST/PATCH | Write: yes |
| Users | GET list, GET/:id, POST, PATCH/:id, GET /roles | All: yes |
| Reference | POST load-platforms/sellers/items | No |
| ML Staging | POST sync, POST init-schema | No |

---

## [PRE-ALPHA v0.5.1 | 2026-02-26 ~12:00] — Login Page + JWT Authentication

**What changed:** Added full authentication flow: backend JWT login endpoint with bcrypt password hashing, frontend login page with dark-themed UI matching project design system, auth context with token persistence, and protected routes. Seeded a test admin user (`admin@admin.com` / `Admin123`).

### Backend Changes

| File | Change | Why |
|---|---|---|
| `backend/app/schemas/auth.py` (new) | `LoginRequest`, `TokenResponse`, `TokenPayload` Pydantic schemas | Type-safe request/response validation for auth endpoints |
| `backend/app/services/auth.py` (new) | `hash_password()`, `verify_password()`, `create_access_token()`, `decode_access_token()`, `authenticate_user()`, `get_current_user()` | Auth business logic using passlib[bcrypt] + python-jose; separated from router |
| `backend/app/dependencies/__init__.py` (new) | Package init for FastAPI dependencies | Organise dependency injection functions |
| `backend/app/dependencies/auth.py` (new) | `OAuth2PasswordBearer` scheme + `require_current_user()` dependency | JWT extraction from Bearer header; reusable for all protected endpoints |
| `backend/app/routers/auth.py` (new) | `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | Login endpoint returns JWT; /me validates token and returns user profile |
| `backend/app/main.py` | Registered auth router at `/api/v1/auth` | Expose auth endpoints via FastAPI |
| `backend/app/models/seed.py` | Added test admin user insert (`ON CONFLICT DO NOTHING`) | Test user for development; uses subquery for role_id resolution |
| `backend/app/schemas/__init__.py` | Added auth schema imports | Package-level export |

### Frontend Changes

| File | Change | Why |
|---|---|---|
| `frontend/src/types/auth.ts` (new) | `LoginRequest`, `LoginResponse`, `AuthUser` interfaces | TypeScript types matching backend auth contract |
| `frontend/src/api/auth.ts` (new) | `login()`, `getMe()` API functions | Frontend-to-backend auth API calls |
| `frontend/src/contexts/AuthContext.tsx` (new) | `AuthProvider` + `useAuth()` hook | Global auth state: token in localStorage, /me validation on mount, login/logout |
| `frontend/src/components/auth/ProtectedRoute.tsx` (new) | Route guard component | Redirects to /login if unauthenticated; shows spinner while validating |
| `frontend/src/pages/LoginPage.tsx` (new) | Full login page UI | Dark background, decorative blobs panel, email/password form, error handling |
| `frontend/src/api/client.ts` | Activated Bearer token injection; added 401 redirect handler | Token auto-injected on every request; expired tokens trigger login redirect |
| `frontend/src/main.tsx` | Wrapped App in `<AuthProvider>` | Auth context available to all components |
| `frontend/src/App.tsx` | `/login` route outside MainLayout; all others wrapped in `<ProtectedRoute>` | Login page has no sidebar; dashboard requires authentication |

### New Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Public | Authenticate with email + password, receive JWT |
| GET | `/api/v1/auth/me` | Bearer JWT | Get current user profile (token validation) |

### Test User

| Field | Value |
|---|---|
| Email | `admin@admin.com` |
| Password | `Admin123` |
| Username | `admin` |
| Role | Admin |

---

## [PRE-ALPHA v0.4.5 | 2026-02-25 ~16:00] — API Development Proposal revised (10 review findings)

**What changed:** The API Development Proposal (`docs/planning_phase/Backend/06_api_development_proposal_106ea193.plan.md`) was reviewed against the actual codebase and rewritten with 10 improvements.

### Changes Made

| # | Finding | Change |
|---|---------|--------|
| 1 | Nested `/catalog/`, `/marketplace/` paths | Replaced with flat paths matching `main.py:207-211` stubs |
| 2 | Missing authentication | Added new Section 3 covering `app/auth/` package, JWT, login/register/refresh endpoints |
| 3 | Separate `seller.py` for one model | Merged Seller into `platform.py` with other marketplace models |
| 4 | Deeply nested `schemas/` directory | Flattened to mirror model files |
| 5 | `PlatformRawImport` incorrectly marked as "legacy/deprecate" | Corrected: both tables serve distinct roles; `Order.raw_import_id` FK depends on it |
| 6 | Migration naming lacked implementation detail | Added actual `alembic.ini` `file_template` change |
| 7 | `warehouse.py` not discussed | Acknowledged as future split candidate (483 lines, 11 models) |
| 8 | Circular import risk in model split | Added `TYPE_CHECKING` + string FK refs resolution pattern |
| 9 | Existing `ImportResult`/`SyncResult` dataclasses not mentioned | Documented with conversion plan to Pydantic |
| 10 | No error response standardization | Added `ErrorResponse`/`PaginatedResponse` in `common.py` |

Phases reordered from 4 to 6: docs → schemas → **auth** → order CRUD → supporting CRUDs → model split.

---

## [PRE-ALPHA v0.5.0 | 2026-02-25 ~15:00] — Frontend Project Scaffold (React + Vite + TypeScript + MUI)

**What changed:** Created the `frontend/` directory with a complete React + Vite + TypeScript project scaffold. Includes Material UI theming (Montserrat font, custom palette, button/checkbox/alert overrides), react-pro-sidebar navigation, HashRouter for Electron compatibility, Axios API client layer matching all backend endpoints, TypeScript interfaces for JSONB columns, D3 integration hook, and placeholder pages for all features. Also created three new documentation files for frontend development tracking.

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `frontend/` (new) | Complete Vite + React + TS scaffold with 25+ source files | Monorepo frontend sibling to `backend/`; prepared since v0.4.0 |
| `frontend/vite.config.ts` | Dev proxy `/api` → `localhost:8000`; base `./` | Proxy avoids CORS issues; relative base enables Electron file:// |
| `frontend/index.html` | Montserrat font CDN link, updated title | User-specified font; descriptive page title |
| `frontend/src/theme/theme.ts` | MUI theme: Montserrat, primary (#1565C0), secondary (#FF8F00), component overrides | Light-mode theme with scalable ThemeProvider for future dark mode |
| `frontend/src/main.tsx` | StrictMode + ThemeProvider + CssBaseline + HashRouter | HashRouter for Electron compat; theme consistency |
| `frontend/src/App.tsx` | 5 routes: /, /orders/import, /reference, /ml, 404 | Maps all backend features to frontend pages |
| `frontend/src/layouts/MainLayout.tsx` | react-pro-sidebar, responsive AppBar, Outlet | Collapsible sidebar with Material Icons, mobile breakpoints |
| `frontend/src/api/*.ts` | Axios client + 4 API modules matching backend contracts | Type-safe API calls with centralised error handling |
| `frontend/src/types/*.ts` | TypeScript interfaces for orders, reference, mlSync, JSONB | Type safety for all backend interactions |
| `frontend/src/services/dataService.ts` | Multi-DB toggle service (woms_db / ml_woms_db) | Forward-looking abstraction for DB context switching |
| `frontend/src/hooks/useD3.ts` | D3 + useRef integration hook | Prevents D3/React virtual DOM conflicts |
| `frontend/src/components/common/PageHeader.tsx` | Reusable page header | Consistent heading style across pages |
| `frontend/src/pages/*.tsx` | 5 placeholder pages | Skeleton pages ready for feature implementation |
| `docs/official_documentation/frontend-development-progress.md` (new) | Frontend progress tracking document | User ground rule #1: document all updates |
| `docs/official_documentation/web-api.md` (new) | Full API documentation for all 9 endpoints | User ground rule #2: document all APIs |
| `docs/official_documentation/frontend-error.md` (new) | Error tracking log template | User ground rule #6: document all errors |
| `README.md` | Added Frontend section, updated project layout tree | Reflect new frontend directory |

### Tech Stack

| Layer | Choice | Version |
|---|---|---|
| Framework | React + TypeScript (Strict) | 19.x |
| Build tool | Vite | 6.x |
| UI Library | @mui/material + @emotion | 6.x |
| Routing | react-router-dom (HashRouter) | 7.x |
| Sidebar | react-pro-sidebar | 1.x |
| HTTP client | axios | 1.x |
| Charts | d3 (useRef pattern) | 7.x |
| Mock data | @faker-js/faker | 9.x |

---

## [PRE-ALPHA v0.4.4 | 2026-02-23 ~23:30] — Move docs/ to project root, commit planning_phase

**What changed:** The `docs/` folder was moved from `backend/docs/` to the project root so it is visible to anyone browsing the repository without navigating into `backend/`. The `planning_phase/` subfolder was removed from `.gitignore` and all 5 design-notes files are now committed alongside the official documentation.

### Changes Made

| File | Change | Why |
|---|---|---|
| `backend/docs/` → `docs/` | Entire docs folder moved to project root | Better discoverability — docs are now visible at repo root without entering backend/ |
| `.gitignore` | Removed `backend/docs/planning_phase/` and `docs/planning_phase/` exclusion lines | Planning docs should be versioned alongside official docs for full project history |
| `docs/planning_phase/` (5 files) | Added to git and committed for the first time | Design notes are part of the project record and useful for contributors |
| `README.md` | Updated 2 doc links from `backend/docs/...` → `docs/...`; updated project layout tree | Links were pointing to old path after folder move |

---

## [PRE-ALPHA v0.4.3 | 2026-02-23 ~23:00] — README overhaul + remove planning_phase from git

**What changed:** README.md was completely rewritten to reflect the current project state (backend/ layout, actual endpoints, setup_env.py workflow). The `planning_phase/` docs folder was removed from git tracking (files remain on disk but are gitignored).

### Changes Made

| File | Change | Why |
|---|---|---|
| `README.md` | Rewritten: accurate project layout, actual API endpoints, setup_env.py instructions, correct env vars table, links to official docs | Old README was from v0.1.0; referenced non-existent files and commands |
| `.gitignore` | Added `backend/docs/planning_phase/` and `docs/planning_phase/` patterns | Internal design notes should not be published to GitHub |
| `backend/docs/planning_phase/` (5 files) | Removed from git index (`git rm --cached`) — files stay on disk | Planning docs are internal; not relevant to users cloning the repo |

---

## [PRE-ALPHA v0.4.2 | 2026-02-23 ~22:30] — setup_env.py: Auto-generate .env + provision PostgreSQL

**What changed:** Added `setup_env.py` at the project root — a one-command tool that generates all secrets and DB credentials, creates the PostgreSQL user and both databases, then writes a complete `.env` with no placeholder values.

### Changes Made

| File | Change | Why |
|---|---|---|
| `setup_env.py` (new) | Auto-generates `SECRET_KEY` (256-bit hex), DB password (`token_urlsafe`), creates `woms_user` + `woms_db` + `ml_woms_db` in PostgreSQL, writes complete `.env` | Eliminates manual credential setup; every install gets unique secure keys |

### How it works
- `SECRET_KEY` — `secrets.token_hex(32)` → 64-char hex, 256 bits of entropy
- `DATABASE_PASSWORD` — `secrets.token_urlsafe(32)` → URL-safe (A-Z a-z 0-9 `-` `_`), safe in connection URLs without percent-encoding
- Connects to PostgreSQL as admin user (`postgres` by default) using `psycopg3`
- Uses parameterised queries for password to prevent injection
- Idempotent: if user/DB already exists, updates password/owner instead of failing
- Admin credentials are asked interactively (`getpass`) — **never stored**
- Falls back gracefully: prints SQL commands if `psycopg` unavailable or connection fails

### Usage
```bash
python setup_env.py                  # Interactive: generate + provision DB
python setup_env.py --generate-only  # Just write .env (no DB creation)
python setup_env.py --force          # Overwrite existing .env without prompt
```

---

## [PRE-ALPHA v0.4.1 | 2026-02-23 ~22:00] — requirements.txt Sync to Actual Installed Versions

**What changed:** `requirements.txt` was outdated — it listed package versions from the initial project setup, two missing packages (`pandas`, `python-dateutil`), and one wrong package name (`psycopg-binary` vs `psycopg[binary,pool]`). The file now reflects exact versions from the active Python 3.13 environment.

**Root cause discovered:** The project runs on Python 3.13 (system install at `AppData/Local/Programs/Python/Python313/`). The `venv/` directory is not a standard virtual environment (no `pyvenv.cfg`) — it only holds compiled `.pyd` extension stubs. All packages are installed in the system Python 3.13.

### Changes Made

| File | Change | Why |
|---|---|---|
| `backend/requirements.txt` | Updated all package versions to match Python 3.13 actual installs | Old versions were from initial setup; project has been running on newer versions |
| `backend/requirements.txt` | Added `pandas==3.0.1` | Was missing — used throughout order import pipeline for CSV/Excel parsing |
| `backend/requirements.txt` | Added `python-dateutil==2.9.0.post0` | Was missing — used in `cleaner.py` `parse_flexible_date()` for date normalization |
| Python 3.13 | Installed `pandas==3.0.1`, `python-dateutil==2.9.0.post0` | Both were absent from the active Python environment |

### Key Version Changes
| Package | Old | New |
|---|---|---|
| `fastapi` | 0.109.2 | 0.111.0 |
| `uvicorn` | 0.27.1 | 0.30.1 |
| `sqlmodel` | 0.0.14 | 0.0.31 |
| `sqlalchemy` | 2.0.25 | 2.0.34 |
| `pydantic-settings` | 2.1.0 | 2.11.0 |
| `asyncpg` | 0.29.0 | 0.31.0 |
| `bcrypt` | 4.1.2 | 5.0.0 |
| `pandas` | missing | 3.0.1 |
| `python-dateutil` | missing | 2.9.0.post0 |

---

## [PRE-ALPHA v0.4.0 | 2026-02-23 ~21:30] — Project Restructuring: `backend/` layout + `venv` → `.venv`

**What changed:** All application code was relocated from the project root into a `backend/` subfolder, adopting a monorepo-style layout that makes room for a future `frontend/` sibling. The deprecated SQL `migrations/` folder was co-located inside `app/`. The virtual environment was renamed from `venv/` to `.venv/` (convention standard, already in `.gitignore`).

### Changes Made

| File / Folder | Change | Why |
|---|---|---|
| `alembic/` | Moved to `backend/alembic/` | All backend code lives in `backend/` |
| `alembic.ini` | Moved to `backend/alembic.ini` | `script_location = alembic` stays relative — run alembic from `backend/` |
| `app/` | Moved to `backend/app/` | Monorepo layout for future frontend sibling |
| `docs/` | Moved to `backend/docs/` | Documentation co-located with application |
| `migrations/` (root) | Moved to `backend/app/migrations/` | Deprecated SQL reference files co-located with app |
| `requirements.txt` | Moved to `backend/requirements.txt` | Dependency manifest with the application code |
| `tests/` | Moved to `backend/tests/` | Test data/fixtures with the application code |
| `venv/` | Renamed to `.venv/` at project root | Convention standard; stays at root (not inside backend/) |
| `backend/app/config.py` | `env_file=".env"` → absolute path via `Path(__file__).parent.parent.parent / ".env"` | `.env` stays at project root; absolute path ensures it loads regardless of CWD |
| `backend/app/database.py` | `PROJECT_ROOT` path updated (`.parent.parent` → `.parent.parent.parent`); comment updated | Reflects new depth of file in `backend/app/` |
| `.claude/settings.local.json` | All `venv/` references → `.venv/` | Match new virtual environment folder name |

### Files NOT Moved (remain at project root)
`.env`, `.env.template`, `.gitignore`, `README.md`, `setup.py`

### How to Run After Restructuring
```bash
# Start server (from project root):
cd backend
../.venv/Scripts/uvicorn app.main:app --reload

# Run Alembic (from backend/):
cd backend
../.venv/Scripts/alembic upgrade head
```

### Verification
- Server started from `backend/` with `DEBUG=false venv/Scripts/uvicorn app.main:app`
- `GET /api/v1/health` → `{"status": "healthy"}` ✓
- Swagger UI at `http://localhost:8000/docs` ✓
- `.env` loaded correctly (DB settings resolved from project root) ✓

---

## [PRE-ALPHA v0.3.5 | 2026-02-23 ~19:00] — Documentation Restructuring

**What changed:** Project documentation files were renamed and consolidated into a single canonical directory. New ground rule established for where documentation lives.

### Changes Made

| File | Change | Why |
|---|---|---|
| `docs/database.md` | Renamed/moved to `docs/official_documentation/database_structure.md` | Descriptive filename better communicates purpose; consolidated into the official docs folder |
| `version_update.md` (project root) | Moved to `docs/official_documentation/version_update.md` (this file) | Single canonical location for all official project documentation |

### New Ground Rule
- **Canonical documentation directory:** `docs/official_documentation/`
- **Database schema docs:** always update `docs/official_documentation/database_structure.md` (previously `database.md`)
- **Version update log:** always update `docs/official_documentation/version_update.md` (this file)

---

## [PRE-ALPHA v0.3.4 | 2026-02-23 ~18:00] — Item Master Upload Correction + SKU Mapping Plan

**What changed:** The `load_item_master` endpoint was uploading platform SKU codes with a hard-coded `seller_id`, which is architecturally wrong. Different sellers across multiple platforms have different platform-specific SKU names for the same product. The mapping from platform SKU → Internal SKU is a manual per-seller decision.

### Changes Made

| File | Change | Why |
|---|---|---|
| `app/services/reference_loader/loader.py` | Removed all `platform_sku` and `listing_component` creation from `load_item_master()`. Now only inserts/updates `items` rows. Removed `seller_id` parameter. | Platform SKU codes in the Item Master file are generic product codes, not seller-specific. Forcing a single seller_id creates false associations. |
| `app/routers/reference.py` | Removed `seller_id: int = Form(...)` from `upload_items` endpoint. Removed `Form` import. | `load_item_master` no longer needs seller context. |

### Data Reset Applied
- Cleared `items`, `platform_sku`, `listing_component` in both `woms_db` and `woms_test_db`
- Re-uploaded items correctly (items table only, 0 platform_sku records)
- Order staging data (`order_import_staging`, `order_import_raw`) was preserved — it serves as the reference for manual SKU mapping

### Final State
```
woms_db:       items=499  platform_sku=0  staging=517 rows
woms_test_db:  items=499  platform_sku=0  staging=517 rows
```

### Platform SKU Mapping — Plan for Future Orders

The `platform_sku` table will be populated manually by the user, per seller, by referencing:
1. **Order staging data** — `platform_sku` column contains the platform's SKU string for each order line
2. **Item Master** — `Internal CODE` is the canonical ID to map to

Mapping workflow (future):
1. User reviews `order_import_staging` rows (e.g. Shopee platform_sku = `"(10 inch) 5'"`)
2. User identifies the matching `items.master_sku` (e.g. `ADM10001`)
3. User creates a `platform_sku` record: `{platform_id, seller_id, platform_sku="(10 inch) 5'", → item}`
4. A `listing_component` record links `platform_sku.listing_id → items.item_id`
5. Once mapped, future imports can auto-resolve platform SKU → internal item

A future admin endpoint `POST /api/v1/reference/map-sku` will be built to accept these mappings.

---

## [PRE-ALPHA v0.3.3 | 2026-02-23 ~17:30] — woms_test_db Clean-Install Test + 2 Bug Fixes

**What changed:** Full clean-install test on a fresh `woms_test_db` PostgreSQL database (separate from `woms_db`). Uncovered and fixed 2 new bugs.

### Bugs Fixed

| File | Bug | Fix |
|---|---|---|
| `app/database.py` → `init_db()` | `create_all()` fails on a fresh database with `InvalidSchemaNameError: schema "order_import" does not exist` — the `order_import` schema must be created before any tables that use it | Added `CREATE SCHEMA IF NOT EXISTS order_import` inside `init_db()` before `create_all()` (mirrors the fix already present in `init_ml_db()`) |
| `app/services/order_import/cleaner.py` → `_DATE_FORMATS` | Shopee dates (`23/12/2025 20:52`) and Lazada dates (`1/1/2025 15:35`) use `DD/MM/YYYY HH:MM` format (no seconds). The format list only had `%d/%m/%Y %H:%M:%S` (with seconds) and `%d/%m/%Y` (date only), so all Shopee/Lazada `order_date` fields were stored as `NULL` | Added `"%d/%m/%Y %H:%M"` to `_DATE_FORMATS` between the with-seconds and date-only variants |

### Why each fix was needed
- **init_db schema**: SQLModel `create_all()` iterates tables alphabetically; `order_import.*` tables come before the schema exists. The `init_ml_db()` function already had this fix — it was just missing from the production `init_db()`.
- **Date format HH:MM vs HH:MM:SS**: Shopee and Lazada export timestamps without seconds. Python's `strptime` does not allow partial pattern matches — `%H:%M:%S` won't match `20:52` because seconds are absent.

### Test Results on woms_test_db (2026-02-23)

```
DB: woms_test_db (fresh PostgreSQL database, clean install)
Server: port 8001, DATABASE_URL override via env var

POST /api/v1/reference/load-platforms  -> 4 platforms loaded
POST /api/v1/reference/load-sellers    -> 8 sellers loaded
POST /api/v1/reference/load-items      -> 499 items, 1497 platform SKUs

POST /api/v1/orders/import [shopee]    -> 116/116 success
POST /api/v1/orders/import [lazada]    -> 120/120 success
POST /api/v1/orders/import [tiktok]    -> 281/281 success

Staging coverage after fix:
  Platform    Rows  w/ Date  w/ Phone  w/ Tracking
  lazada       120      120       120          120   (100% all fields)
  shopee       116      115       115          115   (1 row has empty date/phone in source)
  tiktok       281      278       281          279   (3 rows missing date, 2 missing tracking in source)
  TOTAL        517
```

---

## [PRE-ALPHA v0.3.2 | 2026-02-23 ~17:00] — Alembic Stamp to Head

**What changed:** After the v0.3.1 end-to-end test, the Alembic version tracker in `woms_db` was at `c4d5e6f7a8b9` even though two newer migrations existed in `alembic/versions/`:
- `d5e6f7a8b9c0` — adds `phone_number` and `platform_order_status` to `order_import_staging`
- `e6f7a8b9c0d1` — adds all 47 performance indexes

Both migrations' effects were already present in the DB (columns added via `ALTER TABLE` in v0.3.1; indexes applied by SQLModel `__table_args__` via `create_all()`). Re-running the migrations would have failed with "column already exists" / "index already exists" errors.

**Fix:** Ran `alembic stamp e6f7a8b9c0d1` to advance the version pointer to head without re-executing the DDL. Confirmed with `alembic current` → `e6f7a8b9c0d1 (head)`.

**Why this approach:** `alembic stamp` is the correct tool when the DB state already matches the migration's DDL but the version table is behind — it records the migration as applied without running it.

---

## [PRE-ALPHA v0.3.1 | 2026-02-23 16:30] — End-to-End Test + Bug Fixes

**What changed:** First full end-to-end test run against the test database. Found and fixed 5 bugs uncovered during testing.

### Bugs Fixed

| File | Bug | Fix |
|---|---|---|
| `app/database.py`, `app/main.py`, `app/models/triggers.py`, `app/models/views.py`, `app/models/seed.py`, `app/ml_database.py` | Unicode characters (✓ ⚠) in print() caused `UnicodeEncodeError` on Windows cp1252 console | Replaced all emoji/special chars with ASCII `[OK]` / `[WARN]` |
| `app/services/order_import/parser.py` | CSV files encoded in cp1252 (not UTF-8), causing `UnicodeDecodeError` on Shopee/Lazada/TikTok CSVs | `_read_dataframe()` now tries encodings in order: `utf-8-sig` → `cp1252` → `latin-1` |
| `app/services/order_import/importer.py` | Raw and staging inserts used `:param::jsonb` SQLAlchemy named-param + Postgres cast syntax; asyncpg rejects this combo | Changed to `CAST(:param AS jsonb)` standard SQL syntax |
| `app/models/order_import.py` / DB migration | `phone_number` and `platform_order_status` columns exist in SQLModel but were missing from the live DB (old Alembic migration predated them) | Applied `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` to both `woms_db` and `ml_woms_db` |
| `app/services/order_import/parser.py` | Shopee CSV has an unnamed phone-number column inserted after "Receiver Name", shifting Province/City/Country/Zip Code labels right by 1 position | `parse_shopee_file()` now detects the unnamed column and renames all shifted columns by position index (no duplicate column names created) |

### Why each fix was needed
- **Unicode print**: Windows cmd/uvicorn terminal uses cp1252 by default; Python 3.12 raises on any unencodable char in print()
- **CSV encoding**: The test data CSVs were saved with Windows encoding (cp1252) — they contain characters like ° or Malaysian text that UTF-8 can't decode
- **CAST vs ::jsonb**: SQLAlchemy's text() binds named params (`:name`) then converts to `$N` positional; the `::` Postgres cast operator immediately after `:name` breaks the tokenizer
- **Missing columns**: The Alembic migration `e6f7a8b9c0d1` was created from an older version of the model that didn't yet have `phone_number`/`platform_order_status`; `init_db()` at startup only creates tables that don't exist yet, so columns added to the model after table creation are never added to the live DB automatically
- **Shopee column shift**: Shopee's CSV exporter inserts the phone number column without a header between "Receiver Name" and "Phone Number", pushing all subsequent column labels one position to the right. The delivery address data ends up under the "Phone Number" label, geo columns end up mismatched, etc.

### Test Results (2026-02-23)

```
POST /api/v1/reference/load-platforms  → 4 platforms (test data subset)
POST /api/v1/reference/load-sellers    → 8 sellers
POST /api/v1/reference/load-items      → 499 items, 1497 platform SKUs

POST /api/v1/orders/import [shopee]    → 116/116 success
POST /api/v1/orders/import [lazada]    → 120/120 success
POST /api/v1/orders/import [tiktok]    → 281/281 success

POST /api/v1/ml/sync                   → 505 synced, 12 skipped (duplicate keys in lazada data)

woms_db staging breakdown:
  shopee:  116 rows
  lazada:  120 rows
  tiktok:  281 rows
  total:   517 rows

ml_woms_db staging breakdown:
  shopee:  116 rows
  lazada:  108 rows  (12 duplicate keys skipped)
  tiktok:  281 rows
  total:   505 rows
```

### Remaining Known Issue
- ~~`phone_number` and `platform_order_status` missing-column fix was applied as a direct `ALTER TABLE` to the live DB.~~ **Resolved in v0.3.2**: Alembic stamped to `e6f7a8b9c0d1 (head)` — migration `d5e6f7a8b9c0` in `alembic/versions/` already covers these columns; fresh environments will pick them up via `alembic upgrade head`.

---

## [PRE-ALPHA v0.3.0 | 2026-02-21 ~12:00] — Multi-Platform ETL Pipeline + ML Staging DB

### Context
Extended the import pipeline to support three platforms (Shopee, Lazada, TikTok),
CSV file format in addition to Excel, a reference data loading service for platforms/
sellers/items, a separate ML staging database (`ml_woms_db`), and a sync endpoint
that promotes cleaned staging records from `woms_db` → `ml_woms_db`.

---

### Files Changed

#### `app/services/order_import/parser.py`
**What:** Full rewrite.
- Added `_read_dataframe(file_bytes, filename)` helper — dispatches on `.csv` vs `.xlsx/.xls`
  using `pd.read_csv(..., keep_default_na=False, encoding="utf-8-sig")` for CSV and
  `pd.read_excel()` for Excel.
- Updated `_df_to_records()` to handle both NaN (Excel empty cells) and `""` (CSV empty cells).
- Renamed `parse_shopee_excel` → `parse_shopee_file(file_bytes, filename)`.
- Renamed `parse_lazada_excel` → `parse_lazada_file(file_bytes, filename)`.
- Added `parse_tiktok_file(file_bytes, filename)` — fixes corrupted column header
  `"Tracking ID577729206730130897"` by renaming any column starting with `"Tracking ID"` → `"Tracking ID"`.

**Why:** All three test data files are CSV, not Excel. The original parsers used
`pd.read_excel()` only, so CSV files would have failed silently. The filename-based
dispatch avoids breaking existing Excel workflows.

---

#### `app/services/order_import/cleaner.py`
**What:**
- Added `"%d/%m/%Y %H:%M:%S"` to `_DATE_FORMATS` (TikTok uses DD/MM/YYYY HH:MM:SS).
- Added `clean_tiktok_row()` — cleans all TikTok-specific fields: string fields including
  "Phone #", all timestamp columns (Created Time, Paid Time, RTS Time, etc.),
  decimal fields (Order Amount, SKU Unit Original Price, etc.), Quantity as int.

**Why:** TikTok has a distinct timestamp format and a non-standard phone column name.
Without the new format, all TikTok dates would return None from `parse_flexible_date()`.

---

#### `app/services/order_import/mapper.py`
**What:**
- Added `TIKTOK_FIELD_MAP` (23 staging columns mapped to TikTok CSV column names).
- Registered `"tiktok": TIKTOK_FIELD_MAP` in `_PLATFORM_MAPS`.
- Updated error message in `map_to_staging()` to include tiktok.

**Why:** The mapper is the single source of truth for per-platform column name
translations. Adding TikTok here keeps all platform-specific logic in one place.

---

#### `app/services/order_import/importer.py`
**What:**
- Updated imports: `parse_shopee_file`, `parse_lazada_file`, `parse_tiktok_file`,
  `clean_tiktok_row`.
- Added `"tiktok"` to `_PARSERS` and `_CLEANERS`.
- Changed `parser(file_bytes)` → `parser(file_bytes, filename)` so parsers can
  dispatch on file extension.
- Updated docstring and error message.

**Why:** The orchestrator must pass the filename to parsers so they know whether
to use `pd.read_csv()` or `pd.read_excel()`.

---

#### `app/routers/order_import.py`
**What:**
- Added `"tiktok"` to `_SUPPORTED_PLATFORMS`.
- Extended file extension check to allow `.csv` in addition to `.xlsx/.xls`.
- Updated endpoint descriptions.

**Why:** The API must accept TikTok CSV files and validate platform names correctly.

---

#### `app/services/reference_loader/__init__.py` *(new)*
**What:** Package init — exports `load_platforms`, `load_sellers`, `load_item_master`.

**Why:** Clean public API so the router only imports from the package.

---

#### `app/services/reference_loader/loader.py` *(new)*
**What:** Three async loader functions for seeding reference tables from upload files.
- `load_platforms(session, file_bytes, filename)` — reads `test platform.xlsx` columns
  (Platform_ID, Platform_Name, Address, Postcode); upserts into `platform` table by
  `platform_name` (SELECT-then-update/insert pattern).
- `load_sellers(session, sellers_bytes, sellers_filename, platforms_bytes=None, platforms_filename=None)` —
  reads `test_sellers.xlsx`; resolves Platform_ID codes (MYONL1→Lazada) via an optional
  platform file cross-reference + DB lookup; upserts sellers by `platform_store_id`.
- `load_item_master(session, file_bytes, filename, seller_id)` — reads multi-sheet Excel
  with `header=3` (headers on row 4); filters blank rows by checking `Internal CODE (Main code)`;
  upserts `items` (by `master_sku`), `platform_sku` (by `platform_id/seller_id/platform_sku`),
  and `listing_component` (by `listing_id/item_id`). Creates `BaseUOM` records on demand.

**Why:** Reference data must be loaded once per environment before order imports so
`platform_id`, `seller_id`, and item lookups resolve correctly. The SELECT-then-upsert
pattern avoids needing DB-level unique constraints beyond those already on the models.

---

#### `app/routers/reference.py` *(new)*
**What:** Three `POST` endpoints:
- `POST /api/v1/reference/load-platforms` — accepts single upload file
- `POST /api/v1/reference/load-sellers` — accepts `sellers_file` + optional `platforms_file`
- `POST /api/v1/reference/load-items` — accepts upload file + `seller_id` form field

**Why:** Exposes the reference loaders as REST endpoints for admin upload tooling.
All three are idempotent (safe to re-run).

---

#### `app/config.py`
**What:** Added ML database config fields: `ml_database_host`, `ml_database_port`,
`ml_database_name`, `ml_database_user`, `ml_database_password`, `ml_database_url`
(optional override). Added `async_ml_database_url` property.

**Why:** The ML database URL must be configurable via env vars (`.env` or shell)
without hardcoding credentials.

---

#### `app/ml_database.py` *(new)*
**What:** Separate SQLAlchemy async engine (`ml_engine`) and session factory
(`ml_session_maker`) for `ml_woms_db`. Provides:
- `get_ml_session()` — FastAPI dependency (mirrors `get_session()` from database.py)
- `init_ml_db()` — creates `order_import` schema + all SQLModel tables in `ml_woms_db`
- `check_ml_db_connection()` — health check

**Why:** ML workloads must be completely isolated from the production `woms_db`.
A separate engine with the same SQLModel metadata means both DBs stay in schema sync
without duplicating model definitions.

---

#### `app/services/ml_sync/__init__.py` *(new)*
**What:** Package init — exports `sync_staging_to_ml`, `SyncResult`.

---

#### `app/services/ml_sync/sync.py` *(new)*
**What:** `sync_staging_to_ml(woms_session, ml_session, platform_source=None, seller_id=None)`.
- Reads `order_import_staging` rows from woms_db (with optional platform/seller filters).
- Builds an in-memory set of already-synced keys from ml_woms_db for dedup.
- For each new row: copies the referenced platform + seller to ml_woms_db (satisfies FK
  constraints), then inserts the staging row (with `raw_import_id=None` since raw imports
  are not synced).
- Upsert key: `(platform_source, platform_order_id, platform_sku, seller_id)`.
- Returns `SyncResult` with `staging_synced`, `staging_skipped`, `platforms_synced`,
  `sellers_synced`, and per-row errors.

**Why:** ML models need a clean, isolated copy of processed staging data. Copying
platforms/sellers automatically avoids FK constraint failures in ml_woms_db.

---

#### `app/routers/ml_sync.py` *(new)*
**What:** Two endpoints:
- `POST /api/v1/ml/sync` — JSON body `{platform_source, seller_id}` (both optional);
  runs sync; returns SyncResult as dict.
- `POST /api/v1/ml/init-schema` — calls `init_ml_db()` to create ml_woms_db tables.

**Why:** Exposes sync and init as REST calls so they can be triggered from admin
tooling without shell access.

---

#### `app/main.py`
**What:** Registered `reference_router` at `/api/v1/reference` and `ml_sync_router`
at `/api/v1/ml`.

**Why:** Routers must be attached to the FastAPI app to be served.

---

### New Endpoints Summary

| Method | URL | Purpose |
|---|---|---|
| POST | `/api/v1/orders/import` | Import Shopee/Lazada/TikTok CSV or Excel |
| POST | `/api/v1/reference/load-platforms` | Upsert platforms from file |
| POST | `/api/v1/reference/load-sellers` | Upsert sellers from file |
| POST | `/api/v1/reference/load-items` | Upsert items + platform_skus from file |
| POST | `/api/v1/ml/init-schema` | Initialize ml_woms_db schema |
| POST | `/api/v1/ml/sync` | Sync staging data to ml_woms_db |

---

### Data Quality Issues Documented (TikTok)

| Issue | Handling |
|---|---|
| Column header `"Tracking ID577729206730130897"` — tracking code appended to header | Renamed: any col starting with `"Tracking ID"` → `"Tracking ID"` in `parse_tiktok_file()` |
| Phone column named `"Phone #"` (non-standard) | Mapped directly in `TIKTOK_FIELD_MAP` + cleaned in `clean_tiktok_row()` |
| Timestamps in `DD/MM/YYYY HH:MM:SS` format | Added `"%d/%m/%Y %H:%M:%S"` to `_DATE_FORMATS` |
| All test data files are CSV not Excel | `_read_dataframe()` dispatches on file extension |

### Data Quality Issues Documented (Item Master)

| Issue | Handling |
|---|---|
| Headers in row 4 (not row 1) | `pd.read_excel(..., header=3)` |
| Example data rows between header and real data | Filtered: drop rows where `Internal CODE` is blank |
| Empty trailing columns (`Unnamed: N`) | Ignored — only mapped columns are accessed |
| BaseUOM values not pre-seeded for all items | `get_or_create_uom()` inserts on demand |

---

### Tests Pending
- [ ] `POST /api/v1/orders/import` — Shopee Test Data.csv (shopee, seller_id=1)
- [ ] `POST /api/v1/orders/import` — Lazada Test Data.csv (lazada, seller_id=1)
- [ ] `POST /api/v1/orders/import` — Tiktok Sample Data.csv (tiktok, seller_id=1)
- [ ] `POST /api/v1/reference/load-platforms` — test platform.xlsx → expect 10 platforms
- [ ] `POST /api/v1/reference/load-sellers` — test_sellers.xlsx + test platform.xlsx → expect 15 sellers
- [ ] `POST /api/v1/reference/load-items` — Item Master.xlsx, seller_id=1 → expect ~1900 items
- [ ] `POST /api/v1/ml/init-schema` — verify ml_woms_db tables created
- [ ] `POST /api/v1/ml/sync` — body: `{"platform_source":"tiktok"}` → verify rows copied
- [ ] `SELECT COUNT(*) FROM order_import.order_import_staging` in ml_woms_db — match woms_db count

---

## [PRE-ALPHA v0.1.0 | 2026-02-21 ~09:00] — Order Import Pipeline (Initial Build)

### Context
Analyzed two real e-commerce export files (Shopee 60-col/116-row, Lazada 79-col/120-row) and
implemented a full ingestion pipeline into the existing `order_import` schema in `woms_db`.

---

### Files Changed

#### `app/models/order_import.py`
**What:** Added two new fields to `OrderImportStaging`:
- `phone_number: Optional[str]` (max 50)
- `platform_order_status: Optional[str]` (max 50)

**Why:** The existing staging schema had no field for the shipping contact phone number
(critical for delivery operations) and no way to distinguish the platform's own order status
(e.g. Shopee "Completed", Lazada "packed") from the manually entered `manual_status` column.
These two fields exist in both datasets and are operationally meaningful.

---

#### `alembic/versions/20260221_0900_00_d5e6f7a8b9c0_add_phone_platform_status_to_staging.py`
**What:** New Alembic migration — `ALTER TABLE order_import.order_import_staging`
adds `phone_number VARCHAR(50)` and `platform_order_status VARCHAR(50)`.

**Why:** SQLModel model changes must be mirrored in a migration so the live DB schema
stays in sync. The migration chains from `c4d5e6f7a8b9` (the order_import schema creation).

---

#### `app/services/order_import/parser.py` *(new file)*
**What:** Excel-to-raw-dict parsers for Shopee and Lazada.
- `parse_shopee_excel()` — strips trailing `*` from column names (e.g. `"Tracking Number*"`)
- `parse_lazada_excel()` — renames duplicate `status` column: col 66 → `status_platform`,
  col 76 → `status_manual`

**Why:** Both platforms export columns with platform-specific quirks that must be resolved
before any cleaning or mapping. Doing this at the parse stage keeps downstream code clean
and platform-agnostic.

---

#### `app/services/order_import/cleaner.py` *(new file)*
**What:** Per-platform data cleaning functions.
- `normalize_address()` — replaces fullwidth commas U+FF0C → ASCII `,` (Lazada issue)
- `parse_flexible_date()` — handles ISO, DD.MM.YYYY, D.M.YYYY; returns `None` for
  non-date strings (e.g. driver names found in Shopee's misaligned "Date" column)
- `parse_phone()` — converts float phone numbers (e.g. `60123456789.0`) to clean string
- `clean_shopee_row()` / `clean_lazada_row()` — apply all cleaners per row

**Why:** The raw datasets contain encoding issues (Lazada fullwidth commas), column
misalignment (Shopee "Date" col containing driver names), and type inconsistencies
(phone as float, multiple date formats). Cleaning must happen before mapping to prevent
bad data reaching the staging table.

---

#### `app/services/order_import/mapper.py` *(new file)*
**What:** Field mapping configuration and staging dict builder.
- `SHOPEE_FIELD_MAP` — maps 23 staging columns to their Shopee source column names
- `LAZADA_FIELD_MAP` — maps 23 staging columns to their Lazada source column names
  (with `__LITERAL__1` for quantity since Lazada is 1 item/row, and `__CAST_STR__orderNumber`
  to handle integer order IDs)
- `map_to_staging()` — applies the map and casts values to correct types (Decimal, int, date)

**Why:** Centralising field mappings in one place makes it easy to update when platforms
change their export format, and keeps the importer logic free of per-platform conditionals.

---

#### `app/services/order_import/importer.py` *(new file)*
**What:** Main orchestration function `import_excel_file()`.
Pipeline: parse → generate batch UUID → for each row: insert raw (JSONB) → clean → map → insert staging.
Returns `ImportResult` dataclass with total/success/skipped/error counts and per-row error details.

**Why:** Separating orchestration from parsing/cleaning/mapping means each concern can be
tested and maintained independently. The two-table design (raw + staging) preserves the
original data immutably while giving a clean normalized view for order processing.

---

#### `app/services/order_import/__init__.py` *(new file)*
**What:** Package init — exports `import_excel_file` and `ImportResult`.

**Why:** Clean public API for the service package; consumers import from the package,
not from internal modules directly.

---

#### `app/routers/order_import.py` *(new file)*
**What:** FastAPI router with `POST /api/v1/orders/import`.
Accepts: `platform` (form field), `seller_id` (form field), `file` (UploadFile .xlsx).
Returns: JSON import summary (counts + error list).
Validates: platform name, file extension, file size (≤ 10 MB).

**Why:** Exposes the import pipeline as a REST endpoint so the frontend or admin tooling
can trigger imports without direct DB access. File size limit prevents memory exhaustion
from oversized uploads.

---

#### `app/main.py`
**What:** Registered the new order_import router under `{api_v1_prefix}/orders`.

**Why:** The router must be attached to the FastAPI app to be served. Placed under `/orders`
prefix to keep the import endpoint logically grouped with order-related operations.

---

### Data Quality Issues Documented (from test file analysis)

| Platform | Issue | Handling |
|---|---|---|
| Shopee | "Tracking Number*" column has trailing asterisk | Stripped in `parse_shopee_excel()` |
| Shopee | "Date" col (manual) contains driver names / tracking codes | `parse_flexible_date()` returns `None` for non-date strings |
| Shopee | Mixed date formats (ISO vs DD.MM.YYYY) | `parse_flexible_date()` tries multiple formats |
| Shopee | Phone stored as float (`60123456789.0`) | `parse_phone()` strips `.0` |
| Lazada | Duplicate `status` column (col 66 + col 76) | Renamed to `status_platform` / `status_manual` |
| Lazada | Fullwidth comma U+FF0C in addresses | `normalize_address()` replaces with ASCII `,` |
| Lazada | `orderNumber` stored as integer | `__CAST_STR__` sentinel in mapper |
| Lazada | 27 completely empty columns | Skipped in staging; preserved in raw JSONB |
| Both | Numeric prices as float/int in Excel | `parse_decimal()` → `Decimal` |

---

### Tests Pending
- [ ] `alembic upgrade head` — verify migration applies cleanly
- [ ] `POST /api/v1/orders/import` with Shopee Test Data.xlsx — expect 116 success rows
- [ ] `POST /api/v1/orders/import` with LAZADA Test Data.xlsx — expect 120 success rows
- [ ] Query `order_import.order_import_raw` — verify JSONB row count matches
- [ ] Query `order_import.order_import_staging` — spot-check mapped fields
- [ ] Verify Lazada `platform_order_status = 'packed'` (from col 66)
- [ ] Verify Lazada address has no fullwidth commas after import
- [ ] Verify Shopee non-date "Date" values produce `manual_date = NULL`

---

## [PRE-ALPHA v0.2.0 | 2026-02-21 10:00] — SQL Migration → Python Conversion

### Context
All content from `migrations/*.sql` (triggers, views, seed data, indexes) has been
converted to Python and embedded directly in `app/models/`. The SQL files are retained
as reference only — the application no longer reads them at runtime.

**Why:** Keeping DB logic in external SQL files created an implicit dependency on the
filesystem and made it easy for the schema to drift from the Python models. Embedding
everything in Python means a fresh `init_db_full()` call produces a fully operational
database without any manual SQL steps.

---

### New Files Created

#### `app/models/triggers.py`
**What:** All 8 PostgreSQL trigger functions as Python string constants in `_TRIGGER_SQL`.
Public API: `async def apply_triggers(conn: AsyncConnection) -> None`.

Triggers: `update_timestamp`, `check_inventory_threshold`, `update_inventory_on_transaction`,
`auto_resolve_inventory_alerts`, `update_updated_at_column`, `sync_order_detail_return_status`,
`calculate_exchange_value_difference`, `calculate_price_adjustment_final`.

**Why:** `CREATE OR REPLACE FUNCTION` and `DROP TRIGGER IF EXISTS` make every statement
idempotent. Called from `database.run_migrations()` so triggers are always applied after
`create_all()` without needing to run SQL files manually.

---

#### `app/models/views.py`
**What:** All 12 reporting views as Python string constants.
Public API: `async def apply_views(conn: AsyncConnection) -> None`.

Views: `v_inventory_status`, `v_order_fulfillment`, `v_seller_warehouse_routing`,
`v_platform_import_status`, `v_active_inventory_alerts`, `v_warehouse_summary`,
`v_order_line_items`, `v_order_returns`, `v_order_exchanges`, `v_order_modifications`,
`v_order_price_adjustments`, `v_order_operations_summary`.

**Why:** `CREATE OR REPLACE VIEW` is idempotent. Views provide denormalized read-only
projections used by reporting/dashboard queries.

---

#### `app/models/seed.py`
**What:** All lookup table seed data as Python data structures.
Public API: `async def seed_database(session: AsyncSession) -> None`.

Tables seeded: `action_type`, `status`, `item_type`, `base_uom`, `inventory_type`,
`movement_type`, `delivery_status`, `roles`, `platform`, `cancellation_reason`,
`return_reason`, `exchange_reason`.

**Why:** `INSERT … ON CONFLICT DO NOTHING` is idempotent. Seed data is required for
FK lookups and role-based access control and must be applied immediately after schema creation.

---

#### `alembic/versions/20260221_1000_00_e6f7a8b9c0d1_add_all_performance_indexes.py`
**What:** Alembic migration applying all 47 performance indexes (GIN + composite +
partial) to existing databases using `CREATE INDEX IF NOT EXISTS`.

**Why:** `__table_args__` indexes are created by `create_all()` for fresh databases
but existing databases need an explicit Alembic migration. All statements use
`IF NOT EXISTS` so re-running is safe.

---

### Files Modified

#### `app/models/items.py`
**What:** Added `__table_args__` to `Item` (GIN on `variations_data`; partial active items)
and `ItemsHistory` (GIN on `snapshot_data`).

**Why:** GIN enables `@>` JSONB containment queries. Partial index covers the
overwhelmingly common "active items only" query pattern.

---

#### `app/models/warehouse.py`
**What:** Added `__table_args__` to `Warehouse`, `InventoryLevel`, `InventoryAlert`,
`SellerWarehouse`, `InventoryTransaction` — composite and partial indexes for stock
lookups, FIFO/FEFO allocation, alert dashboards, and transaction history.

**Why:** Inventory queries are the highest-frequency operations in a WMS.

---

#### `app/models/users.py`
**What:** Added `__table_args__` to `Role` (GIN on `permissions`) and `AuditLog`
(GIN on `old_data` and `new_data`).

**Why:** Enables permission-level JSONB queries and before/after change queries on the
audit log without full table scans.

---

#### `app/models/orders.py`
**What:** Added `Index` + `text` imports. Added `__table_args__` to `Seller`, `PlatformRawImport`,
`PlatformSKU`, `CustomerPlatform`, `Order`, `OrderDetail` — GIN indexes on all JSONB
fields; composite indexes for fulfillment queue, reporting, SKU translation; partial
indexes for pending orders and active-only filtering.

**Why:** Order queries are the most common read pattern. Partial indexes on "pending"
orders avoid scanning completed/cancelled rows.

---

#### `app/models/order_operations.py`
**What:** Added `Index` + `text` imports. Added `__table_args__` to `ReturnReason`,
`OrderReturn`, `ExchangeReason`, `OrderExchange`, `OrderModification`, `OrderPriceAdjustment`.

Partial indexes on optional FK columns use `WHERE col IS NOT NULL` — avoids indexing NULL
entries which are never used in FK-specific joins.

**Why:** GIN on JSONB diffs enables audit trail queries by field value.

---

#### `app/database.py`
**What:** Replaced `run_migrations()` (read SQL files) with calls to `apply_triggers(conn)`,
`apply_views(conn)`, `seed_database(session)` from the new Python modules.

**Why:** Application no longer depends on `migrations/*.sql` at runtime. All DB init
logic is self-contained in Python and importable/testable.

---

#### `app/models/__init__.py`
**What:** Added imports and `__all__` entries for `apply_triggers`, `apply_views`,
`seed_database`.

**Why:** Callers that already import from `app.models` can access init utilities without
a separate import path.

---

### Tests Pending
- [ ] `alembic upgrade head` — confirm `e6f7a8b9c0d1` applies without error
- [ ] `python -c "import asyncio; from app.database import init_db_full; asyncio.run(init_db_full())"` — fresh DB: confirm triggers/views/seed applied
- [ ] `SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename` — verify 47 new indexes present
- [ ] `SELECT * FROM action_type` — confirm seed data populated
- [ ] GIN query test: `SELECT * FROM orders WHERE platform_raw_data @> '{"platform":"shopee"}'`

---

## [PRE-ALPHA v0.1.1 | 2026-02-21 ~09:30] — Ground Rules & Version Control Setup

### Files Changed

#### `version_update.md` *(this file — new)*
**What:** Created version update log with pre-alpha versioning scheme.
Backfilled all v0.1.0 work.

**Why:** User ground rule — all changes must be logged with version label, timestamp,
file changed, what was done, and why.

#### `C:\Users\James\.claude\projects\d--Documents-Project-WOMS-FYP-NEW\memory\MEMORY.md`
**What:** Added ground rule #5 (version_update.md logging) and created the file with
project overview, key file paths, recent work summary, and patterns.

**Why:** Persists project context and user preferences across jtee509 sessions so rules
and architecture decisions don't need to be re-explained each time.
