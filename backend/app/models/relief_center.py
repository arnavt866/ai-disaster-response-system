from sqlalchemy import Column, Integer, String, Float
from app.database.connection import Base


class ReliefCenter(Base):
    __tablename__ = "relief_centers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    address = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    capacity = Column(Integer, nullable=False)

    available_capacity = Column(Integer, nullable=False)

    contact_number = Column(String)

    status = Column(String, default="Active")