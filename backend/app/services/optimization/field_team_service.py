"""Field team management."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.field_team import FieldTeam


def list_field_teams(db: Session) -> list[FieldTeam]:
    return db.query(FieldTeam).order_by(FieldTeam.team_name.asc()).all()


def get_field_team(db: Session, team_id: int) -> FieldTeam | None:
    return db.query(FieldTeam).filter(FieldTeam.id == team_id).first()


def create_field_team(
    db: Session,
    *,
    team_name: str,
    vehicle_type: str | None = None,
    vehicle_capacity: int = 0,
    contact_number: str | None = None,
    base_latitude: float | None = None,
    base_longitude: float | None = None,
) -> FieldTeam:
    team = FieldTeam(
        team_name=team_name,
        vehicle_type=vehicle_type,
        vehicle_capacity=vehicle_capacity,
        contact_number=contact_number,
        base_latitude=base_latitude,
        base_longitude=base_longitude,
        status="Available",
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def update_field_team_status(db: Session, team_id: int, status: str) -> FieldTeam:
    team = get_field_team(db, team_id)
    if team is None:
        raise ValueError(f"Field team {team_id} not found")
    team.status = status
    db.commit()
    db.refresh(team)
    return team
