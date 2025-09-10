from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid
from sqlalchemy.sql import func

class AffiliateReferrals(Base):
    __tablename__ = "affiliate_referrals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)  # Relación con el afiliado
    referred_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)  # Relación con el usuario referido
    referred_at = Column(DateTime,  default=func.now())  # Fecha y hora de la referencia