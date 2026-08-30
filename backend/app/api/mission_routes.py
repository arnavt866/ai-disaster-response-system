"""Mission assignment routes."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.mission import (
    MissionCreate,
    MissionResponse,
    MissionStatusUpdate,
    MissionTeamAssign,
)
from app.services.optimization.mission_service import (
    assign_mission_field_team,
    create_mission,
    get_mission,
    list_missions,
    update_mission_status,
)

router = APIRouter(prefix="/missions", tags=["Missions"])


@router.get("/", response_model=list[MissionResponse])
def get_missions(limit: int = 100, db: Session = Depends(get_db)):
    return list_missions(db, limit=limit)


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission_by_id(mission_id: int, db: Session = Depends(get_db)):
    mission = get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("/", response_model=MissionResponse)
def create_mission_endpoint(request: MissionCreate, db: Session = Depends(get_db)):
    try:
        return create_mission(
            db,
            zone_id=request.zone_id,
            field_team_id=request.field_team_id,
            relief_center_id=request.relief_center_id,
            priority=request.priority,
            resources_payload=request.resources_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{mission_id}/status", response_model=MissionResponse)
def update_status(
    mission_id: int,
    request: MissionStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_mission_status(db, mission_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{mission_id}/team", response_model=MissionResponse)
def assign_team(
    mission_id: int,
    request: MissionTeamAssign,
    db: Session = Depends(get_db),
):
    try:
        return assign_mission_field_team(db, mission_id, request.field_team_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{mission_id}/resources")
def get_mission_resources(mission_id: int, db: Session = Depends(get_db)):
    mission = get_mission(db, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    payload = {}
    if mission.resources_payload:
        payload = json.loads(mission.resources_payload)
    return {"mission_id": mission.id, "resources": payload}
