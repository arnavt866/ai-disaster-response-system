from sqlalchemy import Column, Integer, String, Float
from app.database.connection import Base


class DisasterZone(Base):
    __tablename__ = "disaster_zones"

    id = Column(Integer, primary_key=True, index=True)

    zone_name = Column(String, nullable=False)

    disaster_type = Column(String, nullable=False)

    severity = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    affected_population = Column(Integer, nullable=False)

    status = Column(String, default="Active")