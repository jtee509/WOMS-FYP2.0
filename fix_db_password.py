"""
Quick fix: sync the woms_user password in PostgreSQL with the .env file.

Usage:
    python fix_db_password.py

Prompts once for the postgres admin password, then:
  1. Reads DATABASE_PASSWORD from .env
  2. ALTER USER woms_user WITH PASSWORD '<password from .env>'
  3. Verifies the connection works

Safe to delete this script after use.
"""

import getpass
import sys
from pathlib import Path


def main():
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("[ERR] .env not found — run setup_env.py first")
        sys.exit(1)

    # Read DATABASE_PASSWORD from .env
    db_password = None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_PASSWORD="):
            db_password = line.split("=", 1)[1].strip()
            break

    if not db_password:
        print("[ERR] DATABASE_PASSWORD not found in .env")
        sys.exit(1)

    print(f"[OK] Read DATABASE_PASSWORD from .env")
    print(f"     Password: {db_password[:8]}...{db_password[-4:]}")

    # Get postgres admin password
    admin_pass = getpass.getpass("Enter postgres admin password: ")

    try:
        import psycopg
    except ImportError:
        print("[ERR] psycopg not installed — run: pip install psycopg-binary")
        sys.exit(1)

    # Connect as admin and update woms_user
    try:
        conn = psycopg.connect(
            f"host=localhost port=5432 user=postgres password={admin_pass} dbname=postgres",
            autocommit=True,
        )
        print("[OK] Connected to PostgreSQL as postgres")

        # Create or update woms_user
        try:
            conn.execute("CREATE USER woms_user WITH PASSWORD %s", (db_password,))
            print("[OK] Created user woms_user")
        except psycopg.errors.DuplicateObject:
            conn.execute("ALTER USER woms_user WITH PASSWORD %s", (db_password,))
            print("[OK] Updated woms_user password")

        # Ensure databases exist
        for db in ("woms_db", "ml_woms_db"):
            try:
                conn.execute(f'CREATE DATABASE "{db}" OWNER woms_user')
                print(f"[OK] Created database: {db}")
            except psycopg.errors.DuplicateDatabase:
                conn.execute(f'ALTER DATABASE "{db}" OWNER TO woms_user')
                print(f"[OK] Database '{db}' exists — owner set to woms_user")
            conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db}" TO woms_user')

        conn.close()
        print("[OK] Privileges granted")

    except psycopg.OperationalError as e:
        print(f"[ERR] Cannot connect as postgres: {e}")
        sys.exit(1)

    # Verify the new connection works
    try:
        verify = psycopg.connect(
            f"postgresql://woms_user:{db_password}@localhost:5432/woms_db"
        )
        verify.execute("SELECT 1")
        verify.close()
        print("\n[OK] Verified: woms_user can connect to woms_db")
        print("\nYou can now start the backend:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n[ERR] Verification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
