import uuid
from config.database import Base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
class Operation(Base):
    __tablename__ = "operations"
    operation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry = Column(String)
    close = Column(String, default="0")
    time_start = Column(BigInteger)
    time_end = Column(BigInteger)
    timer = Column(Integer)
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id'))  # Foreign key to Asset
    winner = Column(Boolean, default=False)
    direction = Column(String)
    amount = Column(String)
    income = Column(String, default="0")
    operation_mode = Column(Integer, default=0) # 0 = Demo | 1 = Real
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))  # Foreign key to User
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    closed_at = Column(DateTime, default=func.now())    
    # Define the relationship to User
    user = relationship("User", back_populates="operations")

     # Define the relationship to Asset
    asset = relationship("Asset", back_populates="operations")