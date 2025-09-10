from sqlalchemy import Column, ForeignKey, DateTime, String, Enum
from sqlalchemy.dialects.postgresql import UUID
from config.database import Base
import uuid
from sqlalchemy.sql import func
import enum

class LinkProgram(enum.Enum):
    income_split = "income_split"
    total_billing = "total_billing"

class LinkTypeEnum(enum.Enum):
    MainPage = "MainPage"
    RegisterLink = "RegisterLink"
    

class AffiliateLinks(Base):
    __tablename__ = "affiliate_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)  # Relación con el afiliado
    affiliate_program = Column(Enum(LinkProgram), nullable=False)  # Tipo de enlace: "income_split" o "total_billing"
    link_type = Column(Enum(LinkTypeEnum), nullable=False)
    link_code = Column(String, unique=True, nullable=False)  # Código único del enlace
    comment = Column(String, default="")
    created_at = Column(DateTime,  default=func.now())  # Fecha de creación