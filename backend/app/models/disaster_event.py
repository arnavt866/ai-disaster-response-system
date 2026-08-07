from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database.connection import Base


class DisasterEvent(Base):
    __tablename__ = "disaster_events"

    id = Column(Integer, primary_key=True, index=True)

    event_id = Column(String, unique=True, nullable=False)

    title = Column(String, nullable=False)

    disaster_type = Column(String, nullable=False)

    magnitude = Column(Float)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    location = Column(String)

    severity = Column(String)

    status = Column(String, default="Active")

    source = Column(String)

    event_time = Column(DateTime, default=datetime.utcnow)