from sqlalchemy import Column, ForeignKey, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid
from sqlalchemy.sql import func


class AffiliateEarnings(Base):
    __tablename__ = "affiliate_earnings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)  # Relación con el afiliado
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("affiliate_transactions.id"), nullable=False)  # Relación con la transacción
    earnings = Column(Float, nullable=False)  # Ganancias del afiliado
    created_at =Column(DateTime,  default=func.now())  # Fecha de la ganancia