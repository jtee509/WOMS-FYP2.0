---
name: Bundle Module v2 — Decoupled BOM Plan
overview: >
  Revised plan for the Bundle feature. The original Bundle implementation (v0.5.17–v0.5.27)
  tied bundles to the PlatformSKU / listing_component tables, requiring platform_id and
  seller_id to create a bundle. This coupling was incorrect: a bundle is a catalog/warehouse
  concept, not a platform concept. This plan decouples bundles from platform listings by
  introducing a dedicated bundle_components table and updating all 7 bundle API endpoints.
  Target versions: PRE-ALPHA v0.5.50+
created: 2026-03-09
author: Planning phase document
supersedes: docs/planning_phase/Backend/07_bundle_sku_inventory_plan.plan.md
---

# Bundle Module v2 — Decoupled BOM Plan

**Target versions:** PRE-ALPHA v0.5.50+
**Created:** 2026-03-09
**Supersedes:** `07_bundle_sku_inventory_plan.plan.md` (v0.5.17–v0.5.27, now removed)
**Status:** PLANNING

---

## 1. Problem Statement

### 1.1 What went wrong with v1

The original bundle implementation (v0.5.17–v0.5.27) went through three phases:

| Phase | What happened | Outcome |
|-------|---------------|---------|
| v0.5.17–v0.5.19 | Created `item_bundle_components` table (warehouse-level BOM) + ATP logic | Worked but was complex |
| v0.5.27 | **Dropped** `item_bundle_components` table via migration `cc0305drop01` | BOM removed from DB |
| Post-v0.5.27 | Backend endpoints rewritten to use `listing_component` + `platform_sku` | Coupled bundles to platforms |

**Current state (broken coupling):**

```
Bundle Item → PlatformSKU (requires platform_id + seller_id) → listing_component (BOM rows)
```

This architecture has two fundamental problems:

1. **Platform dependency:** Creating a bundle requires choosing a platform and seller, even
   though bundles are an internal catalog/warehouse concept. A "Summer Essentials Pack" should
   exist independently of Lazada/Shopee/TikTok.

2. **SKU collision:** The create endpoint sets `PlatformSKU.platform_sku = Item.master_sku`,
   which collides with real platform SKUs if the same item is later listed on a platform.

### 1.2 What we want

```
Bundle Item → bundle_components (BOM rows, platform-independent)
```

A bundle is simply an Item with `item_type = "Bundle"` plus 1+ component rows in a dedicated
`bundle_components` table. No platform involvement. Platform listings for bundles are handled
separately via the existing `listing_component` → `platform_sku` flow when the bundle is
actually listed on a marketplace.

### 1.3 Bundle validity rules (from user requirements)

A bundle is **valid** and shown on the Bundles page if it satisfies at least one of:

- **(a)** At least one component has `quantity > 1` (e.g., "2× Item A")
- **(b)** The bundle contains more than one distinct component item (e.g., "1× Item A + 1× Item B")

A trivial "bundle" of "1× Item A" is not a real bundle — it's just a single item and should
NOT appear on the Bundles page. This rule is enforced both at CREATE/UPDATE time (backend
validation) and at LIST time (query filter).

**Items vs Bundles page separation:**

- **Items List** (`/catalog/items`): Must exclude Bundle-type items (`exclude_item_type_id`)
- **Bundles List** (`/catalog/bundles`): Must show ONLY items with `item_type = "Bundle"` that
  pass the validity rules above

---

## 2. Proposed Schema

### 2.1 New table: `bundle_components`

```sql
CREATE TABLE bundle_components (
    id              SERIAL PRIMARY KEY,
    bundle_item_id  INT NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    component_item_id INT NOT NULL REFERENCES items(item_id) ON DELETE RESTRICT,
    quantity        INT NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (bundle_item_id, component_item_id)
);

-- Indexes
CREATE INDEX idx_bundle_comp_bundle ON bundle_components(bundle_item_id);
CREATE INDEX idx_bundle_comp_component ON bundle_components(component_item_id);
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| `ON DELETE CASCADE` on `bundle_item_id` | If the bundle item is hard-deleted, its BOM goes too |
| `ON DELETE RESTRICT` on `component_item_id` | Cannot delete an item that's used as a bundle component — must remove from bundle first |
| `UNIQUE (bundle_item_id, component_item_id)` | Same item cannot appear twice in a bundle; use `quantity` to express multiples |
| `sort_order` | Allows user to arrange components in a preferred display order |
| No `is_active` / `deleted_at` | BOM rows are either present or deleted; no soft-delete needed |

### 2.2 Alembic migration

```
File: backend/alembic/versions/20260310_xxxx_create_bundle_components.py
Revision: (auto-generated)
Down_revision: (current head)
```

Migration creates the `bundle_components` table and its indexes. No data migration needed
since the `item_bundle_components` table was already dropped and there's no BOM data to
preserve in `listing_component` (those rows will remain as platform listing data).

### 2.3 SQLModel model

```python
# In backend/app/models/items.py

class BundleComponent(SQLModel, table=True):
    """
    Bill of Materials (BOM) for bundle items.
    Links a bundle item to its component items with quantities.
    """
    __tablename__ = "bundle_components"
    __table_args__ = (
        Index("idx_bundle_comp_bundle", "bundle_item_id"),
        Index("idx_bundle_comp_component", "component_item_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    bundle_item_id: int = Field(foreign_key="items.item_id", index=True)
    component_item_id: int = Field(foreign_key="items.item_id", index=True)
    quantity: int = Field(default=1, ge=1)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.4 What stays unchanged

| Table | Role | Change |
|-------|------|--------|
| `items` | Bundle items identified by `item_type_id` = Bundle | None |
| `item_type` | Contains "Bundle" seed value | None |
| `platform_sku` | Platform marketplace listings | No longer used for internal bundles |
| `listing_component` | Platform listing → item mapping | Remains for platform kit definitions |

---

## 3. Backend API Changes

All 7 bundle endpoints are updated. The key change is replacing `PlatformSKU` + `ListingComponent`
with `BundleComponent`.

### 3.1 Schema changes (`backend/app/schemas/items.py`)

**Remove from `BundleCreateRequest`:**
```python
# REMOVE these fields:
platform_id: int
seller_id: int
```

**Remove from `BundleReadResponse`:**
```python
# REMOVE these fields:
listing_id: int
platform_sku: str
```

**Updated schemas:**

```python
class BundleCreateRequest(BaseModel):
    item_name: str = Field(..., max_length=500)
    master_sku: str = Field(..., max_length=100)
    sku_name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    uom_id: Optional[int] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: bool = True
    components: list[BundleComponentInput] = Field(..., min_length=1)

class BundleReadResponse(BaseModel):
    item: ItemRead
    components: list[BundleComponentRead]

class BundleComponentRead(BaseModel):
    id: int
    item_id: int
    item_name: str
    master_sku: str
    image_url: Optional[str] = None
    quantity: int
    sort_order: int = 0
```

### 3.2 Endpoint changes summary

| Endpoint | Current | New |
|----------|---------|-----|
| `POST /items/bundles` | Creates Item + PlatformSKU + ListingComponent | Creates Item + BundleComponent rows |
| `PATCH /items/bundles/{id}` | Updates Item + PlatformSKU + deletes/reinserts ListingComponent | Updates Item + deletes/reinserts BundleComponent |
| `GET /items/bundles/{id}` | Joins via PlatformSKU → ListingComponent | Direct query on BundleComponent |
| `GET /items/bundles` | Subquery on PlatformSKU → ListingComponent for counts | Subquery on BundleComponent for counts |
| `GET /items/bundles/counts` | Counts items with type=Bundle | Same (no change) |
| `DELETE /items/bundles/{id}` | Soft-deletes Item + deactivates PlatformSKU | Soft-deletes Item only (BOM rows kept) |
| `POST /items/bundles/{id}/restore` | Restores Item + re-activates PlatformSKU | Restores Item only |

### 3.3 Create bundle flow (revised)

```
1. Validate master_sku uniqueness
2. Validate bundle composition (>1 distinct items OR qty > 1)
3. Validate all component item_ids exist and are not deleted
4. Resolve "Bundle" item_type_id
5. INSERT into items (item_type_id = Bundle)
6. INSERT into bundle_components (one row per component)
7. Return BundleReadResponse
```

No PlatformSKU or ListingComponent involvement.

### 3.4 List bundles — validity filter

The `GET /items/bundles` endpoint must enforce the validity rules from Section 1.3.
After filtering to `item_type = "Bundle"`, add a subquery that filters to only bundles where:

```sql
-- Subquery: valid bundles (pass at least one condition)
SELECT bc.bundle_item_id
FROM bundle_components bc
GROUP BY bc.bundle_item_id
HAVING
    COUNT(DISTINCT bc.component_item_id) > 1    -- (b) multiple distinct components
    OR MAX(bc.quantity) > 1                       -- (a) any component with qty > 1
```

Bundles that fail both conditions (single component with qty=1) are excluded from the list.

---

## 4. Frontend Changes

### 4.1 Type updates (`frontend/src/api/base_types/items.ts`)

```typescript
// Remove platform_id, seller_id from BundleCreateRequest
export interface BundleCreateRequest {
  item_name: string;
  master_sku: string;
  sku_name?: string;
  description?: string;
  image_url?: string;
  uom_id?: number;
  brand_id?: number;
  category_id?: number;
  is_active?: boolean;
  components: BundleComponentInput[];
}

// Remove listing_id, platform_sku from BundleReadResponse
export interface BundleReadResponse {
  item: ItemRead;
  components: BundleComponentRead[];
}

// Add image_url + sort_order to BundleComponentRead
export interface BundleComponentRead {
  id: number;
  item_id: number;
  item_name: string;
  master_sku: string;
  image_url: string | null;
  quantity: number;
  sort_order: number;
}
```

### 4.2 BundleFormPage updates

Already done (v0.5.50 prep):
- ✅ Removed Platform and Seller fields from the form UI
- ✅ Removed platform/seller imports, state, and API calls
- ✅ Updated create payload to not send platform_id/seller_id

Still needed:
- Update `BundleReadResponse` usage (remove `listing_id` / `platform_sku` references)
- Remove `existingListingId` state variable (orphaned)

### 4.3 BundlesListPage

Already functional. The list page calls `GET /items/bundles` which will return only valid
bundles after the backend filter is applied.

### 4.4 Items page exclusion

The Items List page (`/catalog/items`) must exclude Bundle-type items. Implementation:

```typescript
// On mount, resolve "Bundle" type ID from the item types list
const bundleType = itemTypes.find(t => t.name === 'Bundle');

// Pass to listItems and getItemCounts
listItems({ ...params, exclude_item_type_id: bundleType?.id });
getItemCounts({ exclude_item_type_id: bundleType?.id });
```

The backend `listItems` and `getItemCounts` already support `exclude_item_type_id`.

---

## 5. Implementation Phases

### Phase 1: Database + Model (v0.5.50)

| Step | File | Action |
|------|------|--------|
| 1 | `backend/app/models/items.py` | Add `BundleComponent` SQLModel class |
| 2 | `backend/alembic/versions/` | Create migration for `bundle_components` table |
| 3 | `backend/app/main.py` | Ensure model is imported (for create_all) |

### Phase 2: Backend API (v0.5.51)

| Step | File | Action |
|------|------|--------|
| 1 | `backend/app/schemas/items.py` | Remove `platform_id`/`seller_id` from `BundleCreateRequest`; remove `listing_id`/`platform_sku` from `BundleReadResponse` |
| 2 | `backend/app/routers/items.py` | Rewrite all 7 bundle endpoints to use `BundleComponent` instead of `ListingComponent` + `PlatformSKU` |
| 3 | Test all 7 endpoints manually | Ensure create, read, update, list, counts, delete, restore all work |

### Phase 3: Frontend sync (v0.5.52)

| Step | File | Action |
|------|------|--------|
| 1 | `frontend/src/api/base_types/items.ts` | Remove `listing_id`/`platform_sku` from `BundleReadResponse` |
| 2 | `frontend/src/pages/bundles/BundleFormPage.tsx` | Remove `existingListingId` state |
| 3 | `frontend/src/pages/items/ItemsListPage.tsx` | Add `exclude_item_type_id` filter to exclude bundles |
| 4 | End-to-end test | Create bundle → verify it appears in Bundles list but NOT Items list |

### Phase 4: Items page exclusion (v0.5.53)

| Step | File | Action |
|------|------|--------|
| 1 | `frontend/src/pages/items/ItemsListPage.tsx` | On mount, resolve "Bundle" type ID → pass as `exclude_item_type_id` to `listItems` + `getItemCounts` |
| 2 | Verify | Items page shows no Bundle-type items; Bundles page shows only valid bundles |

---

## 6. Data Migration Notes

### 6.1 Existing bundle items

Any items with `item_type = "Bundle"` created via the old flow will:
- Still appear as items with type "Bundle"
- Have `listing_component` rows linked via `platform_sku`
- NOT have `bundle_components` rows (new table)

**Migration strategy:** After creating the `bundle_components` table, run a one-time script
to copy BOM data from `listing_component` → `bundle_components` for existing bundles:

```python
# One-time migration script (not an Alembic migration)
# For each bundle item:
#   1. Find PlatformSKU where platform_sku = item.master_sku
#   2. Copy listing_component rows to bundle_components
#   3. (Optional) Delete the PlatformSKU + listing_component rows
```

### 6.2 Fresh installs

No migration needed. The `bundle_components` table is created empty.

---

## 7. Future Considerations (out of scope)

These are NOT part of this plan but are noted for future reference:

| Feature | Description |
|---------|-------------|
| **Bundle ATP** | Computed available-to-promise stock for bundles (min of component quantities / BOM quantities) |
| **Bundle inventory deduction** | When a bundle is sold, atomically deduct component stock with reservation |
| **Nested bundles** | A bundle containing another bundle — requires cycle detection |
| **Platform bundle listing** | Linking a bundle to a platform via `platform_sku` + `listing_component` (separate from internal BOM) |
| **Bundle pricing** | Computed or overridden pricing for bundles vs sum of components |

---

## 8. Files Changed Summary

| File | Change Type |
|------|-------------|
| `backend/app/models/items.py` | ADD `BundleComponent` model |
| `backend/alembic/versions/` | ADD migration for `bundle_components` |
| `backend/app/schemas/items.py` | MODIFY — remove platform fields from bundle schemas |
| `backend/app/routers/items.py` | MODIFY — rewrite 7 bundle endpoints |
| `frontend/src/api/base_types/items.ts` | MODIFY — update bundle types |
| `frontend/src/pages/bundles/BundleFormPage.tsx` | MODIFY — cleanup orphaned state |
| `frontend/src/pages/items/ItemsListPage.tsx` | MODIFY — add bundle exclusion filter |
| `docs/official_documentation/database_structure.md` | UPDATE — add `bundle_components` table |
| `docs/official_documentation/web-api.md` | UPDATE — revised bundle API docs |
| `docs/official_documentation/version_update.md` | UPDATE — changelog entries |
