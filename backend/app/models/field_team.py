from sqlalchemy import Column, Float, Integer, String

from app.database.connection import Base


class FieldTeam(Base):
    __tablename__ = "field_teams"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Available")
    vehicle_type = Column(String, nullable=True)
    vehicle_capacity = Column(Integer, nullable=False, default=0)
    contact_number = Column(String, nullable=True)
    base_latitude = Column(Float, nullable=True)
    base_longitude = Column(Float, nullable=True)
