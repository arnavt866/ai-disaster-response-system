from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.connection import Base


class NdmaAlert(Base):
    """SACHET CAP early-warning alert. Not a confirmed disaster_event."""

    __tablename__ = "ndma_alerts"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, unique=True, nullable=False, index=True)
    cap_identifier = Column(String, nullable=True, index=True)
    etag = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    sent = Column(DateTime, nullable=True)
    msg_status = Column(String, nullable=True)
    msg_type = Column(String, nullable=True)
    category = Column(String, nullable=True)
    event = Column(String, nullable=True)
    urgency = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    certainty = Column(String, nullable=True)
    headline = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    instruction = Column(Text, nullable=True)
    area_description = Column(Text, nullable=True)
    area_polygon = Column(Text, nullable=True)
    area_circle = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    effective = Column(DateTime, nullable=True)
    onset = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="Active", index=True)
    source = Column(String, nullable=False, default="NDMA SACHET")
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
