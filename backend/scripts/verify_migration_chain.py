"""Verify `alembic upgrade head` succeeds on a genuinely empty database.

Creates a throwaway database, runs the full migration chain from <base>, then
diffs the resulting schema against the current live database. Drops the
throwaway database afterwards. The live database is only read from.

    python scripts/verify_migration_chain.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "disaster_migration_check"

load_dotenv()

LIVE_URL = os.getenv("DATABASE_URL")
if not LIVE_URL:
    sys.exit("DATABASE_URL is not set")


def _with_database(url: str, dbname: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{dbname}"))


TEST_URL = _with_database(LIVE_URL, TEST_DB_NAME)
ADMIN_URL = _with_database(LIVE_URL, "postgres")


def _recreate_test_database() -> None:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": TEST_DB_NAME},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()


def _drop_test_database() -> None:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": TEST_DB_NAME},
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    admin.dispose()


def _run_alembic_upgrade() -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_URL
    return subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _snapshot(url: str) -> dict:
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        tables = {
            name
            for name in inspector.get_table_names()
            if name not in {"spatial_ref_sys"}
        }
        columns = {
            table: {
                col["name"]: (str(col["type"]), col["nullable"])
                for col in inspector.get_columns(table)
            }
            for table in sorted(tables)
        }
        return {"tables": tables, "columns": columns}
    finally:
        engine.dispose()


def main() -> None:
    print(f"=== Creating empty database '{TEST_DB_NAME}' ===")
    _recreate_test_database()

    empty = _snapshot(TEST_URL)
    print(f"Tables before migrations: {sorted(empty['tables']) or '(none)'}")

    try:
        print("\n=== Running 'alembic upgrade head' from <base> ===")
        result = _run_alembic_upgrade()
        print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        if result.returncode != 0:
            sys.exit(f"\nFAILED: alembic exited {result.returncode}")
        print("\nalembic upgrade head: OK")

        fresh = _snapshot(TEST_URL)
        live = _snapshot(LIVE_URL)

        print(f"\n=== Fresh DB tables ({len(fresh['tables'])}) ===")
        for name in sorted(fresh["tables"]):
            print(f"  {name}")

        missing = sorted(live["tables"] - fresh["tables"])
        extra = sorted(fresh["tables"] - live["tables"])
        print("\n=== Diff vs live database ===")
        print(f"  missing in fresh: {missing or 'none'}")
        print(f"  extra in fresh:   {extra or 'none'}")

        column_diffs = []
        for table in sorted(live["tables"] & fresh["tables"]):
            if live["columns"][table] != fresh["columns"][table]:
                column_diffs.append(table)
                print(f"\n  column mismatch in '{table}':")
                live_cols = live["columns"][table]
                fresh_cols = fresh["columns"][table]
                for col in sorted(set(live_cols) | set(fresh_cols)):
                    if live_cols.get(col) != fresh_cols.get(col):
                        print(f"    {col}: live={live_cols.get(col)} fresh={fresh_cols.get(col)}")
        if not column_diffs:
            print("  column definitions: identical for all shared tables")

        print("\n=== RESULT ===")
        if missing or extra or column_diffs:
            sys.exit("Schema drift between fresh migration chain and live database.")
        print("Fresh migration chain reproduces the live schema exactly.")
    finally:
        print(f"\n=== Dropping '{TEST_DB_NAME}' ===")
        _drop_test_database()


if __name__ == "__main__":
    main()
