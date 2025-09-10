from sqlalchemy import Column, ForeignKey, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid
from sqlalchemy.sql import func

class AffiliateClicks(Base):
    __tablename__ = "affiliate_clicks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)  # Relación con el afiliado
    link_id = Column(UUID(as_uuid=True), ForeignKey("affiliate_links.id"), nullable=False)
    clicked_at = Column(DateTime,  default=func.now())  # Fecha y hora del click
    ip_address = Column(String, nullable=True)  # IP del usuario (opcional)
    user_agent = Column(String, nullable=True)  # User-Agent del navegador (opcional)