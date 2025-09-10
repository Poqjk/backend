from sqlalchemy import Column, ForeignKey, DateTime, String, Float
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid
from sqlalchemy.sql import func

class AffiliateTransactions(Base):
    __tablename__ = "affiliate_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_link_id = Column(UUID(as_uuid=True), ForeignKey("affiliate_links.id"), nullable=False)  # Relación con el enlace
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)  # Relación con el cliente referido
    amount = Column(Float, nullable=False)  # Monto de la transacción (pérdidas o volumen)
    transaction_type = Column(String, nullable=False)  # Tipo de transacción: "loss" o "volume"
    created_at = Column(DateTime,  default=func.now())  # Fecha de creación