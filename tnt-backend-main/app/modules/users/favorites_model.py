from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class UserFavoriteVendor(Base):
    __tablename__ = "user_favorite_vendors"
    __table_args__ = (UniqueConstraint("user_id", "vendor_id", name="uq_user_favorite_vendor"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow_naive)

    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("User", foreign_keys=[vendor_id])


class UserFavoriteMenuItem(Base):
    __tablename__ = "user_favorite_menu_items"
    __table_args__ = (UniqueConstraint("user_id", "menu_item_id", name="uq_user_favorite_menu_item"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow_naive)

    user = relationship("User", foreign_keys=[user_id])
    menu_item = relationship("MenuItem", foreign_keys=[menu_item_id])
