"""
Drop the product_number column from the items table in woms_db.

WHY: The product_number field (Excel "No." column) is not used in the application.
     It was originally imported from the item master Excel file but serves no purpose
     in the WOMS system. Removing it simplifies the Item model.

WHAT: ALTER TABLE items DROP COLUMN product_number
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from sqlalchemy import text


async def main():
    from app.database import engine

    # Check if column exists before dropping
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'items' AND column_name = 'product_number'"
        ))
        row = result.fetchone()

        if not row:
            print("[OK] Column 'product_number' does not exist in 'items' table. Nothing to do.")
            await engine.dispose()
            return

    # Drop the column
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE items DROP COLUMN product_number"))
        print("[OK] Dropped column 'product_number' from 'items' table.")

    # Verify
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'items' AND column_name = 'product_number'"
        ))
        row = result.fetchone()
        if row:
            print("[WARN] Column still exists after DROP!")
        else:
            print("[OK] Verified: column 'product_number' no longer exists.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
