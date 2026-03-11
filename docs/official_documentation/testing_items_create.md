# Manual Testing Guide: Create Item Endpoint (v0.5.10)

**Feature:** POST `/api/v1/items` — Create Item
**Frontend:** `/catalog/items/new`
**Tested against:** PRE-ALPHA v0.5.10
**Date:** 2026-03-03

---

## Prerequisites

- Backend running at `http://localhost:8000`
- Frontend running at `http://localhost:5173`
- Logged in as an admin user (e.g., `admin@admin.com / Admin123`)
- At least one record exists in: Categories, Brands, UOMs, Item Types (seeded by default)

---

## Section 1 — Frontend Form Validation

### TC-F01: Required field — Item Name

1. Navigate to `/catalog/items/new`
2. Leave **Item Name** blank
3. Fill in **Master SKU** with `TEST-F01`
4. Click **Save**
5. **Expected:** Red validation message under Item Name: _"Item name is required"_. Form does not submit.

---

### TC-F02: Required field — Master SKU

1. Navigate to `/catalog/items/new`
2. Fill in **Item Name** with `Test Item`
3. Leave **Master SKU** blank
4. Click **Save**
5. **Expected:** Red validation message: _"Master SKU is required"_. Form does not submit.

---

### TC-F03: Master SKU — no spaces allowed

1. Navigate to `/catalog/items/new`
2. Fill in **Item Name** with `Space Test`
3. Type `TEST SKU 001` (with spaces) in **Master SKU**
4. Click **Save**
5. **Expected:** Validation message: _"Master SKU must not contain spaces"_. Form does not submit.

---

### TC-F04: Master SKU — max 100 characters

1. Navigate to `/catalog/items/new`
2. Fill in **Item Name** with `Long SKU Test`
3. Paste 101 characters into **Master SKU**: `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` (101 A's)
4. Click **Save**
5. **Expected:** Validation message: _"Max 100 characters"_. Form does not submit.

---

### TC-F05: Item Name — max 500 characters

1. Navigate to `/catalog/items/new`
2. Paste 501 characters into **Item Name**
3. Fill in **Master SKU** with `TEST-F05`
4. Click **Save**
5. **Expected:** Validation message: _"Max 500 characters"_. Form does not submit.

---

### TC-F06: SKU Name — max 500 characters

1. Navigate to `/catalog/items/new`
2. Fill in **Item Name** with `SKU Name Test`
3. Fill in **Master SKU** with `TEST-F06`
4. Paste 501 characters into **SKU Name**
5. Click **Save**
6. **Expected:** Validation message: _"Max 500 characters"_. Form does not submit.

---

### TC-F07: Status toggle — defaults to Active

1. Navigate to `/catalog/items/new`
2. Observe the **Status** toggle before interacting with it.
3. **Expected:** Toggle is in the **ON** (blue/primary) position. Label reads **"Active"**.

---

### TC-F08: Status toggle — toggle to Inactive

1. Navigate to `/catalog/items/new`
2. Click the **Status** toggle once.
3. **Expected:** Toggle moves to the **OFF** (gray) position. Label reads **"Inactive"**.
4. Click the toggle again.
5. **Expected:** Toggle returns to ON. Label reads **"Active"**.

---

### TC-F09: Category / Brand / UOM / Item Type — "Select" placeholder

1. Navigate to `/catalog/items/new`
2. Observe all four dropdown fields.
3. **Expected:** Each dropdown shows **"Select"** as the first/default option (not "Category", "Brand", etc.)

---

### TC-F10: Submit button disabled while submitting

1. Navigate to `/catalog/items/new`
2. Fill in required fields
3. Click **Save** and observe immediately
4. **Expected:** Button shows **"Saving..."** and is disabled (greyed out, `not-allowed` cursor) until the API responds.

---

## Section 2 — Successful Creation (Happy Path)

### TC-H01: Minimal create (required fields only)

1. Navigate to `/catalog/items/new`
2. Fill in:
   - Item Name: `Minimal Test Item`
   - Master SKU: `TEST-MINIMAL-001`
3. Leave all other fields blank. Status toggle remains Active.
4. Click **Save**
5. **Expected:**
   - Redirected to `/catalog/items`
   - `TEST-MINIMAL-001` appears in the items list
   - Status badge shows **Active**

---

### TC-H02: Full create (all fields)

1. Navigate to `/catalog/items/new`
2. Fill in all fields:
   - Item Name: `Full Test Item`
   - Master SKU: `TEST-FULL-001`
   - SKU Name: `Color Edition`
   - Description: `A comprehensive test item`
   - Category, Brand, Base UOM, Item Type: pick any available options
   - Status: leave as Active
3. Upload a product image (JPG or PNG under 5 MB)
4. Click **Save**
5. **Expected:**
   - Redirected to `/catalog/items`
   - Item appears with correct Category, Item Type, UOM columns
   - Thumbnail image displayed in list

---

### TC-H03: Create as Inactive

1. Navigate to `/catalog/items/new`
2. Fill in:
   - Item Name: `Inactive Test Item`
   - Master SKU: `TEST-INACTIVE-001`
3. Toggle **Status** to **Inactive**
4. Click **Save**
5. **Expected:**
   - Item appears in list under the **Unpublished** tab
   - Status badge shows **Inactive**

---

### TC-H04: Edit mode — SKU is read-only

1. Navigate to an existing item's edit page (`/catalog/items/{id}/edit`)
2. Observe the **Master SKU** field.
3. **Expected:** Field is read-only (grayed out) with helper text _"SKU cannot be changed after creation"_.

---

## Section 3 — Backend Conflict Handling

### TC-B01: Duplicate Master SKU → 409

1. Create an item with Master SKU `TEST-DUP-001` (via form or API — see TC-H01)
2. Navigate to `/catalog/items/new` again
3. Fill in:
   - Item Name: `Duplicate SKU Attempt`
   - Master SKU: `TEST-DUP-001`
4. Click **Save**
5. **Expected:** Error banner appears at top of form: _"An item with Master SKU 'TEST-DUP-001' already exists."_ Form remains open.

---

### TC-B02: Duplicate Master SKU via API (using curl or Postman)

```bash
# First create
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"item_name": "First", "master_sku": "TEST-API-DUP"}'
# Expected: 201 Created

# Second create (same SKU)
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"item_name": "Second", "master_sku": "TEST-API-DUP"}'
# Expected: 409 Conflict
# Body: {"detail": "An item with Master SKU 'TEST-API-DUP' already exists."}
```

---

## Section 4 — Authentication

### TC-A01: No token → 401

```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{"item_name": "No Auth", "master_sku": "TEST-NOAUTH"}'
# Expected: 401 Unauthorized
```

### TC-A02: Invalid token → 401

```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid.jwt.token" \
  -d '{"item_name": "Bad Token", "master_sku": "TEST-BADTOKEN"}'
# Expected: 401 Unauthorized
```

---

## Section 5 — Image Upload

### TC-I01: Upload a valid image

1. Navigate to `/catalog/items/new`
2. Click the dashed image upload area
3. Select a JPG or PNG file under 5 MB
4. **Expected:** Upload spinner appears briefly → image preview replaces the placeholder icon.

### TC-I02: Remove uploaded image

1. Complete TC-I01 above
2. Click the **"Remove image"** link beneath the upload area
3. **Expected:** Preview disappears. Upload area shows the `ImageIcon` placeholder again.

### TC-I03: Image persists after save

1. Upload an image, fill required fields, and save
2. Open the edit page for the created item
3. **Expected:** The uploaded image is still displayed.

---

## Section 6 — Automated Tests

Run the pytest integration suite:

```bash
cd backend
python -m pytest tests/test_items_create.py -v
```

**Expected output:** 15 tests, all passing.

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| TC-01 | Minimal create | 201 |
| TC-02 | All fields | 201, fields in response |
| TC-03 | is_active defaults True | is_active=true |
| TC-04 | is_active=false | is_active=false |
| TC-05 | Missing item_name | 422 |
| TC-06 | Missing master_sku | 422 |
| TC-07 | item_name > 500 chars | 422 |
| TC-08 | master_sku > 100 chars | 422 |
| TC-09 | Duplicate master_sku | 409 |
| TC-10 | No auth header | 401 |
| TC-11 | Invalid JWT | 401 |
| TC-12 | has_variation + variations_data | 201, data stored |
| TC-13 | Empty master_sku | 422 |
| TC-14 | Response body structure | All fields present |
| TC-15 | Timestamps set | created_at/updated_at not null |
