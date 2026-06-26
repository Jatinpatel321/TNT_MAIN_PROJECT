from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(150), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Integer, nullable=False)  # paise
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    
    # Food-specific fields
    prep_time_minutes = Column(Integer, nullable=True)  # preparation time
    available_quantity = Column(Integer, nullable=True, default=0)  # stock count
    is_veg = Column(Boolean, default=True, nullable=True)  # vegetarian flag
    
    # Category: "food" or "stationery"
    category = Column(String(50), default="food", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
    
    # Relationships
    vendor = relationship("User", back_populates="menu_items")
    inventory = relationship("Inventory", back_populates="menu_item", uselist=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False, unique=True)
    
    current_stock = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=10)
    last_restocked_at = Column(DateTime, nullable=True)
    
    # Auto-disable when out of stock
    auto_disable = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="inventory")
