from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base
from app.modules.orders.model import OrderStatus


class OrderHistory(Base):
    __tablename__ = "order_history"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=False)
    changed_by = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=utcnow_naive)
