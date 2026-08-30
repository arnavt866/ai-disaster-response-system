"""Mission lifecycle management."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.field_team import FieldTeam
from app.models.mission import Mission
from app.models.relief_center import ReliefCenter
from app.services.optimization.constants import MISSION_STATUSES
from app.services.optimization.resource_tracking_service import (
    VALID_TRANSITIONS,
    deliver_in_transit_for_mission_items,
    dispatch_reserved_for_mission_items,
)
from app.services.optimization.routing_service import build_road_route
from app.services.optimization.field_team_service import get_field_team
from app.services.zone_service import get_zone_by_id


def _next_mission_code() -> str:
    return f"MSN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"


def _payload_items(resources_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not resources_payload:
        return []
    flows = resources_payload.get("flows")
    if isinstance(flows, list) and flows:
        return flows
    items = resources_payload.get("items")
    return items if isinstance(items, list) else []


def create_mission(
    db: Session,
    *,
    zone_id: int,
    field_team_id: int | None = None,
    relief_center_id: int | None = None,
    priority: str = "Moderate",
    resources_payload: dict[str, Any] | None = None,
) -> Mission:
    zone = get_zone_by_id(db, zone_id)
    if zone is None:
        raise ValueError(f"Disaster zone {zone_id} not found")

    route_distance_km = None
    route_eta_hours = None
    route_status = "planned"
    if relief_center_id is not None:
        depot = db.query(ReliefCenter).filter(ReliefCenter.id == relief_center_id).first()
        if depot is None:
            raise ValueError(f"Relief center {relief_center_id} not found")
        route = build_road_route(
            depot_id=depot.id,
            depot_name=depot.name,
            depot_lat=depot.latitude,
            depot_lon=depot.longitude,
            zone_id=zone.id,
            zone_name=zone.zone_name,
            zone_lat=zone.latitude,
            zone_lon=zone.longitude,
        )
        route_distance_km = route["distance_km"]
        route_eta_hours = route["estimated_travel_hours"]
        route_status = route["route_status"]

    initial_status = "Allocated" if _payload_items(resources_payload) else "Created"

    mission = Mission(
        mission_code=_next_mission_code(),
        zone_id=zone_id,
        field_team_id=field_team_id,
        relief_center_id=relief_center_id,
        priority=priority or zone.operational_priority or zone.severity,
        status=initial_status,
        route_distance_km=route_distance_km,
        route_eta_hours=route_eta_hours,
        route_status=route_status,
        resources_payload=json.dumps(resources_payload or {}),
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def update_mission_status(db: Session, mission_id: int, status: str) -> Mission:
    if status not in MISSION_STATUSES:
        raise ValueError(f"Invalid mission status: {status}")
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")

    allowed = VALID_TRANSITIONS.get(mission.status, set())
    if status != mission.status and status not in allowed:
        raise ValueError(
            f"Invalid mission transition: {mission.status} -> {status}"
        )

    previous_status = mission.status
    payload = json.loads(mission.resources_payload or "{}")
    items = _payload_items(payload)
    depot_id = mission.relief_center_id

    if items:
        if status == "Dispatched" and previous_status in {"Created", "Allocated"}:
            dispatch_reserved_for_mission_items(db, items, depot_id)
        elif status == "Delivered" and previous_status == "In Transit":
            deliver_in_transit_for_mission_items(db, items, depot_id)

    mission.status = status
    mission.updated_at = datetime.utcnow()

    if mission.field_team_id is not None:
        team = db.query(FieldTeam).filter(FieldTeam.id == mission.field_team_id).first()
        if team is not None:
            if status in {"Dispatched", "In Transit"}:
                team.status = "In Transit"
            elif status == "Delivered":
                team.status = "Available"
            elif status in {"Created", "Allocated"}:
                team.status = "Assigned"

    db.commit()
    db.refresh(mission)
    return mission


def list_missions(db: Session, limit: int = 100) -> list[Mission]:
    return (
        db.query(Mission)
        .order_by(Mission.created_at.desc())
        .limit(limit)
        .all()
    )


def get_mission(db: Session, mission_id: int) -> Mission | None:
    return db.query(Mission).filter(Mission.id == mission_id).first()


def assign_mission_field_team(
    db: Session,
    mission_id: int,
    field_team_id: int,
) -> Mission:
    mission = get_mission(db, mission_id)
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if mission.status == "Delivered":
        raise ValueError("Cannot assign a team to a delivered mission")

    team = get_field_team(db, field_team_id)
    if team is None:
        raise ValueError(f"Field team {field_team_id} not found")
    if team.status != "Available":
        raise ValueError(
            f"Field team {field_team_id} is not Available (status: {team.status})"
        )

    if mission.field_team_id and mission.field_team_id != field_team_id:
        previous_team = get_field_team(db, mission.field_team_id)
        if previous_team is not None:
            previous_team.status = "Available"

    mission.field_team_id = field_team_id
    team.status = "Assigned"
    mission.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(mission)
    return mission
