from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from src.database.base import Base


class Notifications(Base):
    __tablename__ = "Notifications"
    id = Column(Integer, primary_key=True)
    notification = Column(JSON, nullable=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=True)
