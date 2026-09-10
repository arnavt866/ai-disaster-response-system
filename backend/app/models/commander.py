from sqlalchemy import Column, Integer, String

from app.database.connection import Base


class Commander(Base):
    __tablename__ = "commanders"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="Commander")
