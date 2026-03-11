"""
Migration: Add is_active to items, remove status_id FK.

Usage:
    python migrate_is_active.py

Prompts for the postgres admin password (or any superuser/table-owner),
then applies:
  1. ALTER TABLE items ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE
  2. CREATE INDEX idx_items_is_active ON items (is_active)
  3. ALTER TABLE items DROP CONSTRAINT items_status_id_fkey
  4. ALTER TABLE items DROP COLUMN status_id
  5. GRANT woms_user ownership of the items table (so future DDL works)

Safe to delete after use.
"""

import getpass
import sys


def main():
    admin_user = input("DB admin username [postgres]: ").strip() or "postgres"
    admin_pass = getpass.getpass(f"Enter password for '{admin_user}': ")

    try:
        import psycopg
    except ImportError:
        print("[ERR] psycopg not installed -- run: pip install psycopg-binary")
        sys.exit(1)

    try:
        conn = psycopg.connect(
            f"host=localhost port=5432 user={admin_user} password={admin_pass} dbname=woms_db",
            autocommit=True,
        )
        print(f"[OK] Connected to woms_db as {admin_user}")
    except psycopg.OperationalError as e:
        print(f"[ERR] Cannot connect: {e}")
        sys.exit(1)

    # Step 1 - add is_active
    try:
        conn.execute("ALTER TABLE items ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
        print("[OK] Added is_active column (default TRUE)")
    except Exception as e:
        print(f"[ERR] Add is_active: {e}")
        conn.close()
        sys.exit(1)

    # Step 2 - index
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_is_active ON items (is_active)")
        print("[OK] Created index idx_items_is_active")
    except Exception as e:
        print(f"[WARN] Index: {e}")

    # Step 3 - drop FK constraint
    try:
        conn.execute("ALTER TABLE items DROP CONSTRAINT IF EXISTS items_status_id_fkey")
        print("[OK] Dropped FK constraint items_status_id_fkey")
    except Exception as e:
        print(f"[WARN] Drop FK: {e}")

    # Step 4 - drop status_id column
    try:
        conn.execute("ALTER TABLE items DROP COLUMN IF EXISTS status_id")
        print("[OK] Dropped status_id column")
    except Exception as e:
        print(f"[WARN] Drop column: {e}")

    # Step 5 - transfer ownership of items table to woms_user
    try:
        conn.execute("ALTER TABLE items OWNER TO woms_user")
        print("[OK] Transferred items table ownership to woms_user")
    except Exception as e:
        print(f"[WARN] Ownership transfer: {e}")

    conn.close()

    # Verify via woms_user
    from pathlib import Path
    env_file = Path(__file__).parent / ".env"
    db_password = None
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_PASSWORD="):
                db_password = line.split("=", 1)[1].strip()
                break

    if db_password:
        try:
            verify = psycopg.connect(
                f"postgresql://woms_user:{db_password}@localhost:5432/woms_db"
            )
            row = verify.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'items' AND column_name IN ('is_active', 'status_id') "
                "ORDER BY column_name"
            ).fetchall()
            cols = [r[0] for r in row]
            verify.close()
            print(f"\n[OK] Verified columns on items table: {cols}")
            if "is_active" in cols and "status_id" not in cols:
                print("[OK] Migration successful!")
            else:
                print("[WARN] Unexpected column state - check manually")
        except Exception as e:
            print(f"[WARN] Verification skipped: {e}")
    else:
        print("[INFO] Skipped verification (no .env found)")

    print("\nYou can now restart the backend server:")
    print("  cd backend")
    print("  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload")


if __name__ == "__main__":
    main()
