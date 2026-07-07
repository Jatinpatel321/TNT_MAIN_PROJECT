import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class LedgerType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class LedgerSource(enum.Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    VOUCHER = "voucher"
    ADJUSTMENT = "adjustment"


class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)

    # Nullable so admin manual adjustments need not be tied to an order.
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    # Admin user id for manual adjustments (attribution); null for auto entries.
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    amount = Column(Integer, nullable=False)  # paise
    entry_type = Column(Enum(LedgerType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    source = Column(Enum(LedgerSource, values_callable=lambda x: [e.value for e in x]), nullable=False)

    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)
