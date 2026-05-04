from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from src.database.base import Base


class Leads(Base):
    __tablename__ = "Leads"

    id = Column(Integer, primary_key=True)
    campaign_pk = Column(Integer, ForeignKey("Campaigns.id", ondelete="CASCADE", onupdate="CASCADE"),)

    first_name = Column(String)
    last_name = Column(String)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    conference = Column(String, nullable=True)
    type = Column(String, nullable=True)

    email = Column(String)
    linkedin = Column(String, nullable=True)
    website = Column(String, nullable=True)

    website_data = Column(String, default=None, nullable=True)
    linkedin_data = Column(String, default=None, nullable=True)
    generated_mail = Column(String, default=None)

    campaign_id = Column(String)
    campaign_type = Column(String, default="Fresh")  # Fresh or Follow-Up
    lead_id = Column(String, unique=True, default=None)
    lead_status = Column(Integer, default=None)
    lead_processed_date = Column(Date, default=None)
    email_status = Column(String, default=None, nullable=True)
    email_id = Column(String, unique=True, default=None, nullable=True)
    next_reply_date = Column(DateTime, default=None, nullable=True)
    reply_mail = Column(String, default=None, nullable=True)

    campaign = relationship("Campaigns", back_populates="leads")
