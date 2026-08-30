from sqlalchemy import CheckConstraint, Column, Integer, String

from app.database.connection import Base


class ResourceInventory(Base):
    __tablename__ = "resource_inventory"
    __table_args__ = (
        CheckConstraint(
            "reserved_quantity + in_transit_quantity <= quantity",
            name="ck_resource_inventory_tracking_lte_quantity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    resource_name = Column(String, nullable=False)

    category = Column(String, nullable=False)

    quantity = Column(Integer, nullable=False)

    reserved_quantity = Column(Integer, nullable=False, default=0)

    in_transit_quantity = Column(Integer, nullable=False, default=0)

    unit = Column(String, nullable=False)

    warehouse = Column(String, nullable=False)

    status = Column(String, nullable=False)