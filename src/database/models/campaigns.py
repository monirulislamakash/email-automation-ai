from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import relationship
from src.database.base import Base


class Campaigns(Base):
    __tablename__ = "Campaigns"

    id = Column(Integer, primary_key=True)
    campaign_name = Column(String)
    campaign_id = Column(String, unique=True, default=None)
    campaign_status = Column(Integer, default=0)
    campaign_schedule = Column(JSON)
    options_settings = Column(JSON)
    status = Column(String(255), default="inactive")

    leads = relationship(
        "Leads",
        back_populates="campaign",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    custom_prompts = relationship(
        "CustomPrompts", 
        back_populates="campaign", 
        cascade="all, delete-orphan", 
        passive_deletes=True,
    )
