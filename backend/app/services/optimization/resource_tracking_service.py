"""Inventory lifecycle: available -> reserved -> in_transit -> delivered."""

import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.relief_center import ReliefCenter
from app.models.resource_inventory import ResourceInventory


class InsufficientInventoryError(ValueError):
    """Raised when allocation or dispatch exceeds available stock."""


def _free_quantity(row: ResourceInventory) -> int:
    """Uncommitted stock on a row (quantity is total on-hand)."""
    return max(
        int(row.quantity) - int(row.reserved_quantity) - int(row.in_transit_quantity),
        0,
    )


def _match_depot_id_for_item(
    item: ResourceInventory,
    center_names: dict[int, str],
) -> int | None:
    warehouse = (item.warehouse or "").strip().lower()
    if not warehouse:
        return None
    exact = next(
        (center_id for center_id, center_name in center_names.items() if warehouse == center_name),
        None,
    )
    if exact is not None:
        return exact
    return next(
        (
            center_id
            for center_id, center_name in center_names.items()
            if warehouse in center_name or center_name in warehouse
        ),
        None,
    )


def _inventory_rows_for_depot_category(
    db: Session,
    depot_id: int,
    category: str,
    *,
    prefer_field: str = "free",
) -> list[ResourceInventory]:
    centers = {
        center.id: center.name.lower()
        for center in db.query(ReliefCenter).filter(ReliefCenter.status == "Active").all()
    }
    category = category.lower()
    rows: list[ResourceInventory] = []
    for item in db.query(ResourceInventory).filter(ResourceInventory.status == "Available").all():
        if (item.category or "").lower() != category:
            continue
        if _match_depot_id_for_item(item, centers) == depot_id:
            rows.append(item)

    def _sort_key(row: ResourceInventory) -> tuple[int, int]:
        if prefer_field == "free":
            amount = _free_quantity(row)
        else:
            amount = int(getattr(row, prefer_field) or 0)
        return (-amount, row.id)

    rows.sort(key=_sort_key)
    return rows


def _release_quantity(rows: list[ResourceInventory], amount: int) -> int:
    """Decrease reserved_quantity up to amount; returns actual units released."""
    remaining = amount
    released_total = 0
    for row in rows:
        if remaining <= 0:
            break
        available = int(row.reserved_quantity)
        move = min(available, remaining)
        if move <= 0:
            continue
        row.reserved_quantity = available - move
        remaining -= move
        released_total += move
    return released_total


def _reserve_quantity(rows: list[ResourceInventory], amount: int) -> None:
    """Increase reserved_quantity from free stock without changing total quantity."""
    remaining = amount
    for row in rows:
        if remaining <= 0:
            break
        move = min(_free_quantity(row), remaining)
        if move <= 0:
            continue
        row.reserved_quantity = int(row.reserved_quantity) + move
        remaining -= move
    if remaining > 0:
        raise InsufficientInventoryError(
            f"Insufficient inventory: needed {amount}, short by {remaining}"
        )


def _move_quantity(
    rows: list[ResourceInventory],
    amount: int,
    *,
    from_field: str,
    to_field: str | None = None,
) -> None:
    remaining = amount
    for row in rows:
        if remaining <= 0:
            break
        available_in_field = int(getattr(row, from_field) or 0)
        move = min(available_in_field, remaining)
        if move <= 0:
            continue
        setattr(row, from_field, available_in_field - move)
        if to_field is not None:
            setattr(row, to_field, int(getattr(row, to_field) or 0) + move)
        elif from_field == "in_transit_quantity":
            row.quantity = int(row.quantity) - move
        remaining -= move
    if remaining > 0:
        raise InsufficientInventoryError(
            f"Insufficient inventory: needed {amount}, short by {remaining}"
        )


def reserve_inventory_for_flows(db: Session, flows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reserve stock for allocation flows by increasing reserved_quantity."""
    reservations: list[dict[str, Any]] = []
    for flow in flows:
        amount = int(math.ceil(float(flow.get("allocated", 0))))
        if amount <= 0:
            continue
        depot_id = flow["relief_center_id"]
        category = flow["resource_category"]
        rows = _inventory_rows_for_depot_category(db, depot_id, category, prefer_field="free")
        _reserve_quantity(rows, amount)
        reservations.append(
            {
                "depot_id": depot_id,
                "category": category,
                "quantity": amount,
                "state": "reserved",
            }
        )
    db.commit()
    return reservations


def release_reserved_for_flows(
    db: Session,
    flows: list[dict[str, Any]],
    *,
    strict: bool = False,
) -> list[dict[str, Any]]:
    """Return reserved stock to the free pool by decreasing reserved_quantity."""
    releases: list[dict[str, Any]] = []
    for flow in flows:
        amount = int(math.ceil(float(flow.get("allocated", 0))))
        if amount <= 0:
            continue
        depot_id = flow["relief_center_id"]
        category = flow["resource_category"]
        rows = _inventory_rows_for_depot_category(
            db, depot_id, category, prefer_field="reserved_quantity"
        )
        if strict:
            _move_quantity(rows, amount, from_field="reserved_quantity", to_field=None)
            released = amount
        else:
            released = _release_quantity(rows, amount)
        releases.append(
            {
                "depot_id": depot_id,
                "category": category,
                "quantity": released,
                "requested": amount,
                "state": "released",
            }
        )
    db.commit()
    return releases


def release_superseded_zone_reservations(
    db: Session,
    zone_ids: list[int],
) -> list[dict[str, Any]]:
    """Release reservations from the latest allocation run for each zone."""
    from app.models.allocation_record import AllocationRecord

    all_releases: list[dict[str, Any]] = []
    for zone_id in dict.fromkeys(zone_ids):
        latest_record = (
            db.query(AllocationRecord)
            .filter(
                AllocationRecord.zone_id == zone_id,
                AllocationRecord.allocated > 0,
            )
            .order_by(AllocationRecord.created_at.desc())
            .first()
        )
        if latest_record is None:
            continue

        records = (
            db.query(AllocationRecord)
            .filter(
                AllocationRecord.run_id == latest_record.run_id,
                AllocationRecord.zone_id == zone_id,
                AllocationRecord.allocated > 0,
            )
            .all()
        )
        flows = [
            {
                "relief_center_id": record.relief_center_id,
                "resource_category": record.resource_category,
                "allocated": record.allocated,
            }
            for record in records
        ]
        all_releases.extend(release_reserved_for_flows(db, flows, strict=False))
    return all_releases


VALID_TRANSITIONS: dict[str, set[str]] = {
    "Created": {"Allocated", "Dispatched"},
    "Allocated": {"Dispatched"},
    "Dispatched": {"In Transit"},
    "In Transit": {"Delivered"},
}


def dispatch_reserved_for_mission_items(
    db: Session,
    items: list[dict[str, Any]],
    default_depot_id: int | None,
) -> None:
    for item in items:
        amount = int(math.ceil(float(item.get("allocated", 0))))
        if amount <= 0:
            continue
        depot_id = item.get("relief_center_id") or default_depot_id
        if depot_id is None:
            raise ValueError("Mission depot is required for dispatch")
        category = item.get("resource_category", "")
        rows = _inventory_rows_for_depot_category(
            db, depot_id, category, prefer_field="reserved_quantity"
        )
        _move_quantity(rows, amount, from_field="reserved_quantity", to_field="in_transit_quantity")
    db.commit()


def deliver_in_transit_for_mission_items(
    db: Session,
    items: list[dict[str, Any]],
    default_depot_id: int | None,
) -> None:
    for item in items:
        amount = int(math.ceil(float(item.get("allocated", 0))))
        if amount <= 0:
            continue
        depot_id = item.get("relief_center_id") or default_depot_id
        if depot_id is None:
            raise ValueError("Mission depot is required for delivery")
        category = item.get("resource_category", "")
        rows = _inventory_rows_for_depot_category(
            db, depot_id, category, prefer_field="in_transit_quantity"
        )
        _move_quantity(rows, amount, from_field="in_transit_quantity", to_field=None)
    db.commit()


def release_reserved_for_mission(db: Session, items: list[dict[str, Any]], depot_id: int) -> None:
    """Return reserved stock to the free pool if a mission is cancelled before dispatch."""
    flows = [
        {
            "relief_center_id": depot_id,
            "resource_category": item.get("resource_category", ""),
            "allocated": item.get("allocated", 0),
        }
        for item in items
    ]
    release_reserved_for_flows(db, flows, strict=True)
