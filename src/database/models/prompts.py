from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from src.database.base import Base


class GlobalPrompts(Base):
    __tablename__ = "Global_Prompts"
    id = Column(Integer, primary_key=True)
    prompt_name = Column(String, unique=True)
    prompt_value = Column(String)
    status = Column(String(255), default="active")


class CustomPrompts(Base):
    __tablename__ = "Custom_Prompts"
    id = Column(Integer, primary_key=True)
    # Scope prompt names per campaign and keep referential integrity
    campaign_pk = Column(Integer, ForeignKey("Campaigns.id", ondelete="CASCADE", onupdate="CASCADE"),)
    campaign_id = Column(String)
    prompt_name = Column(String)
    prompt_value = Column(String)
    status = Column(String(255), default="active")
    __table_args__ = (
        # no duplicate prompt_name within the same campaign
        UniqueConstraint("campaign_id", "prompt_name", name="uq_campaign_prompt_name"),
    )
    campaign = relationship("Campaigns", back_populates="custom_prompts")
