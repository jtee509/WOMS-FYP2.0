---
name: Bundle SKU Frontend Plan
overview: >
  Frontend implementation plan for Bundle SKU inventory management.
  Covers TypeScript type extensions, API function additions, conditional
  Bundle Components tab inside ItemFormPage, bundle-aware rows on
  InventoryLevelsPage, and bundle confirmation on InventoryMovementsPage.
  All work lives inside existing page subfolders — no new routes.
  Target versions: PRE-ALPHA v0.5.20 – v0.5.22
created: 2026-03-04
author: Planning phase document
backend_plan: docs/planning_phase/Backend/05_bundle_sku_inventory_plan.plan.md
---

# Bundle SKU Frontend Plan

**Target versions:** PRE-ALPHA v0.5.20 – v0.5.22
**Created:** 2026-03-04
**Backend plan:** `docs/planning_phase/Backend/05_bundle_sku_inventory_plan.plan.md`
**Status:** Planning — not yet implemented

---

## 1. Current State Audit

### 1.1 Items Module

| Surface | Current State | Required Change |
|---------|--------------|-----------------|
| `ItemFormPage.tsx` | Single-card form, General section only | Add tabbed layout (General / Bundle Components) conditional on item_type = Bundle |
| `VariationBuilder.tsx` | Shown when `has_variation = true` | Must be hidden when item_type = Bundle (bundles are not varianted) |
| `ItemsListPage.tsx` | No bundle type differentiation | Add Bundle badge on list rows where `item_type.name === "Bundle"` |
| `api/base_types/items.ts` | No bundle types | Add `BundleComponentRead`, `BundleRead`, `BundleATPRead`, etc. |
| `api/base/items.ts` | No bundle API calls | Add 6 bundle API functions |

### 1.2 Warehouse Module

| Surface | Current State | Required Change |
|---------|--------------|-----------------|
| `InventoryLevelsPage.tsx` | Shows only direct `inventory_levels` rows | Add bundle rows with computed virtual ATP + expandable component breakdown |
| `InventoryMovementsPage.tsx` | No bundle awareness | When item_type = Bundle is selected, show BOM preview + confirmation warning |

### 1.3 No New Routes Required

All bundle UI is embedded within existing pages. The route table in `App.tsx` is unchanged.

---

## 2. Design Principles

These principles apply specifically to all bundle UI components:

1. **Zero surprise**: bundle mode is clearly signalled — "Bundle" badge, "Virtual" stock label,
   "Bundle Components" tab heading — the user always knows they're working with a computed entity.
2. **Fail loudly on partial state**: if the BOM is empty or only partially saved, show a
   persistent amber callout: "This bundle has no components — ATP will always be 0."
3. **Component-first editing**: BOM components are managed via individual API calls, not a
   bulk payload. The form auto-saves each add/remove/update action; no "Save" button needed on the
   BOM tab — each action shows an inline loading state and success/error toast.
4. **Create-first, then edit BOM**: Bundle Components tab is only active in edit mode.
   On create, show a read-only placeholder after the item_type selection so the user
   understands the next step.
5. **Shared stock visibility**: On the BOM editor, each component row shows that item's current
   ATP next to the qty-per-bundle input — giving immediate feedback on whether the bundle is
   constrained by a particular component.

---

## 3. TypeScript Types

**File:** `frontend/src/api/base_types/items.ts` — extend existing file

### 3.1 New types to add

```typescript
/* ------------------------------------------------------------------
 * Bundle / BOM types (mirrors backend ItemBundleComponent + BundleRead)
 * ------------------------------------------------------------------ */

/** One component line in a Bundle BOM */
export interface BundleComponentRead {
  id: number;
  bundle_item_id: number;
  component_item_id: number;
  component_master_sku: string;     // joined from Item.master_sku
  component_item_name: string;      // joined from Item.item_name
  component_atp: number;            // current ATP of the component (joined from inventory)
  quantity_per_bundle: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** Full BOM + computed ATP for a bundle item */
export interface BundleRead {
  bundle_item_id: number;
  bundle_master_sku: string;
  bundle_item_name: string;
  components: BundleComponentRead[];
  bundle_atp: number;               // MIN(floor(component_atp / qty_per_bundle))
  limiting_component_id: number | null; // component_item_id of the constraint
}

/** Payload to add a new component to a bundle BOM */
export interface BundleComponentCreate {
  component_item_id: number;
  quantity_per_bundle: number;
}

/** Payload to update an existing component's quantity */
export interface BundleComponentUpdate {
  quantity_per_bundle: number;
  is_active?: boolean;
}

/** Slim ATP-only response for the ATP chip */
export interface BundleATPRead {
  bundle_item_id: number;
  bundle_atp: number;
  limiting_component_id: number | null;
}

/** A slim bundle summary used for "memberships" (which bundles contain this item) */
export interface BundleMembershipRead {
  bundle_item_id: number;
  bundle_master_sku: string;
  bundle_item_name: string;
  quantity_in_bundle: number;
  bundle_atp: number;
}
```

---

## 4. API Functions

**File:** `frontend/src/api/base/items.ts` — extend existing file

### 4.1 New functions to add

```typescript
/* ------------------------------------------------------------------
 * Bundle / BOM API functions
 * ------------------------------------------------------------------ */

/** Get the full BOM for a bundle item (components + computed ATP) */
export async function getBundleBOM(itemId: number): Promise<BundleRead>

/** Get only the computed ATP for a bundle (lightweight) */
export async function getBundleATP(itemId: number): Promise<BundleATPRead>

/** Add a component to a bundle's BOM */
export async function addBundleComponent(
  bundleItemId: number,
  data: BundleComponentCreate,
): Promise<BundleComponentRead>

/** Update a BOM component's quantity_per_bundle or active flag */
export async function updateBundleComponent(
  bundleItemId: number,
  componentId: number,
  data: BundleComponentUpdate,
): Promise<BundleComponentRead>

/** Remove a component from a bundle's BOM */
export async function removeBundleComponent(
  bundleItemId: number,
  componentId: number,
): Promise<void>

/**
 * List all bundles that contain a given item as a component.
 * Used in the component row hover-tooltip / memberships panel.
 */
export async function getItemBundleMemberships(
  itemId: number,
): Promise<BundleMembershipRead[]>
```

---

## 5. Modified: `ItemFormPage.tsx`

This is the most significant change. The form gains a **conditional tab system** and a
**Bundle Components tab** that replaces the Variations section when `item_type = "Bundle"`.

### 5.1 Tab logic

```
item_type selection
    │
    ├─ item_type_name === "Bundle"
    │     → Show tabs: [ General  |  Bundle Components ]
    │     → Hide "Has Variation" checkbox
    │     → Hide VariationBuilder
    │
    └─ Any other item_type (or none)
          → No tabs shown (current single-card layout unchanged)
          → Show "Has Variation" + VariationBuilder as today
```

How to detect "Bundle" from the form: `item_type_id` is a number in the form,
but we need to know the name. We look it up from `options.itemTypes`:

```typescript
const watchedTypeId = watch('item_type_id');
const isBundle = useMemo(
  () => options.itemTypes.find(t => t.id === Number(watchedTypeId))?.name === 'Bundle',
  [watchedTypeId, options.itemTypes]
);
```

### 5.2 Tab state

Add `activeTab: 'general' | 'bundle'` state (default `'general'`).
Reset to `'general'` when `isBundle` changes from true to false.

### 5.3 New Sub-components (all under `pages/items/`)

| File | Purpose |
|------|---------|
| `BundleComponentsTab.tsx` | Full BOM editor panel — component list, add/remove/update actions |
| `BundleComponentsTab.css` | CSS for the BOM editor (no inline styles per ground rule #8) |
| `AddComponentModal.tsx` | Search-and-add dialog for selecting a component item |
| `BundleMembershipsBadge.tsx` | Hoverable chip on ItemsListPage showing which bundles reference this item |

### 5.4 Layout — Tab Pills (General card header)

```
┌────────────────────────────────────────────────────────────────────┐
│  ┌──────────────┐  ┌───────────────────────────┐                  │
│  │  General     │  │  Bundle Components  [2]   │  ← tab + count  │
│  └──────────────┘  └───────────────────────────┘                  │
│  ─────────────────────────────────────────────────────────────────│
│  [ form fields or BOM editor depending on active tab ]            │
└────────────────────────────────────────────────────────────────────┘
```

Tab pills use the same visual style as `ItemsListPage` status tabs — an underline
indicator bar, `text-primary` for the active tab, `text-text-secondary` for inactive.
Active tab bottom border: `border-b-2 border-primary`.

### 5.5 Create Mode — Bundle Components placeholder

When creating a new bundle item (`!isEdit && isBundle`), the Bundle Components tab is
disabled and shows a placeholder card instead of the BOM editor:

```
┌────────────────────────────────────────────────────────┐
│  [i]  Save this item first to manage bundle components │
│       You can add components after the item is created │
└────────────────────────────────────────────────────────┘
```

After successful create, navigate to `/catalog/items/:id/edit` so the BOM tab
becomes immediately editable.

### 5.6 BOM Editor Layout — `BundleComponentsTab.tsx`

**Props:**
```typescript
interface BundleComponentsTabProps {
  bundleItemId: number;  // only passed in edit mode
}
```

**State inside BundleComponentsTab:**
- `bom: BundleRead | null` — full BOM from `getBundleBOM()`
- `loading: boolean`
- `error: string | null`
- `showAddModal: boolean`
- `actionLoading: number | null` — component ID currently being updated/removed

**Layout:**

```
┌────────────────────────────────────────────────────────────────────┐
│  Bundle Components                       [+ Add Component]         │
│                                                                     │
│  ┌─ Empty state (no components) ─────────────────────────────────┐ │
│  │  [!] This bundle has no components.                            │ │
│  │      Virtual ATP will always be 0 until components are added.  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ─── or if components exist ──────────────────────────────────────  │
│                                                                     │
│  Virtual ATP   7 units   ← green if >10, amber if ≤10, red if 0    │
│  Limiting SKU  T-SHIRT-BLUE-M   ← shown when limiting_component    │
│                                                                     │
│  ┌───────────────────┬────────────┬────────┬──────────┬──────────┐ │
│  │ Component SKU     │ Item Name  │ On ATP │ Qty/Bundle│ Actions  │ │
│  ├───────────────────┼────────────┼────────┼──────────┼──────────┤ │
│  │ T-SHIRT-RED-M     │ T-Shirt    │  13    │  [1]  ↑↓ │ [Remove] │ │
│  │ T-SHIRT-BLUE-M ★ │ T-Shirt    │   7    │  [1]  ↑↓ │ [Remove] │ │
│  │ T-SHIRT-WHT-M     │ T-Shirt    │  20    │  [1]  ↑↓ │ [Remove] │ │
│  └───────────────────┴────────────┴────────┴──────────┴──────────┘ │
│                                                                     │
│  ★ = limiting component (lowest ATP / qty_per_bundle ratio)         │
└────────────────────────────────────────────────────────────────────┘
```

**Column detail:**
- **Component SKU**: `master_sku` chip (monospace, `bg-background` pill)
- **Item Name**: plain text
- **On ATP**: colour-coded number — green `>10`, amber `≤10`, red `0`
- **Qty/Bundle**: inline stepper (–  N  +) — each click calls `updateBundleComponent()`
  immediately; shows spinner on the row while inflight
- **Actions**: red "Remove" link — shows confirm popconfirm inline, calls
  `removeBundleComponent()` on confirm; shows spinner while inflight
- **Limiting star (★)**: amber star icon on the row where this component
  is the constraint: `component_item_id === bom.limiting_component_id`

### 5.7 Add Component Modal — `AddComponentModal.tsx`

**Trigger:** "+ Add Component" button in BundleComponentsTab
**Pattern:** slide-over style dialog (same pattern as warehouse modals)

```
┌────────────────────────────────────────────────────┐
│ Add Component to Bundle                            │
│                                                    │
│ Search SKU or Item Name                            │
│ [____________________________________]  ← debounced│
│                                                    │
│ ┌──────────────────────────────────────────────┐   │
│ │ ● T-SHIRT-RED-M   T-Shirt Red Medium   ATP:13│   │
│ │ ○ T-SHIRT-BLUE-M  T-Shirt Blue Medium  ATP:7 │   │
│ │ ○ JACKET-BLK-L    Jacket Black Large   ATP:25│   │
│ └──────────────────────────────────────────────┘   │
│                                                    │
│ Quantity per bundle    [___1___]   ← min=1         │
│                                                    │
│ [Cancel]                         [Add to Bundle]   │
└────────────────────────────────────────────────────┘
```

**Validation:**
- `component_item_id` must be selected (highlight empty state with error)
- `quantity_per_bundle` must be ≥ 1 (integer only)
- Component must not already be in the BOM (disable already-added items in the list)
- Bundles cannot be nested — filter out items where `item_type.name === "Bundle"` from search results

**API call on confirm:**
```typescript
await addBundleComponent(bundleItemId, {
  component_item_id: selected.item_id,
  quantity_per_bundle: qty,
});
```
On success: close modal, reload BOM, show success toast.
On error: keep modal open, show inline error.

---

## 6. Modified: `ItemsListPage.tsx`

### 6.1 Bundle Badge on list rows

When a row's `item_type?.name === 'Bundle'`, display a small "Bundle" badge
next to the item name in the Name column:

```
T-Shirt 3-Pack  [Bundle]  ← indigo badge
T-Shirt Red M             ← normal
```

Badge class: `bg-info-bg text-info-text text-[10px] font-semibold px-1.5 py-0.5 rounded`

### 6.2 Component Membership tooltip

When a row's item type is NOT Bundle, and it appears as a component in ≥1 bundles,
show a subtle chip: `[In 2 bundles]` — hoverable, showing bundle names on hover.

This is a page-specific tooltip component: `pages/items/BundleMembershipsBadge.tsx`.
It loads memberships lazily on hover via `getItemBundleMemberships(itemId)` — no pre-fetch.

---

## 7. Modified: `InventoryLevelsPage.tsx`

### 7.1 Bundle rows in the stock matrix

The stock matrix currently only shows rows from `inventory_levels`.
Bundle items have no `inventory_levels` rows — their stock is virtual.
Two display modes are proposed:

**Mode A (default):** Show bundle rows interleaved with component rows — bundle rows
are clearly differentiated with a "Bundle" badge and a "Virtual" location label.

**Mode B (toggle):** A "Show Bundles" toggle on the page. When on, bundle ATP rows
are fetched and prepended to the list. When off, only physical inventory rows are shown.

**Decision: implement Mode B** — the toggle prevents cluttering the stock matrix for
warehouses with many bundles. The toggle state persists in `localStorage`.

### 7.2 Toggle state & data loading

Add to page state:
```typescript
const [showBundles, setShowBundles] = useState<boolean>(
  () => localStorage.getItem('inv_show_bundles') === 'true'
);
const [bundles, setBundles] = useState<BundleRead[]>([]);
const [bundlesLoading, setBundlesLoading] = useState(false);
```

When `showBundles = true` and a warehouse is selected:
1. `GET /items?item_type_name=Bundle&page_size=100` — all bundle items
2. For each bundle item, `GET /items/{id}/bundle/atp` — parallel, `Promise.allSettled`
3. Merge into `bundles` state

### 7.3 Bundle row layout

```
┌──────────────────────┬──────────────┬──────────┬────────┬───────────────┐
│ Item                 │ Location     │  Qty ATP │ Reorder│ Status        │
├──────────────────────┼──────────────┼──────────┼────────┼───────────────┤
│ ▶ 3-Pack Bundle [B] │ — Virtual —  │    7     │   —    │ 🟡 Low        │ ← toggle expand
│   ├ T-SHIRT-RED-M   │ S1-Z2-B4     │   13     │   10   │ ✅ OK          │
│   ├ T-SHIRT-BLUE-M★ │ S1-Z2-B5     │    7     │   10   │ 🟡 Low        │
│   └ T-SHIRT-WHT-M   │ S1-Z2-B6     │   20     │   10   │ ✅ OK          │
├──────────────────────┼──────────────┼──────────┼────────┼───────────────┤
│ T-Shirt Red M        │ S1-Z2-B4     │   13     │   10   │ ✅ OK          │
└──────────────────────┴──────────────┴──────────┴────────┴───────────────┘
```

**Bundle row differentiation:**
- Row background: `bg-info-bg/20` (very light blue tint)
- Location column: italic "— Virtual —" in `text-text-secondary`
- Reorder column: `—` (bundles have no reorder point)
- Expand/collapse: chevron icon rotates on expand; default collapsed
- ★ marks the limiting component (amber star, same as BOM editor)

**Bundle status derivation (frontend-side):**
```typescript
function bundleStatusFromATP(atp: number, components: BundleComponentRead[]): StockStatus {
  if (atp === 0) return 'out_of_stock';
  const minComponentStatus = components.reduce((worst, c) => {
    // use same threshold logic: critical if c.component_atp <= safety_stock (if known)
    if (c.component_atp === 0) return 'out_of_stock';
    // If we don't know thresholds, derive from the limiting signal
    return worst;
  }, 'ok' as StockStatus);
  return minComponentStatus;
}
```
In practice: bundle ATP is loaded from `BundleRead.bundle_atp`. Status badge is:
- `0` → `out_of_stock`
- `≤10` → `low` (hardcoded floor; will be replaced when threshold API is available)
- else → `ok`

### 7.4 "Show Bundles" toggle layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ Inventory Levels                                                       │
│ Warehouse: [Select ▾]   [Search SKU/Name]      [◉ Show Bundles]  ←NEW│
└───────────────────────────────────────────────────────────────────────┘
```

Toggle uses the same `role="switch"` pill pattern from `ItemFormPage`.

---

## 8. Modified: `InventoryMovementsPage.tsx`

### 8.1 Bundle awareness in "Record Movement" modal

When the selected item has `item_type.name === "Bundle"`:

1. Show an amber callout below the item selector:
   ```
   ┌──────────────────────────────────────────────────────────────────┐
   │  [!] This is a bundle SKU. Recording an outbound movement will   │
   │      deduct stock from 3 components via the bundle service.      │
   │      Components: T-SHIRT-RED-M × 1, T-SHIRT-BLUE-M × 1, ...    │
   └──────────────────────────────────────────────────────────────────┘
   ```

2. Load the BOM via `getBundleBOM(itemId)` when the bundle item is selected.
   Show a loading skeleton while fetching.

3. The **Transactions section** becomes read-only for bundles — location and
   direction inputs are greyed out with a tooltip: "Component locations are
   determined automatically by the bundle fulfillment service."

4. On submit, the modal calls `POST /warehouse/fulfill/bundle` instead of
   `POST /warehouse/movements` — this is handled transparently; the modal
   detects the item type and routes to the correct endpoint.

---

## 9. File Structure

```
frontend/src/
├── api/
│   ├── base_types/
│   │   └── items.ts              ← MODIFY: add bundle types (§3)
│   └── base/
│       └── items.ts              ← MODIFY: add bundle API functions (§4)
│
├── pages/
│   ├── items/
│   │   ├── ItemFormPage.tsx      ← MODIFY: add tab system + isBundle logic (§5)
│   │   ├── ItemsListPage.tsx     ← MODIFY: add Bundle badge + membership chip (§6)
│   │   ├── BundleComponentsTab.tsx    ← NEW: BOM editor tab panel
│   │   ├── BundleComponentsTab.css    ← NEW: BOM editor styles
│   │   ├── AddComponentModal.tsx      ← NEW: search + add component dialog
│   │   └── BundleMembershipsBadge.tsx ← NEW: "In 2 bundles" hover chip
│   │
│   └── warehouse/
│       ├── InventoryLevelsPage.tsx    ← MODIFY: bundle rows + toggle (§7)
│       └── InventoryMovementsPage.tsx ← MODIFY: bundle awareness (§8)
│
└── index.css                     ← MODIFY: add .bundle-row-* CSS classes
```

> **Ground rule compliance:**
> - All new files are page-specific and live inside the relevant `pages/` subfolder.
> - No bundle-specific files in `components/` — bundle UI is not cross-page shared.
> - All new CSS goes into either `BundleComponentsTab.css` or `index.css` for global tokens.
> - No inline styles.

---

## 10. CSS Additions — `index.css`

```css
/* ==========================================================================
   Bundle SKU — Row & Badge Styles
   ========================================================================== */

.bundle-row {
  background-color: color-mix(in srgb, var(--color-info-bg) 20%, transparent);
}

.bundle-row-component {
  background-color: color-mix(in srgb, var(--color-info-bg) 8%, transparent);
  border-left: 2px solid var(--color-info);
  padding-left: calc(1rem + 16px);  /* indent under bundle parent */
}

.bundle-badge {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 1px 6px;
  border-radius: 4px;
  background-color: var(--color-info-bg);
  color: var(--color-info-text);
  font-family: var(--font-sans);
}

.bundle-limiting-star {
  color: var(--color-warning);
  font-size: 14px;
  line-height: 1;
}

.bundle-virtual-location {
  font-style: italic;
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
}
```

---

## 11. Validation Rules

### 11.1 AddComponentModal

| Field | Rule | Error message |
|-------|------|---------------|
| `component_item_id` | Required (must select from list) | "Please select a component item" |
| `component_item_id` | Must not already be in BOM | Item shows as disabled in search results |
| `component_item_id` | Must not be a Bundle type | Filtered out from search; shown as "(Bundle SKUs cannot be nested)" tooltip |
| `quantity_per_bundle` | Required, integer, min=1, max=999 | "Quantity must be between 1 and 999" |

### 11.2 BOM inline stepper (quantity update)

- Decrement disabled when `quantity_per_bundle === 1` (cannot go below 1)
- Each click immediately calls `updateBundleComponent()` — debounced 300ms to prevent rapid firing
- If API returns error, revert the displayed quantity and show inline error toast

### 11.3 Remove component

- Inline popconfirm (not a modal dialog) appears on "Remove" click:
  ```
  Remove T-SHIRT-RED-M from this bundle?  [Cancel] [Remove]
  ```
- On confirm: call `removeBundleComponent()`, remove row from local state optimistically,
  show error toast and restore row if API fails.

---

## 12. State Management Summary

### `BundleComponentsTab` local state

```typescript
interface BundleComponentsTabState {
  bom: BundleRead | null;
  loading: boolean;
  error: string | null;
  showAddModal: boolean;
  // Per-row action loading — keyed by component.id
  actionLoading: Record<number, 'updating' | 'removing'>;
  // Inline quantity edit value before API call
  pendingQty: Record<number, number>;
}
```

### `ItemFormPage` additions

```typescript
const [activeTab, setActiveTab] = useState<'general' | 'bundle'>('general');
const isBundle: boolean;   // derived, see §5.1
```

Whenever `isBundle` flips to `false`, reset `activeTab` to `'general'`.

---

## 13. Implementation Order

### Phase 1 — Types & API Layer (v0.5.20)
1. Extend `frontend/src/api/base_types/items.ts` with bundle types (§3)
2. Extend `frontend/src/api/base/items.ts` with 6 bundle API functions (§4)
3. Add CSS bundle classes to `index.css` (§10)
4. Smoke test: call `getBundleBOM(id)` against Swagger and confirm shape matches

### Phase 2 — ItemFormPage Bundle Tab (v0.5.20)
1. Create `pages/items/AddComponentModal.tsx` (§5.7)
2. Create `pages/items/BundleComponentsTab.tsx` + `BundleComponentsTab.css` (§5.6)
3. Modify `ItemFormPage.tsx`:
   - Add `isBundle` detection logic (§5.1)
   - Add `activeTab` state (§5.2)
   - Add tab pill UI (§5.4)
   - Add create-mode placeholder (§5.5)
   - Render `<BundleComponentsTab>` when `activeTab === 'bundle' && isEdit` (§5.6)
   - Hide `has_variation` checkbox and VariationBuilder when `isBundle` (§5.3)
4. On create save: redirect to edit path so Bundle tab is immediately available
5. Manual test: create Bundle item → edit → add components → verify BOM displays

### Phase 3 — ItemsListPage Badge (v0.5.21)
1. Add Bundle badge to item name column (§6.1)
2. Create `pages/items/BundleMembershipsBadge.tsx` (§6.2)
3. Wire lazy-load membership fetch on hover

### Phase 4 — InventoryLevelsPage Bundle Rows (v0.5.21)
1. Add `showBundles` toggle to page header (§7.4)
2. Add bundle data loading logic (§7.2)
3. Implement bundle row rendering with expand/collapse (§7.3)
4. Add `bundle-row` / `bundle-row-component` CSS classes (§10)
5. End-to-end test: toggle on, verify bundle rows appear with correct ATP

### Phase 5 — InventoryMovementsPage Bundle Awareness (v0.5.22)
1. Detect bundle item type in "Record Movement" modal (§8.1)
2. Load BOM preview on item select (§8.1)
3. Wire `POST /warehouse/fulfill/bundle` endpoint on submit (§8.1)
4. Update `docs/official_documentation/web-api.md` with new endpoints
5. Update `docs/official_documentation/frontend-development-progress.md`

---

## 14. Backend API Readiness Matrix (Frontend dependency)

| # | Backend endpoint | Backend plan ref | Required for |
|---|-----------------|-----------------|-------------|
| 1 | `GET /items/{id}/bundle` | §6 in backend plan | `BundleComponentsTab`, Levels expand |
| 2 | `GET /items/{id}/bundle/atp` | §6 | ATP chip, Levels bundle row |
| 3 | `POST /items/{id}/bundle/components` | §6 | `AddComponentModal` |
| 4 | `PUT /items/{id}/bundle/components/{cid}` | §6 | BOM inline stepper |
| 5 | `DELETE /items/{id}/bundle/components/{cid}` | §6 | Remove component |
| 6 | `GET /items/{id}/bundle/memberships` | §6 | `BundleMembershipsBadge` |
| 7 | `POST /warehouse/fulfill/bundle` | §6 | Movements modal bundle submit |
| 8 | `GET /items?item_type_name=Bundle` | Existing `/items` with filter | Levels bundle list |

> **Prerequisite:** All Phase 1–3 backend work (backend plan §9) must be deployed before
> any frontend bundle features can be end-to-end tested.

---

## 15. Verification Checklist

| # | Test | Expected |
|---|------|---------|
| 1 | Create item with type "Bundle" | Tabs appear; "Has Variation" is hidden |
| 2 | Try to open Bundle tab on create | Placeholder shown: "Save item first" |
| 3 | Save bundle item and return to edit | Bundle Components tab is now active |
| 4 | Open Add Component modal | Search works; existing BOM items disabled; Bundle items excluded |
| 5 | Add 3 components | BOM table shows 3 rows; Virtual ATP chip updates |
| 6 | Click + on qty stepper | API called; qty updates; ATP chip recalculates |
| 7 | Click – when qty=1 | Button disabled; no API call |
| 8 | Remove component with popconfirm | Row disappears; ATP recalculates |
| 9 | Remove component — API fails | Row restores; error toast shown |
| 10 | ItemsListPage — Bundle row | "Bundle" badge visible on bundle items |
| 11 | ItemsListPage — Component row hover | "In 2 bundles" chip appears; hover shows names |
| 12 | InventoryLevelsPage — Show Bundles OFF | No bundle rows in table |
| 13 | InventoryLevelsPage — Show Bundles ON | Bundle rows appear with blue tint + Virtual location |
| 14 | Expand bundle row | Component breakdown visible with ★ on limiting SKU |
| 15 | Toggle Show Bundles OFF and refresh | Persists OFF via localStorage |
| 16 | Record Movement — select Bundle item | Amber callout + BOM preview loads |
| 17 | Record Movement — Bundle submit | `POST /warehouse/fulfill/bundle` called |

---

## 16. Changelog

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-04 | Initial plan created | Frontend implementation plan for Bundle SKU BOM management, aligned to backend plan §05 |
