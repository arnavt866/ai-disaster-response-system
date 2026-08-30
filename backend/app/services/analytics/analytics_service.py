"""Operational analytics derived from persisted system data."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.allocation_record import AllocationRecord
from app.models.disaster_zone import DisasterZone
from app.models.mission import Mission
from app.models.resource_inventory import ResourceInventory


def _sum_latest_allocation_records(db: Session) -> tuple[float, float]:
    """Sum allocated/unmet from the newest allocation run per zone + category.

    Persisted flow rows share a run_id; allocated is summed across depots while
    unmet is taken once per zone/category from that run.
    """
    row_number = func.row_number().over(
        partition_by=(AllocationRecord.zone_id, AllocationRecord.resource_category),
        order_by=(AllocationRecord.created_at.desc(), AllocationRecord.id.desc()),
    ).label("row_number")

    latest_runs = (
        db.query(
            AllocationRecord.zone_id,
            AllocationRecord.resource_category,
            AllocationRecord.run_id,
            AllocationRecord.unmet,
            row_number,
        )
        .subquery()
    )

    latest_run_keys = (
        db.query(
            latest_runs.c.zone_id,
            latest_runs.c.resource_category,
            latest_runs.c.run_id,
            latest_runs.c.unmet,
        )
        .filter(latest_runs.c.row_number == 1)
        .subquery()
    )

    allocated = (
        db.query(func.coalesce(func.sum(AllocationRecord.allocated), 0.0))
        .join(
            latest_run_keys,
            (AllocationRecord.zone_id == latest_run_keys.c.zone_id)
            & (AllocationRecord.resource_category == latest_run_keys.c.resource_category)
            & (AllocationRecord.run_id == latest_run_keys.c.run_id),
        )
        .scalar()
    )
    unmet = (
        db.query(func.coalesce(func.sum(latest_run_keys.c.unmet), 0.0)).scalar()
    )
    return float(allocated or 0.0), float(unmet or 0.0)


def get_operations_dashboard(db: Session) -> dict:
    active_zones = (
        db.query(DisasterZone)
        .filter(DisasterZone.status == "Active")
        .count()
    )
    critical_zones = (
        db.query(DisasterZone)
        .filter(
            DisasterZone.status == "Active",
            DisasterZone.operational_priority == "Critical",
        )
        .count()
    )
    affected_population = (
        db.query(func.coalesce(func.sum(DisasterZone.affected_population), 0))
        .filter(DisasterZone.status == "Active")
        .scalar()
    )
    available_resources = (
        db.query(func.coalesce(func.sum(ResourceInventory.quantity), 0))
        .filter(ResourceInventory.status == "Available")
        .scalar()
    )
    reserved_resources = (
        db.query(func.coalesce(func.sum(ResourceInventory.reserved_quantity), 0))
        .filter(ResourceInventory.status == "Available")
        .scalar()
    )
    in_transit_resources = (
        db.query(func.coalesce(func.sum(ResourceInventory.in_transit_quantity), 0))
        .filter(ResourceInventory.status == "Available")
        .scalar()
    )
    allocated_resources, unmet_demand = _sum_latest_allocation_records(db)
    active_missions = (
        db.query(Mission)
        .filter(Mission.status.in_(["Allocated", "Dispatched", "In Transit"]))
        .count()
    )
    delivered_missions = (
        db.query(Mission).filter(Mission.status == "Delivered").count()
    )
    total_missions = db.query(Mission).count()

    mission_status_distribution = (
        db.query(Mission.status, func.count(Mission.id))
        .group_by(Mission.status)
        .all()
    )

    severity_distribution = (
        db.query(DisasterZone.operational_priority, func.count(DisasterZone.id))
        .filter(DisasterZone.status == "Active")
        .group_by(DisasterZone.operational_priority)
        .all()
    )

    return {
        "active_zones": active_zones,
        "critical_zones": critical_zones,
        "affected_population": int(affected_population or 0),
        "available_resources": int(available_resources or 0),
        "reserved_resources": int(reserved_resources or 0),
        "in_transit_resources": int(in_transit_resources or 0),
        "allocated_resources": float(allocated_resources or 0.0),
        "unmet_demand": float(unmet_demand or 0.0),
        "active_missions": active_missions,
        "delivered_missions": delivered_missions,
        "total_missions": total_missions,
        "mission_status_distribution": [
            {"status": status, "count": count}
            for status, count in mission_status_distribution
        ],
        "severity_distribution": [
            {"priority": priority or "Unknown", "count": count}
            for priority, count in severity_distribution
        ],
        "data_source": "database",
    }
