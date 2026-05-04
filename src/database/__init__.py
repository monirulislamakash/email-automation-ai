from src.database.base import Base
from src.database.session import engine
from src.database.models import (
    Users,
    Campaigns,
    leads,
    credentials,
    CustomPrompts,
    GlobalPrompts,
    Notifications,
)

Base.metadata.create_all(engine)
