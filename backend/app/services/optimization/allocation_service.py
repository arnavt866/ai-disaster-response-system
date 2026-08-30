"""Priority-weighted resource allocation using OR-Tools linear programming."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ortools.linear_solver import pywraplp
from sqlalchemy.orm import Session

from app.models.allocation_record import AllocationRecord
from app.models.disaster_zone import DisasterZone
from app.models.relief_center import ReliefCenter
from app.models.resource_inventory import ResourceInventory
from app.services.optimization.constants import (
    DEMAND_TO_INVENTORY_CATEGORY,
    M2_DEMAND_TARGETS,
    PRIORITY_WEIGHTS,
)
from app.services.optimization.resource_tracking_service import (
    InsufficientInventoryError,
    release_superseded_zone_reservations,
    reserve_inventory_for_flows,
)
from app.services.optimization.routing_service import build_route, haversine_km
from app.services.prediction.zone_integration_service import predict_demand_for_zone

logger = logging.getLogger(__name__)


def _priority_weight(zone: DisasterZone) -> float:
    priority = zone.operational_priority or zone.severity or "Moderate"
    return PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS.get(zone.severity, 1.0))


def _inventory_supply_by_depot(db: Session) -> dict[int, dict[str, float]]:
    """Aggregate FREE (available minus reserved minus in-transit) inventory
    quantities by relief center and category.

    Matching strategy: prefer an EXACT (case-insensitive) match between
    ResourceInventory.warehouse and ReliefCenter.name. Only fall back to
    substring containment if no exact match exists, so short/generic depot
    names (e.g. "chennai") can't silently absorb stock meant for a
    differently-named depot (e.g. "Chennai Relief Camp"). Any inventory row
    that still can't be matched is logged, not silently dropped.
    """
    centers = {
        center.id: (center.name or "").strip().lower()
        for center in db.query(ReliefCenter).filter(ReliefCenter.status == "Active").all()
    }
    supply: dict[int, dict[str, float]] = {
        center_id: {cat: 0.0 for cat in DEMAND_TO_INVENTORY_CATEGORY.values()}
        for center_id in centers
    }
    unmatched: list[str] = []

    for item in db.query(ResourceInventory).filter(ResourceInventory.status == "Available").all():
        warehouse = (item.warehouse or "").strip().lower()
        category = (item.category or "").strip().lower()

        matched_center_id = next(
            (cid for cid, name in centers.items() if name == warehouse), None
        )
        if matched_center_id is None:
            matched_center_id = next(
                (
                    cid
                    for cid, name in centers.items()
                    if warehouse and name and (warehouse in name or name in warehouse)
                ),
                None,
            )
        if matched_center_id is None:
            unmatched.append(item.warehouse or "<blank>")
            continue

        free_qty = (
            float(item.quantity)
            - float(item.reserved_quantity)
            - float(item.in_transit_quantity)
        )
        free_qty = max(free_qty, 0.0)

        if category not in supply[matched_center_id]:
            supply[matched_center_id][category] = 0.0
        supply[matched_center_id][category] += free_qty

    if unmatched:
        logger.warning(
            "Allocation: %d resource_inventory rows had no matching active "
            "relief center and were excluded from supply calculation: %s",
            len(unmatched),
            sorted(set(unmatched)),
        )

    return supply


def _zone_demands(db: Session, zone_ids: list[int] | None = None) -> list[dict[str, Any]]:
    query = db.query(DisasterZone).filter(DisasterZone.status == "Active")
    if zone_ids:
        query = query.filter(DisasterZone.id.in_(zone_ids))
    zones = query.all()
    demands: list[dict[str, Any]] = []
    for zone in zones:
        prediction = predict_demand_for_zone(db, zone.id, update_source="allocation_engine")
        estimates = prediction["demand"]["prediction"]["predictions"]
        demand_by_category: dict[str, float] = {}
        for target, payload in estimates.items():
            category = DEMAND_TO_INVENTORY_CATEGORY.get(target)
            if category:
                demand_by_category[category] = float(payload["point_estimate"])
        demands.append(
            {
                "zone_id": zone.id,
                "zone_name": zone.zone_name,
                "latitude": zone.latitude,
                "longitude": zone.longitude,
                "priority": zone.operational_priority or zone.severity,
                "priority_weight": _priority_weight(zone),
                "demand_by_category": demand_by_category,
                "prediction": estimates,
            }
        )
    return demands


def _solve_category_transportation(
    *,
    category: str,
    zone_demands: list[dict[str, Any]],
    depot_supply: dict[int, dict[str, float]],
    depots: dict[int, ReliefCenter],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active_zones = [
        zone for zone in zone_demands if zone["demand_by_category"].get(category, 0) > 0
    ]
    active_depots = [
        depot_id
        for depot_id, categories in depot_supply.items()
        if categories.get(category, 0) > 0
    ]
    if not active_zones or not active_depots:
        return (
            [
                {
                    "zone_id": zone["zone_id"],
                    "relief_center_id": None,
                    "resource_category": category,
                    "demanded": zone["demand_by_category"].get(category, 0.0),
                    "allocated": 0.0,
                    "unmet": zone["demand_by_category"].get(category, 0.0),
                    "priority_weight": zone["priority_weight"],
                    "optimization_status": "no_supply_or_demand",
                }
                for zone in zone_demands
            ],
            [],
        )

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        raise RuntimeError("OR-Tools GLOP solver unavailable")

    variables: dict[tuple[int, int], Any] = {}
    for depot_id in active_depots:
        for zone in active_zones:
            variables[(depot_id, zone["zone_id"])] = solver.NumVar(
                0.0,
                solver.infinity(),
                f"x_{depot_id}_{zone['zone_id']}",
            )

    objective = solver.Objective()
    for depot_id in active_depots:
        for zone in active_zones:
            distance = haversine_km(
                depots[depot_id].latitude,
                depots[depot_id].longitude,
                zone["latitude"],
                zone["longitude"],
            )
            coeff = zone["priority_weight"] * 1000.0 - distance
            objective.SetCoefficient(variables[(depot_id, zone["zone_id"])], coeff)
    objective.SetMaximization()

    for depot_id in active_depots:
        constraint = solver.Constraint(0.0, depot_supply[depot_id][category])
        for zone in active_zones:
            constraint.SetCoefficient(
                variables[(depot_id, zone["zone_id"])], 1.0
            )

    for zone in active_zones:
        demand = zone["demand_by_category"].get(category, 0.0)
        constraint = solver.Constraint(0.0, demand)
        for depot_id in active_depots:
            constraint.SetCoefficient(
                variables[(depot_id, zone["zone_id"])], 1.0
            )

    status = solver.Solve()
    optimization_status = "optimal" if status == pywraplp.Solver.OPTIMAL else "feasible_or_partial"

    zone_allocations: dict[int, float] = {zone["zone_id"]: 0.0 for zone in zone_demands}
    flows: list[dict[str, Any]] = []
    for depot_id in active_depots:
        for zone in active_zones:
            allocated = variables[(depot_id, zone["zone_id"])].solution_value()
            if allocated <= 1e-6:
                continue
            zone_allocations[zone["zone_id"]] += allocated
            flows.append(
                {
                    "zone_id": zone["zone_id"],
                    "zone_name": zone["zone_name"],
                    "relief_center_id": depot_id,
                    "relief_center_name": depots[depot_id].name,
                    "resource_category": category,
                    "allocated": round(allocated, 2),
                    "route": build_route(
                        depot_id=depot_id,
                        depot_name=depots[depot_id].name,
                        depot_lat=depots[depot_id].latitude,
                        depot_lon=depots[depot_id].longitude,
                        zone_id=zone["zone_id"],
                        zone_name=zone["zone_name"],
                        zone_lat=zone["latitude"],
                        zone_lon=zone["longitude"],
                    ),
                }
            )

    summary: list[dict[str, Any]] = []
    for zone in zone_demands:
        demanded = zone["demand_by_category"].get(category, 0.0)
        allocated = round(zone_allocations.get(zone["zone_id"], 0.0), 2)
        summary.append(
            {
                "zone_id": zone["zone_id"],
                "relief_center_id": None,
                "resource_category": category,
                "demanded": demanded,
                "allocated": allocated,
                "unmet": round(max(demanded - allocated, 0.0), 2),
                "priority_weight": zone["priority_weight"],
                "optimization_status": optimization_status,
            }
        )
    return summary, flows


def optimize_allocation(
    db: Session,
    zone_ids: list[int] | None = None,
    *,
    persist: bool = True,
    reserve_inventory: bool = True,
) -> dict[str, Any]:
    """Run OR-Tools LP allocation using M2 zone demand and depot inventory."""
    depots = {
        center.id: center
        for center in db.query(ReliefCenter).filter(ReliefCenter.status == "Active").all()
    }
    if not depots:
        return {
            "run_id": None,
            "status": "no_depots",
            "message": "No active relief centers available for allocation.",
            "allocations": [],
            "flows": [],
        }

    depot_supply = _inventory_supply_by_depot(db)
    zone_demands = _zone_demands(db, zone_ids)
    if not zone_demands:
        return {
            "run_id": None,
            "status": "no_zones",
            "message": "No active disaster zones found for allocation.",
            "allocations": [],
            "flows": [],
        }

    run_id = str(uuid.uuid4())
    all_summaries: list[dict[str, Any]] = []
    all_flows: list[dict[str, Any]] = []

    for category in DEMAND_TO_INVENTORY_CATEGORY.values():
        summaries, flows = _solve_category_transportation(
            category=category,
            zone_demands=zone_demands,
            depot_supply=depot_supply,
            depots=depots,
        )
        all_summaries.extend(summaries)
        all_flows.extend(flows)

    inventory_reservations: list[dict[str, Any]] = []
    if reserve_inventory and all_flows:
        zone_ids_for_release = list({flow["zone_id"] for flow in all_flows})
        try:
            release_superseded_zone_reservations(db, zone_ids_for_release)
            inventory_reservations = reserve_inventory_for_flows(db, all_flows)
        except InsufficientInventoryError as exc:
            db.rollback()
            return {
                "run_id": run_id,
                "status": "insufficient_inventory",
                "message": str(exc),
                "allocations": all_summaries,
                "flows": all_flows,
            }

    if persist:
        summary_lookup = {
            (row["zone_id"], row["resource_category"]): row for row in all_summaries
        }
        if all_flows:
            # One record per depot flow so release_superseded_zone_reservations
            # can reverse the exact reserved quantities per relief center.
            for flow in all_flows:
                summary = summary_lookup.get(
                    (flow["zone_id"], flow["resource_category"]), {}
                )
                db.add(
                    AllocationRecord(
                        run_id=run_id,
                        zone_id=flow["zone_id"],
                        relief_center_id=flow["relief_center_id"],
                        resource_category=flow["resource_category"],
                        demanded=summary.get("demanded", 0.0),
                        allocated=flow["allocated"],
                        unmet=summary.get("unmet", 0.0),
                        priority_weight=summary.get("priority_weight", 1.0),
                        optimization_status=summary.get("optimization_status", "optimal"),
                    )
                )
        else:
            for row in all_summaries:
                depot_id = row.get("relief_center_id") or min(depots.keys())
                db.add(
                    AllocationRecord(
                        run_id=run_id,
                        zone_id=row["zone_id"],
                        relief_center_id=depot_id,
                        resource_category=row["resource_category"],
                        demanded=row["demanded"],
                        allocated=row["allocated"],
                        unmet=row["unmet"],
                        priority_weight=row["priority_weight"],
                        optimization_status=row.get("optimization_status", "optimal"),
                    )
                )
        db.commit()

    total_demanded = sum(row["demanded"] for row in all_summaries)
    total_allocated = sum(row["allocated"] for row in all_summaries)

    return {
        "run_id": run_id,
        "status": "ok",
        "algorithm": "ortools_glop_priority_transportation",
        "target_is_observed": False,
        "zone_count": len(zone_demands),
        "total_demanded": round(total_demanded, 2),
        "total_allocated": round(total_allocated, 2),
        "coverage_ratio": round(
            (total_allocated / total_demanded) if total_demanded else 0.0, 4
        ),
        "allocations": all_summaries,
        "flows": all_flows,
        "zone_demands": zone_demands,
        "inventory_reservations": inventory_reservations,
    }


def update_zone_priority(
    db: Session,
    zone_id: int,
    priority: str,
) -> DisasterZone:
    zone = db.query(DisasterZone).filter(DisasterZone.id == zone_id).first()
    if zone is None:
        raise ValueError(f"Disaster zone {zone_id} not found")
    if priority not in PRIORITY_WEIGHTS:
        raise ValueError(f"Invalid priority level: {priority}")
    zone.operational_priority = priority
    db.commit()
    db.refresh(zone)
    return zone