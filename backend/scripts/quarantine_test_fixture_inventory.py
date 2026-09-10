"""Quarantine resource_inventory rows left behind by M3 test fixtures.

Rows written by ``tests/m3_isolated_seed.py`` (and an earlier revision of
``tests/test_m3_resource_tracking.py``) before ``tests/conftest.py`` provided
SAVEPOINT isolation are still committed in the shared database. Their warehouse
labels name Inactive relief centers, so ``_inventory_supply_by_depot`` already
excludes them from allocation, but they were still summed into the analytics
dashboard's resource KPIs.

This script sets ``status='Quarantined'`` on those rows. Quantities are left
untouched so the change is reversible and auditable; affected ids are written to
``reports/inventory_quarantine/``.

A row is quarantined only when BOTH hold:
  1. its warehouse matches no Active relief center (the allocator's own rule), and
  2. its warehouse uses a known test-fixture prefix.

Run with --apply to commit. Without it, the script reports and rolls back.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import SessionLocal
from app.models.relief_center import ReliefCenter
from app.models.resource_inventory import ResourceInventory

TEST_WAREHOUSE_PREFIXES = ("M3 Depot", "Track Depot", "Orphan Depot")
QUARANTINED_STATUS = "Quarantined"
EXPECTED_ROW_COUNT = 300

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "inventory_quarantine"


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _matches_active_depot(warehouse: str, active_names: set[str]) -> bool:
    """Exact match first, then substring — mirrors _inventory_supply_by_depot."""
    if warehouse in active_names:
        return True
    return any(
        warehouse and name and (warehouse in name or name in warehouse)
        for name in active_names
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the quarantine. Omit for a dry run.",
    )
    parser.add_argument(
        "--expect",
        type=int,
        default=EXPECTED_ROW_COUNT,
        help=f"Abort if the target row count differs (default {EXPECTED_ROW_COUNT}).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        centers = db.query(ReliefCenter).all()
        active_names = {_norm(c.name) for c in centers if _norm(c.status) == "active"}
        if not active_names:
            print("ABORT: no Active relief centers found; refusing to quarantine.")
            return 2

        rows = db.query(ResourceInventory).all()

        targets: list[ResourceInventory] = []
        protected = 0
        orphan_non_test: list[ResourceInventory] = []

        for item in rows:
            if _matches_active_depot(_norm(item.warehouse), active_names):
                protected += 1
                continue
            if (item.warehouse or "").startswith(TEST_WAREHOUSE_PREFIXES):
                targets.append(item)
            else:
                orphan_non_test.append(item)

        print(f"Active relief centers          : {len(active_names)}")
        print(f"resource_inventory rows total   : {len(rows)}")
        print(f"  protected (Active depot match): {protected}")
        print(f"  quarantine targets            : {len(targets)}")
        print(f"  orphan but NOT test-pattern   : {len(orphan_non_test)} (left untouched)")

        for item in orphan_non_test:
            print(
                f"    SKIP id={item.id} warehouse={item.warehouse!r} "
                f"category={item.category!r} quantity={item.quantity}"
            )

        already = [t for t in targets if _norm(t.status) == _norm(QUARANTINED_STATUS)]
        pending = [t for t in targets if _norm(t.status) != _norm(QUARANTINED_STATUS)]
        print(f"  already quarantined           : {len(already)}")
        print(f"  to update this run            : {len(pending)}")

        if len(targets) != args.expect:
            print(
                f"ABORT: expected {args.expect} target rows, found {len(targets)}. "
                "Re-run the audit before applying."
            )
            return 3

        by_category: dict[str, int] = defaultdict(int)
        for item in targets:
            by_category[_norm(item.category)] += int(item.quantity or 0)
        total_qty = sum(by_category.values())
        print("\nQuantity being removed from dashboard KPIs:")
        for category in sorted(by_category):
            print(f"  {category:<10} {by_category[category]:>10,}")
        print(f"  {'TOTAL':<10} {total_qty:>10,}")

        if not args.apply:
            print("\nDRY RUN - no changes committed. Re-run with --apply to commit.")
            db.rollback()
            return 0

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = REPORT_DIR / f"quarantine_{stamp}.csv"
        with report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "inventory_id",
                    "warehouse",
                    "resource_name",
                    "category",
                    "quantity",
                    "reserved_quantity",
                    "in_transit_quantity",
                    "previous_status",
                    "new_status",
                ]
            )
            for item in targets:
                writer.writerow(
                    [
                        item.id,
                        item.warehouse,
                        item.resource_name,
                        item.category,
                        item.quantity,
                        item.reserved_quantity,
                        item.in_transit_quantity,
                        item.status,
                        QUARANTINED_STATUS,
                    ]
                )

        for item in pending:
            item.status = QUARANTINED_STATUS
        db.commit()

        print(f"\nAPPLIED: {len(pending)} rows set to status={QUARANTINED_STATUS!r}.")
        print(f"Audit trail: {report_path}")
        print("Quantities were NOT modified; revert by restoring previous_status.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
