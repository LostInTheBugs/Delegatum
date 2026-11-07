from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class UpdateConfig(Base):
    __tablename__ = "update_config"

    key = Column(String(64), primary_key=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
