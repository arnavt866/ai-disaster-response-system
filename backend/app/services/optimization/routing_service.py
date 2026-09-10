"""Haversine routing between depots (relief centers) and disaster zones."""

from __future__ import annotations

import logging
import math
from typing import Any

from app.services.optimization.constants import AVG_TRUCK_SPEED_KPH

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def route_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Road-network distance when the pair is in a cached demo region; else Haversine.

    Matches ``build_road_route`` coverage and fallback: never raises to callers.
    """
    try:
        from app.services.optimization.road_graph import compute_road_path

        road = compute_road_path(lat1, lon1, lat2, lon2)
        if road is not None:
            return float(road.distance_km)
    except Exception as exc:
        logger.warning(
            "Road distance lookup failed; using Haversine fallback: %s",
            exc,
        )
    return haversine_km(lat1, lon1, lat2, lon2)


def build_route(
    *,
    depot_id: int,
    depot_name: str,
    depot_lat: float,
    depot_lon: float,
    zone_id: int,
    zone_name: str,
    zone_lat: float,
    zone_lon: float,
    blocked: bool = False,
) -> dict[str, Any]:
    """Return route metadata using straight-line distance as a road proxy."""
    distance_km = haversine_km(depot_lat, depot_lon, zone_lat, zone_lon)
    eta_hours = distance_km / AVG_TRUCK_SPEED_KPH if AVG_TRUCK_SPEED_KPH > 0 else 0.0
    feasible = not blocked
    return {
        "depot_id": depot_id,
        "depot_name": depot_name,
        "zone_id": zone_id,
        "zone_name": zone_name,
        "distance_km": round(distance_km, 2),
        "estimated_travel_hours": round(eta_hours, 2),
        "route_status": "blocked" if blocked else "open",
        "feasible": feasible,
        "routing_method": "haversine_distance_prototype",
        "routing_label": "Distance-based prototype routing (not road-network optimized)",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [depot_lon, depot_lat],
                [zone_lon, zone_lat],
            ],
        },
        "note": (
            "Route uses Haversine straight-line distance as a proxy. "
            "Real-time road closure data is not integrated."
        ),
    }


def build_road_route(
    *,
    depot_id: int,
    depot_name: str,
    depot_lat: float,
    depot_lon: float,
    zone_id: int,
    zone_name: str,
    zone_lat: float,
    zone_lon: float,
    blocked: bool = False,
) -> dict[str, Any]:
    """
    Try OSM road-network routing for demo depot regions; fall back to Haversine.

    Never raises to callers — logs a warning and returns build_route() on failure.
    """
    if blocked:
        return build_route(
            depot_id=depot_id,
            depot_name=depot_name,
            depot_lat=depot_lat,
            depot_lon=depot_lon,
            zone_id=zone_id,
            zone_name=zone_name,
            zone_lat=zone_lat,
            zone_lon=zone_lon,
            blocked=blocked,
        )

    try:
        from app.services.optimization.road_graph import compute_road_path

        road = compute_road_path(depot_lat, depot_lon, zone_lat, zone_lon)
        if road is not None:
            distance_km = road.distance_km
            eta_hours = (
                distance_km / AVG_TRUCK_SPEED_KPH if AVG_TRUCK_SPEED_KPH > 0 else 0.0
            )
            return {
                "depot_id": depot_id,
                "depot_name": depot_name,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "distance_km": distance_km,
                "estimated_travel_hours": round(eta_hours, 2),
                "route_status": "open",
                "feasible": True,
                "routing_method": "road_network_local_osm",
                "routing_label": "Road-network routing (local OSM PBF + NetworkX shortest path)",
                "region_id": road.region_id,
                "path_edges": road.edges,
                "geometry": {
                    "type": "LineString",
                    "coordinates": road.coordinates,
                },
                "note": (
                    "Route follows the cached local OSM drive network for the demo "
                    "depot region. Falls back to Haversine when out of coverage or "
                    "when all road paths are blocked."
                ),
            }
    except Exception as exc:
        logger.warning(
            "Road routing failed for depot %s -> zone %s; using Haversine fallback: %s",
            depot_id,
            zone_id,
            exc,
        )

    return build_route(
        depot_id=depot_id,
        depot_name=depot_name,
        depot_lat=depot_lat,
        depot_lon=depot_lon,
        zone_id=zone_id,
        zone_name=zone_name,
        zone_lat=zone_lat,
        zone_lon=zone_lon,
        blocked=blocked,
    )


def nearest_depot(
    zone_lat: float,
    zone_lon: float,
    depots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not depots:
        return None
    ranked = sorted(
        depots,
        key=lambda depot: route_distance_km(
            zone_lat, zone_lon, depot["latitude"], depot["longitude"]
        ),
    )
    nearest = ranked[0]
    route = build_road_route(
        depot_id=nearest["id"],
        depot_name=nearest["name"],
        depot_lat=nearest["latitude"],
        depot_lon=nearest["longitude"],
        zone_id=nearest.get("zone_id", 0),
        zone_name=nearest.get("zone_name", ""),
        zone_lat=zone_lat,
        zone_lon=zone_lon,
    )
    return route
