# Plan: Warehouse Rename & Hierarchy Refactor
**Status:** COMPLETED
**Version Target:** PRE-ALPHA v0.5.41
**Date Drafted:** 2026-03-12
**Author:** James (via jtee509)

---

## 1. Overview

This plan covers two tightly coupled changes that must be applied together to avoid
partial-state inconsistencies:

1. **Table rename** — `warehouse` → `warehouse_site`
2. **Location hierarchy refactor** — retire `section` and `bin`; rename `rack`→`bay`,
   `bin`→`rack`; warehouse itself becomes the explicit top-level node

### Why these changes?

- The term "warehouse" is overloaded: it refers to both the physical site and the
  management concept. Renaming the table to `warehouse_site` clarifies that the DB
  row represents a physical facility, not an abstract container.
- The old 5-level hierarchy (`section > zone > aisle > rack > bin`) had an ambiguous
  `section` that duplicated the warehouse's own grouping role. The new structure
  (`warehouse > zone > aisle > bay > rack`) removes that redundancy and uses
  industry-standard terminology (bay = storage bay, rack = physical racking unit).

---

## 2. Scope

### In scope
- Alembic migration: table rename, column renames, data migration, index rebuild
- Python model: `__tablename__`, field names, `full_location_code` property, `__table_args__`
- Python schemas: all `InventoryLocation*` schemas, `HierarchyLevel`, `BulkGenerateRequest`,
  `SegmentRange`, `RenameLevelRequest`, `BulkLocationUpdateItem`, `LocationTreeNode`
- Python router: query param names, filter logic, hierarchy tree builder, bulk-generate
  segment assignment, display-code build logic
- Triggers module: `display_code` trigger column list
- Frontend types: `warehouse.ts` base_types
- Frontend API client: `warehouse.ts` base
- Frontend UI: Settings tabs, warehouse pages, all column headers and form labels

### Out of scope
- Order module — references `warehouse_id` FK only (column name unchanged, stays `warehouse_id`)
- Delivery / users / seller modules — same FK-only dependency
- Auth / JWT — unaffected
- ML sync database — mirrors schema; apply same migration to `ml_woms_db` after main DB

---

## 3. Hierarchy Mapping

| Old column | New column | Notes |
|------------|------------|-------|
| `section`  | *(removed)*| Data preserved by collapsing into `zone` where `zone IS NULL` |
| `zone`     | `zone`     | Unchanged |
| `aisle`    | `aisle`    | Unchanged |
| `rack`     | `bay`      | Column rename only |
| `bin`      | `rack`     | Column rename only |

**Visual before/after:**

```
BEFORE                          AFTER
──────────────────────          ──────────────────────
warehouse                       warehouse_site  ← table rename
  └─ section                      └─ [zone]     ← top sub-level (section retired)
       └─ zone                          └─ aisle
            └─ aisle                         └─ bay   ← was rack
                 └─ rack                          └─ rack  ← was bin
                      └─ bin
```

---

## 4. Data Migration Strategy

### 4a. Retiring `section`

`section` was used as a loose top-level grouper within a warehouse. Two options exist:

| Option | Description | When to use |
|--------|-------------|-------------|
| **A (recommended)** | Copy `section` → `zone` where `zone IS NULL` | Most real-world setups where section ≈ zone |
| B | Discard `section` data | Only if section values are already duplicated in `zone` |

**Default: Option A.** The Alembic migration will execute:

```sql
UPDATE inventory_location
SET zone = section
WHERE zone IS NULL AND section IS NOT NULL;
```

After this, `section` is dropped.

### 4b. Regenerating `display_code`

The `display_code` trigger-generated value currently encodes `section-zone-aisle-rack-bin`.
After migration it must encode `zone-aisle-bay-rack`. The migration will bulk-update:

```sql
UPDATE inventory_location
SET display_code = CONCAT_WS('-',
    NULLIF(zone, ''), NULLIF(aisle, ''),
    NULLIF(bay,  ''), NULLIF(rack,  ''))
WHERE deleted_at IS NULL;
```

### 4c. Unique constraint rebuild

Old constraint: `(warehouse_id, section, zone, aisle, rack, bin)`
New constraint: `(warehouse_id, zone, aisle, bay, rack)`

The migration drops the old constraint and creates the new one. Duplicates could
arise if two locations shared the same `zone/aisle/rack/bin` but different `section`
values — check for this before running on production data.

---

## 5. Implementation Sequence

All steps must be executed in this order to maintain backend→frontend contract integrity.

```
PHASE 1 — Planning & DB Prep
  [x] Draft this plan document
  [ ] Run duplicate-check query on production DB before migration
  [ ] Decide section-retirement option (default: Option A)

PHASE 2 — Alembic Migration
  [ ] Create migration file: 20260312_XXXX_rename_warehouse_site_refactor_hierarchy.py
  [ ] Implement upgrade(): rename table, data migration, column renames, constraint rebuild,
      display_code bulk update
  [ ] Implement downgrade(): full rollback
  [ ] Test upgrade + downgrade on dev DB copy
  [ ] Apply to dev DB; verify with \d warehouse_site and SELECT * FROM inventory_location LIMIT 10

PHASE 3 — Backend Model
  [ ] warehouse.py: __tablename__ = "warehouse_site"
  [ ] InventoryLocation: remove section field, rename rack→bay, bin→rack fields
  [ ] Update full_location_code property (4-part: zone-aisle-bay-rack)
  [ ] Update __table_args__: drop section from unique constraint + indexes, rename rack/bin indexes

PHASE 4 — Backend Schemas
  [ ] InventoryLocationCreate / Update / Read: remove section, rename rack→bay, bin→rack
  [ ] LocationSummary: same
  [ ] HierarchyLevel: Literal["zone", "aisle", "bay", "rack"]
  [ ] BulkGenerateRequest / SegmentRange: remove section slot, rename rack→bay, bin→rack
  [ ] RenameLevelRequest: level field follows updated HierarchyLevel (auto-fixed)
  [ ] BulkLocationUpdateItem: remove section, rename fields
  [ ] LocationTreeNode: update type literals

PHASE 5 — Backend Router
  [ ] GET /warehouse/{id}/locations — remove section filter param, rename rack/bin params
  [ ] DELETE /warehouse/{id}/locations/subtree — same filter rename
  [ ] GET /warehouse/{id}/locations/hierarchy — change tree builder to group by zone first
  [ ] POST /warehouse/{id}/locations/bulk-generate — segment slot order: zone→aisle→bay→rack
  [ ] display_code build in create/update: remove section, use zone-aisle-bay-rack
  [ ] All other filter/query logic referencing section, rack (old), bin

PHASE 6 — Triggers Module
  [ ] backend/app/models/triggers.py: update display_code trigger column list

PHASE 7 — Backend Smoke Test
  [ ] uvicorn restart (no import errors)
  [ ] GET /api/v1/warehouse — verify warehouse_site rows returned
  [ ] GET /api/v1/warehouse/{id}/locations — verify zone/aisle/bay/rack fields present
  [ ] GET /api/v1/warehouse/{id}/locations/hierarchy — verify tree structure
  [ ] POST /api/v1/warehouse/{id}/locations/bulk-generate — verify 4-segment generation
  [ ] PATCH /api/v1/warehouse/{id}/locations/rename-level — verify new level names accepted

PHASE 8 — Frontend Types
  [ ] frontend/src/api/base_types/warehouse.ts:
        HierarchyLevel, InventoryLocationRead/Create/Update, LocationSummary,
        LocationTreeNode, SegmentRangeInput, BulkGenerateRequest,
        RenameLevelRequest, BulkLocationUpdateItem

PHASE 9 — Frontend API Client
  [ ] frontend/src/api/base/warehouse.ts:
        listLocations, deleteLocationSubtree, bulkUpdateLocations,
        bulkGenerateLocations — update field names in request bodies/params

PHASE 10 — Frontend UI
  [ ] WarehouseSettingsTab.tsx — table columns: remove SECTION, rename RACK→BAY, BIN→RACK
  [ ] LocationManagementSection.tsx — inline edit fields + column headers
  [ ] BulkCreationWizard (inside settings) — 4 segment slots: Zone, Aisle, Bay, Rack
  [ ] CsvLocationImport — template column order: zone, aisle, bay, rack
  [ ] InventoryLevelsPage.tsx — location display strings (remove section prefix)
  [ ] InventoryMovementsPage.tsx + MovementExpandedRow.tsx — location labels
  [ ] RecordMovementDrawer.tsx — location picker grouping (was by section, now by zone)
  [ ] Any other component rendering full_location_code / display_code breakdown

PHASE 11 — Frontend Smoke Test
  [ ] Settings → Warehouse → Location Setup: create location, verify 4 fields shown
  [ ] Settings → Warehouse → Location Setup → Pattern Generator: 4 segments work
  [ ] Inventory Levels page: location codes display as zone-aisle-bay-rack
  [ ] Inventory Movements page: expanded row location labels correct
  [ ] Record Movement drawer: location picker renders new hierarchy

PHASE 12 — Documentation
  [ ] docs/official_documentation/database_structure.md — update warehouse_site table,
      update inventory_location columns (remove section, rename rack/bin)
  [ ] docs/official_documentation/web-api.md — update location endpoints,
      remove section from all request/response examples, rename rack/bin
  [ ] docs/official_documentation/version_update.md — log as PRE-ALPHA v0.5.41

PHASE 13 — ML Database
  [ ] Apply identical Alembic migration to ml_woms_db (or run migration against both URLs)
```

---

## 6. Affected Files

### Backend

| File | Change type |
|------|-------------|
| `backend/alembic/versions/20260312_XXXX_*.py` | New migration |
| `backend/app/models/warehouse.py` | __tablename__, field names, property, table_args |
| `backend/app/schemas/warehouse.py` | Field renames, HierarchyLevel type |
| `backend/app/routers/warehouse.py` | Query params, filter logic, tree builder, bulk-generate |
| `backend/app/models/triggers.py` | display_code trigger column list |

### Frontend

| File | Change type |
|------|-------------|
| `frontend/src/api/base_types/warehouse.ts` | Type renames |
| `frontend/src/api/base/warehouse.ts` | Request field renames |
| `frontend/src/pages/settings/WarehouseSettingsTab.tsx` | Column headers |
| `frontend/src/pages/settings/LocationManagementSection.tsx` | Field labels, column headers |
| `frontend/src/pages/warehouse/InventoryLevelsPage.tsx` | Location display |
| `frontend/src/pages/warehouse/InventoryMovementsPage.tsx` | Location labels |
| `frontend/src/pages/warehouse/MovementExpandedRow.tsx` | Location labels |
| `frontend/src/pages/warehouse/RecordMovementDrawer.tsx` | Location picker grouping |

### Docs

| File | Change |
|------|--------|
| `docs/official_documentation/database_structure.md` | warehouse_site table, updated location columns |
| `docs/official_documentation/web-api.md` | Endpoint request/response examples |
| `docs/official_documentation/version_update.md` | Changelog entry v0.5.41 |

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| `section` data loss | HIGH — existing location codes become meaningless | Run Option A data migration before dropping column; verify row counts before and after |
| Duplicate locations after section removal | MEDIUM — constraint violation on upgrade | Run pre-migration duplicate-check query; resolve conflicts manually before migration |
| `display_code` stale after rename | LOW — visual codes wrong in UI | Bulk UPDATE in migration immediately after column renames; verify sample rows |
| FK errors on warehouse table rename | LOW — PostgreSQL auto-updates FK refs on rename | Verify with `\d inventory_location` after migration |
| TypeScript compile errors | LOW — blocked build | Update base_types first; TS compiler surfaces all usages |
| JSONB audit fields retain old field names | LOW — legacy data inconsistency | Document as known legacy data; no code fix required |
| ml_woms_db out of sync | MEDIUM — ML pipeline breaks | Apply same migration to ml_woms_db immediately after main DB |

---

## 8. Pre-Migration DB Checks

Run these queries before executing the Alembic migration on any environment with real data:

```sql
-- Check for section data that would be lost if not migrated to zone
SELECT COUNT(*) AS rows_with_section_only
FROM inventory_location
WHERE section IS NOT NULL AND zone IS NULL AND deleted_at IS NULL;

-- Check for potential duplicate locations after section is removed
-- (same warehouse_id + zone + aisle + rack + bin but different section)
SELECT warehouse_id, zone, aisle, rack AS bay_new, bin AS rack_new, COUNT(*) AS cnt
FROM inventory_location
WHERE deleted_at IS NULL
GROUP BY warehouse_id, zone, aisle, rack, bin
HAVING COUNT(*) > 1;

-- Baseline counts
SELECT COUNT(*) FROM warehouse;
SELECT COUNT(*) FROM inventory_location WHERE deleted_at IS NULL;
```

---

## 9. Rollback Plan

If the migration must be reverted after being applied:

1. Run `alembic downgrade <previous_revision>` — downgrade() restores original column names
   and recreates the old `section` column (populated with NULL values; original data is gone
   if it was not backed up separately).
2. Redeploy previous backend code version.
3. Redeploy previous frontend build.

**Note:** `section` data cannot be recovered from the DB after upgrade unless a DB backup
was taken immediately before migration. Always snapshot the DB before running in production.

---

## 10. Definition of Done

- [ ] All 13 phases completed and checked off
- [ ] No TypeScript compile errors
- [ ] Backend starts cleanly with no import/migration errors
- [ ] All smoke-test API calls return correct field names
- [ ] Frontend renders new hierarchy correctly end-to-end
- [ ] Documentation updated
- [ ] version_update.md entry added as PRE-ALPHA v0.5.41
