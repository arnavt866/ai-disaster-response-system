"""Operational analytics derived from persisted system data."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.allocation_record import AllocationRecord
from app.models.disaster_zone import DisasterZone
from app.models.mission import Mission
from app.models.relief_center import ReliefCenter
from app.services.optimization.constants import ACTIVE_MISSION_STATUSES
from app.services.optimization.resource_tracking_service import (
    active_depot_inventory_totals,
)

# Pytest and smoke allocations often write 1-unit runs that swamp the trend window.
MIN_TREND_DEMAND_UNITS = 50

# Quarantine sets status=Inactive, but leftover pytest rows have also been
# re-activated in past demos. Name markers are a second fence so fixture
# zones never re-enter operational reports even if status is wrong.
FIXTURE_ZONE_NAME_MARKERS = ("M3 Test Zone", "Tracking Zone")


def _fixture_zone_name_clause():
    return or_(
        *[
            DisasterZone.zone_name.ilike(f"%{marker}%")
            for marker in FIXTURE_ZONE_NAME_MARKERS
        ]
    )


def unmet_from(demanded: float, allocated: float) -> float:
    """Unmet is derived, never read back from a depot flow row."""
    return max(float(demanded or 0.0) - float(allocated or 0.0), 0.0)


def _quarantined_supply_run_ids(db: Session):
    """Run ids that drew supply from a depot that is not Active.

    Leftover pytest fixtures ("M3 Depot ...", "Track Depot ...") allocate against
    real Active zones, so a zone-status filter alone does not remove them. Keeping
    such a run while discarding its quarantined supply reports full demand against
    near-zero allocation, which fabricates coverage collapses in the trend. The
    whole run is therefore treated as non-operational.
    """
    return select(AllocationRecord.run_id).outerjoin(
        ReliefCenter, ReliefCenter.id == AllocationRecord.relief_center_id
    ).where(
        AllocationRecord.relief_center_id.isnot(None),
        (ReliefCenter.id.is_(None)) | (ReliefCenter.status != "Active"),
    ).distinct()


def _operational_records(db: Session):
    """Allocation rows for Active zones from runs supplied only by Active depots."""
    return (
        db.query(AllocationRecord)
        .join(DisasterZone, DisasterZone.id == AllocationRecord.zone_id)
        .filter(
            DisasterZone.status == "Active",
            ~_fixture_zone_name_clause(),
            ~AllocationRecord.run_id.in_(_quarantined_supply_run_ids(db)),
        )
    )


def _zone_category_rollups(db: Session):
    """One row per (run_id, zone_id, category).

    Flow rows repeat demanded on every depot line, so demanded is taken once via
    max while allocated sums across depots.
    """
    return (
        _operational_records(db)
        .with_entities(
            AllocationRecord.run_id.label("run_id"),
            AllocationRecord.zone_id.label("zone_id"),
            AllocationRecord.resource_category.label("resource_category"),
            func.max(AllocationRecord.demanded).label("demanded"),
            func.sum(AllocationRecord.allocated).label("allocated"),
            func.min(AllocationRecord.created_at).label("created_at"),
        )
        .group_by(
            AllocationRecord.run_id,
            AllocationRecord.zone_id,
            AllocationRecord.resource_category,
        )
        .subquery()
    )


def _latest_run_keys(db: Session):
    """Newest allocation run per zone + category, with demanded and real allocated."""
    rollups = _zone_category_rollups(db)
    row_number = func.row_number().over(
        partition_by=(rollups.c.zone_id, rollups.c.resource_category),
        order_by=(rollups.c.created_at.desc(), rollups.c.run_id.desc()),
    ).label("row_number")

    ranked = db.query(rollups, row_number).subquery()

    return (
        db.query(
            ranked.c.zone_id,
            ranked.c.resource_category,
            ranked.c.run_id,
            ranked.c.demanded,
            ranked.c.allocated,
        )
        .filter(ranked.c.row_number == 1)
        .subquery()
    )


def _sum_latest_allocation_records(db: Session) -> tuple[float, float]:
    """Total allocated and unmet across the newest run per zone + category."""
    latest = _latest_run_keys(db)
    rows = db.query(latest.c.demanded, latest.c.allocated).all()
    allocated = sum(float(row.allocated or 0.0) for row in rows)
    unmet = sum(unmet_from(row.demanded, row.allocated) for row in rows)
    return allocated, unmet


def get_operations_dashboard(db: Session) -> dict:
    active_zones = (
        db.query(DisasterZone)
        .filter(DisasterZone.status == "Active", ~_fixture_zone_name_clause())
        .count()
    )
    critical_zones = (
        db.query(DisasterZone)
        .filter(
            DisasterZone.status == "Active",
            ~_fixture_zone_name_clause(),
            DisasterZone.operational_priority == "Critical",
        )
        .count()
    )
    affected_population = (
        db.query(func.coalesce(func.sum(DisasterZone.affected_population), 0))
        .filter(DisasterZone.status == "Active", ~_fixture_zone_name_clause())
        .scalar()
    )
    # Restricted to Active depots so the KPI matches allocatable supply; stock
    # on Inactive/quarantined depot warehouses is excluded, not summed.
    inventory_totals = active_depot_inventory_totals(db)
    available_resources = inventory_totals["quantity"]
    reserved_resources = inventory_totals["reserved"]
    in_transit_resources = inventory_totals["in_transit"]
    allocated_resources, unmet_demand = _sum_latest_allocation_records(db)
    active_missions = (
        db.query(Mission)
        .filter(Mission.status.in_(ACTIVE_MISSION_STATUSES))
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
        .filter(DisasterZone.status == "Active", ~_fixture_zone_name_clause())
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


def get_allocation_reports(db: Session, *, trend_limit: int = 24, top_zones: int = 8) -> dict:
    """Charts for the Reports page: coverage trend, category mix, unmet-gap zones."""
    rollups = _zone_category_rollups(db)

    run_rows = (
        db.query(
            rollups.c.run_id,
            func.min(rollups.c.created_at).label("created_at"),
            func.sum(rollups.c.demanded).label("demanded"),
            func.sum(rollups.c.allocated).label("allocated"),
            func.sum(
                func.greatest(rollups.c.demanded - rollups.c.allocated, 0.0)
            ).label("unmet"),
            func.count(func.distinct(rollups.c.zone_id)).label("zone_count"),
        )
        .group_by(rollups.c.run_id)
        .order_by(func.min(rollups.c.created_at).asc())
        .all()
    )
    meaningful_runs = [
        row for row in run_rows if float(row.demanded or 0.0) >= MIN_TREND_DEMAND_UNITS
    ]
    trend_source = meaningful_runs if meaningful_runs else run_rows
    if trend_limit > 0:
        trend_source = trend_source[-trend_limit:]

    coverage_trend = []
    for row in trend_source:
        demanded = float(row.demanded or 0.0)
        allocated = float(row.allocated or 0.0)
        unmet = float(row.unmet or 0.0)
        coverage_trend.append(
            {
                "run_id": row.run_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "demanded": round(demanded, 2),
                "allocated": round(allocated, 2),
                "unmet": round(unmet, 2),
                "coverage_ratio": round((allocated / demanded) if demanded else 0.0, 4),
                "unmet_ratio": round((unmet / demanded) if demanded else 0.0, 4),
                "zone_count": int(row.zone_count or 0),
            }
        )

    latest_run_keys = _latest_run_keys(db)
    latest_demand = db.query(
        latest_run_keys.c.resource_category,
        latest_run_keys.c.zone_id,
        latest_run_keys.c.demanded,
        latest_run_keys.c.allocated,
    ).all()

    category_totals: dict[str, dict[str, float]] = {}
    for row in latest_demand:
        bucket = category_totals.setdefault(
            (row.resource_category or "unknown").lower(),
            {"allocated": 0.0, "demanded": 0.0, "unmet": 0.0},
        )
        bucket["allocated"] += float(row.allocated or 0.0)
        bucket["demanded"] += float(row.demanded or 0.0)
        bucket["unmet"] += unmet_from(row.demanded, row.allocated)

    category_order = ["food", "water", "medical", "shelter"]
    category_breakdown = []
    seen = set()
    for key in category_order:
        if key in category_totals:
            seen.add(key)
            totals = category_totals[key]
            category_breakdown.append(
                {
                    "category": key,
                    "allocated": round(totals["allocated"], 2),
                    "demanded": round(totals["demanded"], 2),
                    "unmet": round(totals["unmet"], 2),
                }
            )
    for key, totals in sorted(category_totals.items()):
        if key in seen:
            continue
        category_breakdown.append(
            {
                "category": key,
                "allocated": round(totals["allocated"], 2),
                "demanded": round(totals["demanded"], 2),
                "unmet": round(totals["unmet"], 2),
            }
        )

    zone_totals: dict[int, dict[str, float]] = {}
    for row in latest_demand:
        bucket = zone_totals.setdefault(
            int(row.zone_id),
            {"unmet": 0.0, "allocated": 0.0, "demanded": 0.0},
        )
        bucket["unmet"] += unmet_from(row.demanded, row.allocated)
        bucket["allocated"] += float(row.allocated or 0.0)
        bucket["demanded"] += float(row.demanded or 0.0)

    zone_ids = list(zone_totals.keys())
    zones = (
        db.query(DisasterZone)
        .filter(
            DisasterZone.id.in_(zone_ids),
            DisasterZone.status == "Active",
            ~_fixture_zone_name_clause(),
        )
        .all()
        if zone_ids
        else []
    )
    zone_map = {zone.id: zone for zone in zones}

    ranked = []
    for zone_id, totals in zone_totals.items():
        zone = zone_map.get(zone_id)
        if zone is None:
            continue
        ranked.append(
            {
                "zone_id": zone_id,
                "zone_name": zone.zone_name,
                "priority": zone.operational_priority or "Unknown",
                "severity": zone.severity or "Unknown",
                "affected_population": int(zone.affected_population or 0),
                "status": zone.status,
                "allocated": round(totals["allocated"], 2),
                "demanded": round(totals["demanded"], 2),
                "unmet": round(totals["unmet"], 2),
            }
        )
    # A "highest unmet demand" chart should only carry zones that actually have a
    # gap; zero-unmet zones previously padded the list out to top_zones.
    ranked = [row for row in ranked if row["unmet"] > 0]
    ranked.sort(key=lambda row: (-row["unmet"], -row["demanded"], row["zone_name"]))
    critical_zones = ranked[:top_zones]

    return {
        "coverage_trend": coverage_trend,
        "category_breakdown": category_breakdown,
        "critical_zones": critical_zones,
        "run_count": len(coverage_trend),
        "data_source": "database",
    }
