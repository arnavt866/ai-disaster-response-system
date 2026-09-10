"""One-shot: release reserved stock on Inactive depots with unique warehouse names."""

from __future__ import annotations

from app.database.connection import SessionLocal
from app.models.relief_center import ReliefCenter
from app.models.resource_inventory import ResourceInventory
from app.services.optimization.resource_tracking_service import (
    _free_quantity,
    release_orphaned_reservations_for_inactive_depots,
)


def _totals(db) -> dict[str, int]:
    rows = db.query(ResourceInventory).all()
    centers = db.query(ReliefCenter).all()
    active_names = {
        (c.name or "").strip().lower()
        for c in centers
        if (c.status or "").strip().lower() == "active"
    }
    inactive_unique = {
        (c.name or "").strip().lower()
        for c in centers
        if (c.status or "").strip().lower() != "active"
        and (c.name or "").strip()
        and (c.name or "").strip().lower() not in active_names
    }

    def acc(predicate) -> tuple[int, int, int, int]:
        qty = reserved = transit = free = 0
        n_reserved_rows = 0
        for row in rows:
            if not predicate(row):
                continue
            qty += int(row.quantity or 0)
            reserved += int(row.reserved_quantity or 0)
            transit += int(row.in_transit_quantity or 0)
            free += _free_quantity(row)
            if int(row.reserved_quantity or 0) > 0:
                n_reserved_rows += 1
        return qty, reserved, transit, free, n_reserved_rows

    g = acc(lambda _r: True)
    inactive = acc(lambda r: (r.warehouse or "").strip().lower() in inactive_unique)
    active = acc(
        lambda r: (r.warehouse or "").strip().lower() in active_names
        or (r.warehouse or "").strip().lower() not in inactive_unique
    )
    return {
        "global_quantity": g[0],
        "global_reserved": g[1],
        "global_in_transit": g[2],
        "global_free": g[3],
        "global_reserved_rows": g[4],
        "inactive_unique_quantity": inactive[0],
        "inactive_unique_reserved": inactive[1],
        "inactive_unique_in_transit": inactive[2],
        "inactive_unique_free": inactive[3],
        "inactive_unique_reserved_rows": inactive[4],
        "active_or_shared_free": active[3],
        "active_or_shared_reserved": active[1],
        "inactive_depot_count": len(
            {c.id for c in centers if (c.status or "").strip().lower() != "active"}
        ),
        "inactive_unique_name_count": len(inactive_unique),
    }


def main() -> None:
    db = SessionLocal()
    try:
        before = _totals(db)
        print("BEFORE", before)
        result = release_orphaned_reservations_for_inactive_depots(db)
        print("RELEASE", result)
        after = _totals(db)
        print("AFTER", after)
    finally:
        db.close()


if __name__ == "__main__":
    main()
