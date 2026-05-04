from sqlalchemy import Column, Integer, String
from src.database.base import Base


class Credentials(Base):
    __tablename__ = "Credentials"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    value = Column(String)
