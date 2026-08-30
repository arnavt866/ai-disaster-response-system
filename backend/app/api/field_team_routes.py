"""Field team management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.field_team import (
    FieldTeamCreate,
    FieldTeamResponse,
    FieldTeamStatusUpdate,
)
from app.services.optimization.field_team_service import (
    create_field_team,
    get_field_team,
    list_field_teams,
    update_field_team_status,
)

router = APIRouter(prefix="/field-teams", tags=["Field Teams"])


@router.get("/", response_model=list[FieldTeamResponse])
def get_field_teams(db: Session = Depends(get_db)):
    return list_field_teams(db)


@router.post("/", response_model=FieldTeamResponse)
def create_team(request: FieldTeamCreate, db: Session = Depends(get_db)):
    return create_field_team(db, **request.model_dump())


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
