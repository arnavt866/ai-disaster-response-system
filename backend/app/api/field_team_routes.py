"""Field team management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.field_team import (
    FieldTeamCreate,
    FieldTeamResponse,
    FieldTeamStatusUpdate,
    FieldTeamUpdate,
)
from app.services.optimization.field_team_service import (
    create_field_team,
    deactivate_field_team,
    get_field_team,
    list_field_teams,
    update_field_team,
    update_field_team_status,
)

router = APIRouter(prefix="/field-teams", tags=["Field Teams"])


@router.get("/", response_model=list[FieldTeamResponse])
def get_field_teams(db: Session = Depends(get_db)):
    return list_field_teams(db)


@router.post("/", response_model=FieldTeamResponse)
def create_team(request: FieldTeamCreate, db: Session = Depends(get_db)):
    return create_field_team(db, **request.model_dump())


@router.get("/{team_id}", response_model=FieldTeamResponse)
def get_team_by_id(team_id: int, db: Session = Depends(get_db)):
    team = get_field_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Field team not found")
    return team


@router.put("/{team_id}", response_model=FieldTeamResponse)
def update_team(
    team_id: int,
    request: FieldTeamUpdate,
    db: Session = Depends(get_db),
):
    team = update_field_team(db, team_id, request)
    if team is None:
        raise HTTPException(status_code=404, detail="Field team not found")
    return team


@router.patch("/{team_id}/status", response_model=FieldTeamResponse)
def update_team_status(
    team_id: int,
    request: FieldTeamStatusUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_field_team_status(db, team_id, request.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{team_id}", response_model=FieldTeamResponse)
def deactivate_team(team_id: int, db: Session = Depends(get_db)):
    team = deactivate_field_team(db, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Field team not found")
    return team
