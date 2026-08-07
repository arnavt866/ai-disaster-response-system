from sqlalchemy.orm import Session

from app.models.relief_center import ReliefCenter
from app.schemas.relief_center import ReliefCenterCreate


def create_relief_center(db: Session, center: ReliefCenterCreate) -> ReliefCenter:
    db_center = ReliefCenter(**center.model_dump())

    db.add(db_center)
    db.commit()
    db.refresh(db_center)

    return db_center


def get_all_relief_centers(db: Session) -> list[ReliefCenter]:
    return db.query(ReliefCenter).all()

def get_relief_center_by_id(
    db: Session,
    center_id: int
) -> ReliefCenter | None:

    return (
        db.query(ReliefCenter)
        .filter(ReliefCenter.id == center_id)
        .first()
    )

def update_relief_center(
    db: Session,
    center_id: int,
    updated_center: ReliefCenterCreate
) -> ReliefCenter | None:

    center = (
        db.query(ReliefCenter)
        .filter(ReliefCenter.id == center_id)
        .first()
    )

    if center is None:
        return None

    center.name = updated_center.name
    center.address = updated_center.address
    center.latitude = updated_center.latitude
    center.longitude = updated_center.longitude
    center.capacity = updated_center.capacity
    center.available_capacity = updated_center.available_capacity
    center.contact_number = updated_center.contact_number
    center.status = updated_center.status

    db.commit()

    db.refresh(center)

    return center

def delete_relief_center(
    db: Session,
    center_id: int
) -> ReliefCenter | None:

    center = (
        db.query(ReliefCenter)
        .filter(ReliefCenter.id == center_id)
        .first()
    )

    if center is None:
        return None

    db.delete(center)

    db.commit()

    return center