from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.database.connection import Base


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    mission_code = Column(String, nullable=False, unique=True, index=True)
    zone_id = Column(Integer, ForeignKey("disaster_zones.id"), nullable=False, index=True)
    field_team_id = Column(Integer, ForeignKey("field_teams.id"), nullable=True)
    relief_center_id = Column(Integer, ForeignKey("relief_centers.id"), nullable=True)
    priority = Column(String, nullable=False, default="Moderate")
    status = Column(String, nullable=False, default="Created")
    route_distance_km = Column(Float, nullable=True)
    route_eta_hours = Column(Float, nullable=True)
    route_status = Column(String, nullable=False, default="planned")
    resources_payload = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
