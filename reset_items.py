"""
Reset all item-related tables in woms_db.

WHY: User requested clearing all item data and resetting auto-increment sequences
     to 1 so items can be re-imported fresh.

WHAT this script does:
1. DELETEs all rows from: items_history, items, status, item_type, category, brand, base_uom
2. Uses setval() to reset all serial sequences back to 1
3. Deletes in FK-safe order (children before parents)
4. Re-seeds item_type and base_uom (since they're needed by the application)
5. Verifies results by querying row counts and current sequence values

Tables affected (in deletion order):
- items_history  (FK -> items.item_id)
- items          (FK -> base_uom, brand, item_type, category; self-ref parent_id)
- status         (standalone lookup)
- item_type      (referenced by items.item_type_id) -- re-seeded after delete
- category       (referenced by items.category_id)
- brand          (referenced by items.brand_id)
- base_uom       (referenced by items.uom_id) -- re-seeded after delete

NOTE: Uses DELETE + setval() instead of TRUNCATE RESTART IDENTITY because the
      database user (woms_user) does not own the sequences -- RESTART IDENTITY
      requires sequence ownership while setval() only needs USAGE privilege.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import text


async def main():
    from app.config import settings
    from app.database import engine, async_session_maker

    # Deletion order: children first, then parents (respects FK constraints)
    delete_order = [
        "items_history",   # FK -> items
        "items",           # FK -> lookups; self-ref parent_id (children deleted first via CASCADE or same table)
        "status",
        "item_type",
        "category",
        "brand",
        "base_uom",
    ]

    # Sequences to reset (table_seq_name, display_label)
    sequences = [
        ("items_item_id_seq", "items.item_id"),
        ("items_history_history_id_seq", "items_history.history_id"),
        ("status_status_id_seq", "status.status_id"),
        ("item_type_item_type_id_seq", "item_type.item_type_id"),
        ("category_category_id_seq", "category.category_id"),
        ("brand_brand_id_seq", "brand.brand_id"),
        ("base_uom_uom_id_seq", "base_uom.uom_id"),
    ]

    print("=" * 60)
    print("WOMS Item Data Reset")
    print("=" * 60)
    print(f"Database: {settings.database_name}")
    print(f"Tables to clear: {', '.join(delete_order)}")
    print()

    # --- Step 1: Show current row counts ---
    print("--- Current row counts ---")
    async with engine.connect() as conn:
        for t in delete_order:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
            count = result.scalar()
            print(f"  {t}: {count} rows")

    # --- Step 2: DELETE all rows (FK-safe order) ---
    print("\n--- Deleting all rows ---")
    async with engine.begin() as conn:
        for t in delete_order:
            result = await conn.execute(text(f"DELETE FROM {t}"))
            print(f"  [OK] DELETE FROM {t} ({result.rowcount} rows removed)")

    # --- Step 3: Reset sequences to 1 ---
    print("\n--- Resetting sequences ---")
    async with engine.begin() as conn:
        for seq_name, label in sequences:
            try:
                # setval(seq, 1, false) means next nextval() returns 1
                await conn.execute(text(f"SELECT setval('{seq_name}', 1, false)"))
                print(f"  [OK] {label} sequence reset (next ID = 1)")
            except Exception as e:
                print(f"  [WARN] {label}: {e}")

    # --- Step 4: Re-seed item_type and base_uom ---
    print("\n--- Re-seeding lookup tables (item_type, base_uom) ---")
    from app.models.seed import _ITEM_TYPES, _BASE_UOMS

    async with async_session_maker() as session:
        await session.execute(
            text("INSERT INTO item_type (item_type_name) VALUES (:name) ON CONFLICT (item_type_name) DO NOTHING"),
            [{"name": t} for t in _ITEM_TYPES],
        )
        await session.execute(
            text("INSERT INTO base_uom (uom_name) VALUES (:name) ON CONFLICT (uom_name) DO NOTHING"),
            [{"name": u} for u in _BASE_UOMS],
        )
        await session.commit()
        print(f"  [OK] item_type: {len(_ITEM_TYPES)} rows seeded")
        print(f"  [OK] base_uom: {len(_BASE_UOMS)} rows seeded")

    # --- Step 5: Verify results ---
    print("\n--- Verification ---")
    async with engine.connect() as conn:
        for t in delete_order:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
            count = result.scalar()
            print(f"  {t}: {count} rows")

        print("\n--- Sequence values (next insert ID) ---")
        for seq_name, label in sequences:
            try:
                result = await conn.execute(text(f"SELECT last_value, is_called FROM {seq_name}"))
                row = result.fetchone()
                if row:
                    last_val, is_called = row
                    next_id = last_val + 1 if is_called else last_val
                    print(f"  {label}: next ID = {next_id}")
            except Exception as e:
                print(f"  {label}: sequence check failed ({e})")

    await engine.dispose()
    print("\n" + "=" * 60)
    print("[OK] Item data reset complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
