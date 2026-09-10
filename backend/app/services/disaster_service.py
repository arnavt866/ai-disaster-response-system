from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.disaster_event import DisasterEvent
from app.schemas.disaster_event import DisasterEventCreate


def create_disaster(db: Session, disaster: DisasterEventCreate):

    db_disaster = DisasterEvent(**disaster.model_dump())

    try:
        db.add(db_disaster)
        db.commit()
        db.refresh(db_disaster)
        return db_disaster

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Event ID already exists."
        )


def get_all_disasters(
    db: Session,
) -> list[DisasterEvent]:
    return db.query(DisasterEvent).order_by(DisasterEvent.id.asc()).all()


def list_disasters(
    db: Session,
    *,
    offset: int,
    limit: int,
) -> tuple[int, list[DisasterEvent]]:
    query = db.query(DisasterEvent)
    total = query.count()
    rows = (
        query.order_by(DisasterEvent.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, rows

def get_disaster_by_id(
    db: Session,
    disaster_id: int
) -> DisasterEvent | None:

    return (
        db.query(DisasterEvent)
        .filter(DisasterEvent.id == disaster_id)
        .first()
    )

def update_disaster(
    db: Session,
    disaster_id: int,
    updated_disaster: DisasterEventCreate
) -> DisasterEvent | None:

    disaster = (
        db.query(DisasterEvent)
        .filter(DisasterEvent.id == disaster_id)
        .first()
    )

    if disaster is None:
        return None

    disaster.event_id = updated_disaster.event_id
    disaster.title = updated_disaster.title
    disaster.disaster_type = updated_disaster.disaster_type
    disaster.magnitude = updated_disaster.magnitude
    disaster.latitude = updated_disaster.latitude
    disaster.longitude = updated_disaster.longitude
    disaster.location = updated_disaster.location
    disaster.severity = updated_disaster.severity
    disaster.status = updated_disaster.status
    disaster.source = updated_disaster.source
    disaster.event_time = updated_disaster.event_time

    try:

        db.commit()

        db.refresh(disaster)

        return disaster

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Event ID already exists."
        )

def delete_disaster(
    db: Session,
    disaster_id: int
) -> DisasterEvent | None:

    disaster = (
        db.query(DisasterEvent)
        .filter(DisasterEvent.id == disaster_id)
        .first()
    )

    if disaster is None:
        return None

    db.delete(disaster)

    db.commit()

    return disaster