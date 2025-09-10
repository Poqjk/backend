import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from config.database import Base

# Definición del enum para el estado del pago
class PaymentStatusEnum(enum.Enum):
    waiting = "waiting"               # Waiting for the customer to send the payment (initial status)
    confirming = "confirming"         # Transaction is being processed on the blockchain
    confirmed = "confirmed"           # Funds have accumulated enough confirmations
    sending = "sending"               # Funds are being sent to your personal wallet
    partially_paid = "partially_paid" # Customer sent less than the actual price
    finished = "finished"             # Payment is finished (funds reached the personal address)
    failed = "failed"                 # Payment wasn't completed due to an error
    refunded = "refunded"             # Funds were refunded back to the user
    expired = "expired"               # User didn't send funds within the specified time window

class Payment(Base):
    __tablename__ = "payments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String)
    amount = Column(String)
    currency = Column(String)  # e.g. "usdt", "usd"
    type = Column(String)      # e.g. "Crypto", "cards"
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))  # Foreign key to User
    # Usamos el enum para el status con un valor por defecto de "waiting"
    status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.waiting, nullable=False)
    country = Column(String)
    affiliate_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    
    # Define la relación con User
    user = relationship("User", back_populates="payments")
