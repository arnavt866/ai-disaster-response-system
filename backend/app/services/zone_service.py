from sqlalchemy.orm import Session

from app.models.disaster_zone import DisasterZone
from app.schemas.disaster_zone import DisasterZoneCreate


def create_zone(db: Session, zone: DisasterZoneCreate) -> DisasterZone:

    db_zone = DisasterZone(**zone.model_dump())

    db.add(db_zone)

    db.commit()

    db.refresh(db_zone)

    return db_zone


def get_all_zones(db: Session) -> list[DisasterZone]:

    return db.query(DisasterZone).all()

def get_zone_by_id(
    db: Session,
    zone_id: int
) -> DisasterZone | None:

    return (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

def update_zone(
    db: Session,
    zone_id: int,
    updated_zone: DisasterZoneCreate
) -> DisasterZone | None:

    zone = (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

    if zone is None:
        return None

    zone.zone_name = updated_zone.zone_name
    zone.disaster_type = updated_zone.disaster_type
    zone.severity = updated_zone.severity
    zone.latitude = updated_zone.latitude
    zone.longitude = updated_zone.longitude
    zone.affected_population = updated_zone.affected_population
    zone.status = updated_zone.status

    db.commit()

    db.refresh(zone)

    return zone

def delete_zone(
    db: Session,
    zone_id: int
) -> DisasterZone | None:

    zone = (
        db.query(DisasterZone)
        .filter(DisasterZone.id == zone_id)
        .first()
    )

    if zone is None:
        return None

    db.delete(zone)

    db.commit()

    return zone