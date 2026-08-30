from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, Integer, String

from app.database.connection import Base


class DisasterZone(Base):
    __tablename__ = "disaster_zones"

    id = Column(Integer, primary_key=True, index=True)

    zone_name = Column(String, nullable=False)

    disaster_type = Column(String, nullable=False)

    severity = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    affected_population = Column(Integer, nullable=False)

    status = Column(String, default="Active")

    operational_priority = Column(String, nullable=False, default="Moderate")