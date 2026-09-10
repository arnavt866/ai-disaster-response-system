"""Quarantine duplicate demo relief centers and inventory rows.

Targets the false "Stock mismatch" signal on the Resources page caused by:
  - duplicate relief_center rows sharing a name (Active + Inactive copy)
  - duplicate resource_inventory rows for the same warehouse + category

Relief centers are set to status='Quarantined' (reversible, not deleted).
Inventory duplicates keep the lowest id per (warehouse, category) as Available;
additional rows are set to status='Quarantined'.

Run without --apply for a dry run. Writes an audit CSV under reports/inventory_quarantine/.
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

QUARANTINED_STATUS = "Quarantined"
REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "inventory_quarantine"


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _find_duplicate_relief_centers(centers: list[ReliefCenter]) -> list[ReliefCenter]:
    by_name: dict[str, list[ReliefCenter]] = defaultdict(list)
    for center in centers:
        by_name[_norm(center.name)].append(center)

    targets: list[ReliefCenter] = []
    for group in by_name.values():
        if len(group) < 2:
            continue
        active = [c for c in group if _norm(c.status) == "active"]
        if not active:
            continue
        keep_id = min(c.id for c in active)
        for center in group:
            if center.id == keep_id:
                continue
            if _norm(center.status) != _norm(QUARANTINED_STATUS):
                targets.append(center)
    return targets


def _find_duplicate_inventory(rows: list[ResourceInventory]) -> tuple[list[ResourceInventory], list[ResourceInventory]]:
    by_key: dict[tuple[str, str], list[ResourceInventory]] = defaultdict(list)
    for row in rows:
        if _norm(row.status) == _norm(QUARANTINED_STATUS):
            continue
        key = (_norm(row.warehouse), _norm(row.category))
        by_key[key].append(row)

    keep: list[ResourceInventory] = []
    targets: list[ResourceInventory] = []
    for group in by_key.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda item: item.id)
        keep.append(group[0])
        targets.extend(group[1:])
    return keep, targets


def _stock_mismatch_preview(
    centers: list[ReliefCenter],
    inventory: list[ResourceInventory],
) -> list[dict[str, object]]:
    active_by_name: dict[str, ReliefCenter] = {}
    for center in centers:
        key = _norm(center.name)
        if _norm(center.status) == "active" and key not in active_by_name:
            active_by_name[key] = center

    stock_by_depot: dict[str, int] = defaultdict(int)
    for row in inventory:
        if _norm(row.status) != "available":
            continue
        stock_by_depot[_norm(row.warehouse)] += int(row.quantity or 0)

    previews: list[dict[str, object]] = []
    for key, center in sorted(active_by_name.items()):
        stock = stock_by_depot.get(key, 0)
        available = int(center.available_capacity or 0)
        mismatch = available > 0 and stock > available * 1.5
        previews.append(
            {
                "depot": center.name,
                "active_id": center.id,
                "available": available,
                "stock_available_rows": stock,
                "mismatch": mismatch,
            }
        )
    return previews


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit quarantine changes. Omit for dry run.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        centers = db.query(ReliefCenter).order_by(ReliefCenter.id).all()
        inventory = db.query(ResourceInventory).order_by(ResourceInventory.id).all()

        print("=== BEFORE stock mismatch preview (Active depot vs Available inventory) ===")
        for row in _stock_mismatch_preview(centers, inventory):
            flag = "MISMATCH" if row["mismatch"] else "ok"
            print(
                f"  [{flag}] {row['depot']} id={row['active_id']} "
                f"available={row['available']} stock={row['stock_available_rows']}"
            )

        relief_targets = _find_duplicate_relief_centers(centers)
        keep_rows, inventory_targets = _find_duplicate_inventory(inventory)

        print(f"\nRelief center quarantine targets : {len(relief_targets)}")
        for center in relief_targets:
            print(
                f"  id={center.id} name={center.name!r} status={center.status!r} "
                f"available={center.available_capacity}"
            )

        print(f"Inventory duplicate keep rows     : {len(keep_rows)}")
        print(f"Inventory quarantine targets      : {len(inventory_targets)}")
        for row in inventory_targets:
            print(
                f"  id={row.id} warehouse={row.warehouse!r} category={row.category!r} "
                f"qty={row.quantity} status={row.status!r}"
            )

        if not args.apply:
            print("\nDRY RUN - no changes committed. Re-run with --apply to commit.")
            db.rollback()
            return 0

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = REPORT_DIR / f"demo_duplicate_quarantine_{stamp}.csv"

        with report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["entity", "record_id", "name_or_warehouse", "previous_status", "new_status"])
            for center in relief_targets:
                writer.writerow(["relief_center", center.id, center.name, center.status, QUARANTINED_STATUS])
                center.status = QUARANTINED_STATUS
            for row in inventory_targets:
                writer.writerow(["inventory", row.id, row.warehouse, row.status, QUARANTINED_STATUS])
                row.status = QUARANTINED_STATUS

        db.commit()

        refreshed_centers = db.query(ReliefCenter).order_by(ReliefCenter.id).all()
        refreshed_inventory = db.query(ResourceInventory).order_by(ResourceInventory.id).all()
        print("\n=== AFTER stock mismatch preview ===")
        for row in _stock_mismatch_preview(refreshed_centers, refreshed_inventory):
            flag = "MISMATCH" if row["mismatch"] else "ok"
            print(
                f"  [{flag}] {row['depot']} id={row['active_id']} "
                f"available={row['available']} stock={row['stock_available_rows']}"
            )

        print(f"\nAPPLIED: {len(relief_targets)} relief centers, {len(inventory_targets)} inventory rows.")
        print(f"Audit trail: {report_path}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
