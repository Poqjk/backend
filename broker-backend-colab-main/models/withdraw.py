import uuid
from config.database import Base
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

class Withdraw(Base):
    __tablename__ = "withdraws"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))  # Foreign key to User
    admin_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'),nullable=True) 
    amount = Column(String)
    reason = Column(String, default="")
    type = Column(String) # Tether usdt - etc
    network = Column(String, default="")
    address = Column(String, default="") 
    status = Column(String, default="pending") # Expire - Pending - Completed - Reject
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())    
    # Define the relationship to User with foreign_keys specified
    user = relationship("User", back_populates="withdraws", foreign_keys=[user_id])
    admin = relationship("User", back_populates="admin_withdraws", foreign_keys=[admin_id])  # Added admin relationship
