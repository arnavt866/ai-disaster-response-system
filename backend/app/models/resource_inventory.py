from sqlalchemy import Column, Integer, String
from app.database.connection import Base


class ResourceInventory(Base):
    __tablename__ = "resource_inventory"

    id = Column(Integer, primary_key=True, index=True)

    resource_name = Column(String, nullable=False)

    category = Column(String, nullable=False)

    quantity = Column(Integer, nullable=False)

    unit = Column(String, nullable=False)

    warehouse = Column(String, nullable=False)

    status = Column(String, nullable=False)