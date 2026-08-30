from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.database.connection import Base


class AllocationRecord(Base):
    __tablename__ = "allocation_records"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)
    zone_id = Column(Integer, ForeignKey("disaster_zones.id"), nullable=False, index=True)
    relief_center_id = Column(Integer, ForeignKey("relief_centers.id"), nullable=False)
    resource_category = Column(String, nullable=False)
    demanded = Column(Float, nullable=False, default=0.0)
    allocated = Column(Float, nullable=False, default=0.0)
    unmet = Column(Float, nullable=False, default=0.0)
    priority_weight = Column(Float, nullable=False, default=1.0)
    optimization_status = Column(String, nullable=False, default="optimal")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
