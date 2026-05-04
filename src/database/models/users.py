from sqlalchemy import Column, Integer, String
from src.database.base import Base


class Users(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True)
    password = Column(String)
    status = Column(String(255), default="active")
