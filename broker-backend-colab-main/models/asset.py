import uuid
from config.database import Base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Asset(Base):
    __tablename__ = "assets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    active_id = Column(String)
    name = Column(String)
    type = Column(String)
    status = Column(Boolean, default=True)  # 0 = Demo | 1 = Real
    profit = Column(Float, default=1.8) # 80%
    custom_profit = Column(Float, default=1.4) # 40%
    available_broker = Column(Boolean, default=True)
    in_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())  
    updated_at = Column(DateTime, default=func.now())

    # Define the relationship to Operation
    operations = relationship("Operation", back_populates="asset")