from sqlalchemy import Column, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from config.database import Base
from sqlalchemy.sql import func

class Affiliates(Base):
    __tablename__ = "affiliates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)  # Relación con la tabla de usuarios
    affiliate_level = Column(Integer, default=1)  # Nivel del afiliado (1, 2, 3, ...)
    created_at = Column(DateTime,  default=func.now())  # Fecha de creación