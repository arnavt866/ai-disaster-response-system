from sqlalchemy import Column, Float, Integer

from app.database.connection import Base


class Building(Base):

    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)

    osm_id = Column(Integer, unique=True, nullable=False, index=True)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)