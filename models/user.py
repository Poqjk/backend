import uuid
from config.database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String)
    password = Column(String)
    balance_real = Column(String, default="0")
    balance_demo = Column(String, default="10000.00")
    account_mode = Column(Integer, default=0) # 0 = Demo | 1 = Real
    created_at = Column(DateTime, default=func.now())  
    updated_at = Column(DateTime, default=func.now())
    last_connection  = Column(DateTime, default=func.now())
    role = Column(String, default="user")
    firstname = Column(String, default="")
    lastname = Column(String, default="") 
    birthday = Column(Date, default=func.current_date())
    country = Column(String, default="")
    phone_number = Column(String, default="")
    accept_terms = Column(Boolean, default=True)
    newsletter = Column(Boolean, default=False)
    refreshToken = Column(String, default="")
    block = Column(Boolean, default=False)
    is_affiliate = Column(Boolean, default=False)
    affiliated_code = Column(String, nullable=True)
    # Define the relationship to Operation
    operations = relationship("Operation", back_populates="user")  
    payments = relationship("Payment", back_populates="user")  
    withdraws = relationship("Withdraw", back_populates="user", foreign_keys="Withdraw.user_id")
    admin_withdraws = relationship("Withdraw", back_populates="admin", foreign_keys="Withdraw.admin_id")  # Added admin relationship # Added admin relationship