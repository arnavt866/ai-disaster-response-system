from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text

from app.database.connection import Base


class SatelliteAssessment(Base):
    """Copernicus EMS Rapid Mapping polygons (observed, not AI-detected)."""

    __tablename__ = "satellite_assessments"

    id = Column(Integer, primary_key=True, index=True)
    activation_code = Column(String, nullable=False, index=True)
    event_name = Column(String, nullable=False)
    event_date = Column(Date, nullable=True)
    product_type = Column(String, nullable=False, index=True)
    source_url = Column(String, nullable=True)
    geometry = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False)
    classification = Column(String, nullable=True)
    area_m2 = Column(Float, nullable=True)
    source_license = Column(Text, nullable=True)
    imported_at = Column(DateTime, nullable=False, default=datetime.utcnow)
