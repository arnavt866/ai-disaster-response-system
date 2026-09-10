from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String

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

    population_0_14 = Column(Float, nullable=True)
    population_60_plus = Column(Float, nullable=True)
    elderly_ratio = Column(Float, nullable=True)
    children_ratio = Column(Float, nullable=True)
    vulnerability_source = Column(String, nullable=True)
    vulnerability_data_available = Column(Boolean, nullable=False, default=False)
    vulnerability_computed_at = Column(DateTime, nullable=True)

    @property
    def elderly_share(self) -> float | None:
        return self.elderly_ratio

    @property
    def child_share(self) -> float | None:
        return self.children_ratio