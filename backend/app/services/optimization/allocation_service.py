"""Priority-weighted resource allocation using OR-Tools linear programming."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ortools.linear_solver import pywraplp
from sqlalchemy.orm import Session

from app.models.allocation_record import AllocationRecord
from app.models.disaster_zone import DisasterZone
from app.models.field_team import FieldTeam
from app.models.relief_center import ReliefCenter
from app.models.resource_inventory import ResourceInventory
from app.services.optimization.constants import (
    DEFAULT_DEPOT_DAILY_PAYLOAD_KG,
    DEMAND_TO_INVENTORY_CATEGORY,
    INACTIVE_FIELD_TEAM_STATUS,
    PRIORITY_WEIGHTS,
    RESOURCE_UNIT_WEIGHT_KG,
    TEAM_DEPOT_COLOCATION_KM,
)
from app.services.optimization.resource_tracking_service import (
    InsufficientInventoryError,
    release_superseded_zone_reservations,
    reserve_inventory_for_flows,
)
from app.services.optimization.routing_service import (
    build_road_route,
    haversine_km,
)
from app.services.prediction.zone_integration_service import predict_demand_for_zone

logger = logging.getLogger(__name__)

LP_DISTANCE_PRIORITY_SCALE = 1000.0


def allocation_objective_coefficient(priority_weight: float, distance_km: float) -> float:
    """Priority-weighted maximization coefficient: higher priority, shorter distance."""
    return priority_weight * LP_DISTANCE_PRIORITY_SCALE - distance_km


def _cached_road_route(
    cache: dict[tuple[int, int], dict[str, Any]],
    *,
    depot_id: int,
    depot_name: str,
    depot_lat: float,
    depot_lon: float,
    zone_id: int,
    zone_name: str,
    zone_lat: float,
    zone_lon: float,
) -> dict[str, Any]:
    """Compute a depot-zone road route once; reuse the same payload for LP and flows."""
    key = (depot_id, zone_id)
    if key not in cache:
        cache[key] = build_road_route(
            depot_id=depot_id,
            depot_name=depot_name,
            depot_lat=depot_lat,
            depot_lon=depot_lon,
            zone_id=zone_id,
            zone_name=zone_name,
            zone_lat=zone_lat,
            zone_lon=zone_lon,
        )
    return cache[key]


def _cached_route_distance_km(
    cache: dict[tuple[int, int], dict[str, Any]],
    depot_id: int,
    depot_lat: float,
    depot_lon: float,
    zone_id: int,
    zone_lat: float,
    zone_lon: float,
    *,
    depot_name: str = "",
    zone_name: str = "",
) -> float:
    route = _cached_road_route(
        cache,
        depot_id=depot_id,
        depot_name=depot_name,
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        zone_id=zone_id,
        zone_name=zone_name,
        zone_lat=zone_lat,
        zone_lon=zone_lon,
    )
    return float(route["distance_km"])


def compute_depot_transport_capacity_kg(
    depots: dict[int, Any],
    teams: list[Any],
) -> dict[int, float]:
    """Total available vehicle payload (kg) per relief center for one allocation run.

    FieldTeam has vehicle_capacity and optional base coordinates, but no
    relief_center_id (or other FK) tying a team to a depot. Teams with a base
    location within TEAM_DEPOT_COLOCATION_KM of the nearest depot are treated
    as that depot's fleet. Any depot with no such match uses
    DEFAULT_DEPOT_DAILY_PAYLOAD_KG and logs a warning.
    """
    fleet_kg: dict[int, float] = {depot_id: 0.0 for depot_id in depots}

    for team in teams:
        if (getattr(team, "status", None) or "Available") != "Available":
            continue
        payload = float(getattr(team, "vehicle_capacity", 0) or 0)
        team_lat = getattr(team, "base_latitude", None)
        team_lon = getattr(team, "base_longitude", None)
        team_id = getattr(team, "id", None)
        team_name = getattr(team, "team_name", None)
        if team_lat is None or team_lon is None:
            logger.warning(
                "Field team id=%s name=%s has no base_latitude/base_longitude; "
                "cannot co-locate with a depot and is excluded from fleet capacity",
                team_id,
                team_name,
            )
            continue

        nearest_id: int | None = None
        nearest_km: float | None = None
        for depot_id, depot in depots.items():
            distance = haversine_km(
                float(team_lat),
                float(team_lon),
                float(depot.latitude),
                float(depot.longitude),
            )
            if nearest_km is None or distance < nearest_km:
                nearest_km = distance
                nearest_id = depot_id

        if nearest_id is None or nearest_km is None or nearest_km > TEAM_DEPOT_COLOCATION_KM:
            logger.warning(
                "Field team id=%s name=%s is not co-located with any depot "
                "(nearest=%.2f km, threshold=%.1f km); excluded from fleet capacity",
                team_id,
                team_name,
                nearest_km if nearest_km is not None else float("nan"),
                TEAM_DEPOT_COLOCATION_KM,
            )
            continue
        fleet_kg[nearest_id] += payload

    capacity: dict[int, float] = {}
    for depot_id, depot in depots.items():
        if fleet_kg[depot_id] > 0:
            capacity[depot_id] = fleet_kg[depot_id]
            continue
        capacity[depot_id] = DEFAULT_DEPOT_DAILY_PAYLOAD_KG
        logger.warning(
            "Depot id=%s name=%s has no linked/co-located Available field team; "
            "using DEFAULT_DEPOT_DAILY_PAYLOAD_KG=%.1f (assumption, not a measured fleet)",
            depot_id,
            getattr(depot, "name", None),
            DEFAULT_DEPOT_DAILY_PAYLOAD_KG,
        )
    return capacity


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


def _zone_demands(
    db: Session,
    zone_ids: list[int] | None = None,
    max_zones: int | None = None,
) -> list[dict[str, Any]]:
    query = db.query(DisasterZone).filter(DisasterZone.status == "Active")
    if zone_ids:
        query = query.filter(DisasterZone.id.in_(zone_ids))
    elif max_zones:
        query = query.limit(max_zones)
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


def _empty_category_summaries(
    category: str,
    zone_demands: list[dict[str, Any]],
    status: str = "no_supply_or_demand",
) -> list[dict[str, Any]]:
    return [
        {
            "zone_id": zone["zone_id"],
            "relief_center_id": None,
            "resource_category": category,
            "demanded": zone["demand_by_category"].get(category, 0.0),
            "allocated": 0.0,
            "unmet": zone["demand_by_category"].get(category, 0.0),
            "priority_weight": zone["priority_weight"],
            "optimization_status": status,
        }
        for zone in zone_demands
    ]


def _solve_allocation_lp(
    *,
    zone_demands: list[dict[str, Any]],
    depot_supply: dict[int, dict[str, float]],
    depots: dict[int, ReliefCenter],
    categories: tuple[str, ...] | None = None,
    distance_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
    depot_capacity_kg: dict[int, float] | None = None,
    unit_weights: dict[str, float] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One GLOP model for all resource categories in an allocation run.

    Transport capacity is a single per-depot mass budget shared across
    categories. Solving category-by-category with a fresh solver would
    silently reuse the full fleet for every category.
    """
    solve_categories = categories or tuple(DEMAND_TO_INVENTORY_CATEGORY.values())
    weights = unit_weights or RESOURCE_UNIT_WEIGHT_KG
    if distance_cache is None:
        distance_cache = {}

    variables: dict[tuple[int, int, str], Any] = {}
    pairs_by_category: dict[str, tuple[list[int], list[dict[str, Any]]]] = {}
    for category in solve_categories:
        active_zones = [
            zone
            for zone in zone_demands
            if zone["demand_by_category"].get(category, 0) > 0
        ]
        active_depots = [
            depot_id
            for depot_id, supply in depot_supply.items()
            if supply.get(category, 0) > 0
        ]
        pairs_by_category[category] = (active_depots, active_zones)
        for depot_id in active_depots:
            for zone in active_zones:
                variables[(depot_id, zone["zone_id"], category)] = None

    if not variables:
        summaries: list[dict[str, Any]] = []
        for category in solve_categories:
            summaries.extend(_empty_category_summaries(category, zone_demands))
        return summaries, []

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        raise RuntimeError("OR-Tools GLOP solver unavailable")

    for key in list(variables):
        depot_id, zone_id, category = key
        variables[key] = solver.NumVar(
            0.0,
            solver.infinity(),
            f"x_{depot_id}_{zone_id}_{category}",
        )

    objective = solver.Objective()
    coeff_cache: dict[tuple[int, int], float] = {}
    for depot_id, zone_id, category in variables:
        cache_key = (depot_id, zone_id)
        if cache_key not in coeff_cache:
            depot = depots[depot_id]
            zone = next(z for z in zone_demands if z["zone_id"] == zone_id)
            distance = _cached_route_distance_km(
                distance_cache,
                depot_id,
                depot.latitude,
                depot.longitude,
                zone_id,
                zone["latitude"],
                zone["longitude"],
                depot_name=depot.name,
                zone_name=zone["zone_name"],
            )
            coeff_cache[cache_key] = allocation_objective_coefficient(
                zone["priority_weight"],
                distance,
            )
        objective.SetCoefficient(variables[(depot_id, zone_id, category)], coeff_cache[cache_key])
    objective.SetMaximization()

    for category, (active_depots, active_zones) in pairs_by_category.items():
        for depot_id in active_depots:
            constraint = solver.Constraint(0.0, depot_supply[depot_id][category])
            for zone in active_zones:
                constraint.SetCoefficient(
                    variables[(depot_id, zone["zone_id"], category)], 1.0
                )
        for zone in active_zones:
            demand = zone["demand_by_category"].get(category, 0.0)
            constraint = solver.Constraint(0.0, demand)
            for depot_id in active_depots:
                constraint.SetCoefficient(
                    variables[(depot_id, zone["zone_id"], category)], 1.0
                )

    if depot_capacity_kg is not None:
        participating_depots = {depot_id for depot_id, _zone_id, _cat in variables}
        for depot_id in participating_depots:
            cap_kg = float(depot_capacity_kg.get(depot_id, DEFAULT_DEPOT_DAILY_PAYLOAD_KG))
            constraint = solver.Constraint(0.0, cap_kg)
            for zone_id, category in {
                (z, c) for d, z, c in variables if d == depot_id
            }:
                unit_kg = float(weights.get(category, 1.0))
                constraint.SetCoefficient(
                    variables[(depot_id, zone_id, category)],
                    unit_kg,
                )

    status = solver.Solve()
    optimization_status = (
        "optimal" if status == pywraplp.Solver.OPTIMAL else "feasible_or_partial"
    )

    allocated_by_zone_category: dict[tuple[int, str], float] = {}
    flows: list[dict[str, Any]] = []
    for depot_id, zone_id, category in variables:
        allocated = variables[(depot_id, zone_id, category)].solution_value()
        if allocated <= 1e-6:
            continue
        key = (zone_id, category)
        allocated_by_zone_category[key] = (
            allocated_by_zone_category.get(key, 0.0) + allocated
        )
        zone = next(z for z in zone_demands if z["zone_id"] == zone_id)
        flows.append(
            {
                "zone_id": zone_id,
                "zone_name": zone["zone_name"],
                "relief_center_id": depot_id,
                "relief_center_name": depots[depot_id].name,
                "resource_category": category,
                "allocated": round(allocated, 2),
                "route": _cached_road_route(
                    distance_cache,
                    depot_id=depot_id,
                    depot_name=depots[depot_id].name,
                    depot_lat=depots[depot_id].latitude,
                    depot_lon=depots[depot_id].longitude,
                    zone_id=zone_id,
                    zone_name=zone["zone_name"],
                    zone_lat=zone["latitude"],
                    zone_lon=zone["longitude"],
                ),
            }
        )

    summaries: list[dict[str, Any]] = []
    for category in solve_categories:
        active_depots, active_zones = pairs_by_category[category]
        category_status = (
            optimization_status
            if active_depots and active_zones
            else "no_supply_or_demand"
        )
        for zone in zone_demands:
            demanded = zone["demand_by_category"].get(category, 0.0)
            allocated = round(
                allocated_by_zone_category.get((zone["zone_id"], category), 0.0), 2
            )
            summaries.append(
                {
                    "zone_id": zone["zone_id"],
                    "relief_center_id": None,
                    "resource_category": category,
                    "demanded": demanded,
                    "allocated": allocated,
                    "unmet": round(max(demanded - allocated, 0.0), 2),
                    "priority_weight": zone["priority_weight"],
                    "optimization_status": category_status,
                }
            )
    return summaries, flows


def _solve_category_transportation(
    *,
    category: str,
    zone_demands: list[dict[str, Any]],
    depot_supply: dict[int, dict[str, float]],
    depots: dict[int, ReliefCenter],
    distance_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
    depot_capacity_kg: dict[int, float] | None = None,
    unit_weights: dict[str, float] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return _solve_allocation_lp(
        zone_demands=zone_demands,
        depot_supply=depot_supply,
        depots=depots,
        categories=(category,),
        distance_cache=distance_cache,
        depot_capacity_kg=depot_capacity_kg,
        unit_weights=unit_weights,
    )


def optimize_allocation(
    db: Session,
    zone_ids: list[int] | None = None,
    *,
    persist: bool = True,
    reserve_inventory: bool = True,
    max_zones: int | None = None,
    allow_unbounded: bool = False,
) -> dict[str, Any]:
    """Run OR-Tools LP allocation using M2 zone demand and depot inventory."""
    if not zone_ids and not allow_unbounded:
        raise ValueError(
            "zone_ids is required. Passing null/empty runs every Active zone and is "
            "blocked unless allow_unbounded=True."
        )
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
    zone_demands = _zone_demands(db, zone_ids, max_zones=max_zones)
    if not zone_demands:
        return {
            "run_id": None,
            "status": "no_zones",
            "message": "No active disaster zones found for allocation.",
            "allocations": [],
            "flows": [],
        }

    run_id = str(uuid.uuid4())
    distance_cache: dict[tuple[int, int], dict[str, Any]] = {}
    teams = (
        db.query(FieldTeam)
        .filter(FieldTeam.status != INACTIVE_FIELD_TEAM_STATUS)
        .all()
    )
    depot_capacity_kg = compute_depot_transport_capacity_kg(depots, teams)
    all_summaries, all_flows = _solve_allocation_lp(
        zone_demands=zone_demands,
        depot_supply=depot_supply,
        depots=depots,
        distance_cache=distance_cache,
        depot_capacity_kg=depot_capacity_kg,
    )

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