import enum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class RewardType(enum.Enum):
    ORDER_COMPLETION = "order_completion"
    REFERRAL = "referral"
    FIRST_ORDER = "first_order"
    LOYALTY_MILESTONE = "loyalty_milestone"
    OFF_PEAK_BONUS = "off_peak_bonus"
    VOUCHER_REDEMPTION = "voucher_redemption"


class RedemptionType(enum.Enum):
    DISCOUNT_PERCENTAGE = "discount_percentage"
    DISCOUNT_FIXED = "discount_fixed"
    FREE_ITEM = "free_item"


class VoucherDiscountType(enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class RewardPoints(Base):
    __tablename__ = "reward_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    points = Column(Float, nullable=False, default=0.0)  # Allow decimal points
    total_earned = Column(Float, nullable=False, default=0.0)
    total_redeemed = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class RewardTransaction(Base):
    __tablename__ = "reward_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_type = Column(Enum(RewardType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    points = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redemption_type = Column(Enum(RedemptionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    points_used = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # discount amount or item value
    description = Column(String, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)


class RewardRule(Base):
    __tablename__ = "reward_rules"

    id = Column(Integer, primary_key=True, index=True)
    reward_type = Column(Enum(RewardType, values_callable=lambda x: [e.value for e in x]), nullable=False, unique=True)
    points_per_rupee = Column(Float, nullable=False, default=1.0)  # Points earned per rupee spent
    fixed_points = Column(Float, nullable=True)  # Fixed points for certain actions
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class RedemptionRule(Base):
    __tablename__ = "redemption_rules"

    id = Column(Integer, primary_key=True, index=True)
    redemption_type = Column(Enum(RedemptionType, values_callable=lambda x: [e.value for e in x]), nullable=False, unique=True)
    min_points = Column(Float, nullable=False)
    max_discount_percentage = Column(Float, nullable=True)  # For percentage discounts
    max_discount_amount = Column(Float, nullable=True)  # For fixed discounts
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=False)
    discount_type = Column(Enum(VoucherDiscountType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    discount_value = Column(Float, nullable=False)
    min_order_amount_paise = Column(Integer, nullable=False, default=0)
    max_discount_amount_paise = Column(Integer, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    times_redeemed = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VoucherRedemption(Base):
    __tablename__ = "voucher_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    discount_amount_paise = Column(Integer, nullable=False)
    redeemed_at = Column(DateTime, default=utcnow_naive)


class OffPeakRewardPolicy(Base):
    __tablename__ = "offpeak_reward_policies"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Integer, nullable=False, default=0)
    start_hour = Column(Integer, nullable=False, default=15)
    end_hour = Column(Integer, nullable=False, default=17)
    bonus_points_per_order = Column(Float, nullable=False, default=10.0)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class OffPeakRewardPolicyAudit(Base):
    __tablename__ = "offpeak_reward_policy_audit"

    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Integer, nullable=False)
    start_hour = Column(Integer, nullable=False)
    end_hour = Column(Integer, nullable=False)
    bonus_points_per_order = Column(Float, nullable=False)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=utcnow_naive)
