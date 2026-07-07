from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.ledger.model import LedgerSource, LedgerType
from app.modules.ledger.service import add_ledger_entry
from app.modules.orders.model import Order, OrderStatus
from app.modules.rewards.model import (
    RedemptionRule,
    RedemptionType,
    OffPeakRewardPolicy,
    OffPeakRewardPolicyAudit,
    Voucher,
    VoucherDiscountType,
    VoucherRedemption,
    RewardPoints,
    RewardRedemption,
    RewardRule,
    RewardTransaction,
    RewardType,
)
from app.modules.users.model import User


def get_or_create_reward_points(user_id: int, db: Session) -> RewardPoints:
    """Get or create reward points record for user"""
    reward_points = db.query(RewardPoints).filter(RewardPoints.user_id == user_id).first()
    if not reward_points:
        reward_points = RewardPoints(user_id=user_id)
        db.add(reward_points)
        db.commit()
        db.refresh(reward_points)
    return reward_points


def award_points(user_id: int, reward_type: RewardType, points: float, description: str, order_id: int = None, db: Session = None):
    """Award points to user"""
    if db is None:
        from app.database.session import get_db
        db = next(get_db())

    # Create transaction record
    transaction = RewardTransaction(
        user_id=user_id,
        reward_type=reward_type,
        points=points,
        description=description,
        order_id=order_id
    )
    db.add(transaction)

    # Update points balance
    reward_points = get_or_create_reward_points(user_id, db)
    reward_points.points += points
    reward_points.total_earned += points

    db.commit()


def redeem_points(user_id: int, redemption_type: RedemptionType, points_used: float, value: float, order_id: int = None, db: Session = None):
    """Redeem points for discount/benefit"""
    if db is None:
        from app.database.session import get_db
        db = next(get_db())

    # Check if user has enough points
    reward_points = get_or_create_reward_points(user_id, db)
    if reward_points.points < points_used:
        raise ValueError("Insufficient points")

    # Validate redemption rules
    rule = db.query(RedemptionRule).filter(
        and_(RedemptionRule.redemption_type == redemption_type, RedemptionRule.is_active == 1)
    ).first()

    if not rule:
        raise ValueError("Redemption type not available")

    if points_used < rule.min_points:
        raise ValueError(f"Minimum {rule.min_points} points required")

    # For percentage discounts, validate max percentage
    if redemption_type == RedemptionType.DISCOUNT_PERCENTAGE and rule.max_discount_percentage:
        if value > rule.max_discount_percentage:
            raise ValueError(f"Maximum discount percentage is {rule.max_discount_percentage}%")

    # For fixed discounts, validate max amount
    if redemption_type == RedemptionType.DISCOUNT_FIXED and rule.max_discount_amount:
        if value > rule.max_discount_amount:
            raise ValueError(f"Maximum discount amount is ₹{rule.max_discount_amount}")

    # Create redemption record
    redemption = RewardRedemption(
        user_id=user_id,
        redemption_type=redemption_type,
        points_used=points_used,
        value=value,
        description=f"Redeemed {points_used} points for {redemption_type.value}",
        order_id=order_id
    )
    db.add(redemption)

    # Update points balance
    reward_points.points -= points_used
    reward_points.total_redeemed += points_used

    db.commit()
    db.refresh(redemption)
    return redemption


def get_user_points(user_id: int, db: Session):
    """Get user's points and recent transactions"""
    reward_points = get_or_create_reward_points(user_id, db)

    # Get recent transactions (last 10)
    transactions = db.query(RewardTransaction).filter(
        RewardTransaction.user_id == user_id
    ).order_by(RewardTransaction.created_at.desc()).limit(10).all()

    # Get recent redemptions (last 10)
    redemptions = db.query(RewardRedemption).filter(
        RewardRedemption.user_id == user_id
    ).order_by(RewardRedemption.created_at.desc()).limit(10).all()

    return {
        "current_points": reward_points.points,
        "total_earned": reward_points.total_earned,
        "total_redeemed": reward_points.total_redeemed,
        "recent_transactions": [
            {
                "id": t.id,
                "reward_type": t.reward_type.value,
                "points": t.points,
                "description": t.description,
                "created_at": t.created_at.isoformat()
            } for t in transactions
        ],
        "recent_redemptions": [
            {
                "id": r.id,
                "redemption_type": r.redemption_type.value,
                "points_used": r.points_used,
                "value": r.value,
                "description": r.description,
                "created_at": r.created_at.isoformat()
            } for r in redemptions
        ]
    }


def get_available_redemptions(user_points: float, db: Session):
    """Get available redemption options for user's points"""
    rules = db.query(RedemptionRule).filter(RedemptionRule.is_active == 1).all()

    available = []
    for rule in rules:
        if user_points >= rule.min_points:
            available.append({
                "id": rule.id,
                "redemption_type": rule.redemption_type.value,
                "min_points": rule.min_points,
                "max_discount_percentage": rule.max_discount_percentage,
                "max_discount_amount": rule.max_discount_amount
            })

    return available


def process_order_completion_rewards(order_id: int, db: Session):
    """Process rewards for completed order"""
    order = db.query(Order).filter(Order.id == order_id).first()
    # Accept canonical READY / PICKED and legacy COMPLETED as "done"
    _done_statuses = {OrderStatus.READY, OrderStatus.PICKED, OrderStatus.COMPLETED}
    if not order or order.status not in _done_statuses:
        return

    # Get reward rules
    rule = db.query(RewardRule).filter(
        and_(RewardRule.reward_type == RewardType.ORDER_COMPLETION, RewardRule.is_active == 1)
    ).first()

    if not rule:
        return

    # Calculate points (amount in rupees / 100 since amount is in paise)
    order_amount_rupees = order.total_amount / 100
    points_earned = order_amount_rupees * rule.points_per_rupee

    award_points(
        order.user_id,
        RewardType.ORDER_COMPLETION,
        points_earned,
        f"Earned {points_earned} points for order completion",
        order_id,
        db
    )

    policy = get_offpeak_policy(db)
    order_hour = order.created_at.hour if order.created_at else None
    if policy["enabled"] and order_hour is not None and policy["start_hour"] <= order_hour < policy["end_hour"]:
        bonus_points = float(policy["bonus_points_per_order"])
        if bonus_points > 0:
            award_points(
                order.user_id,
                RewardType.OFF_PEAK_BONUS,
                bonus_points,
                f"Off-peak bonus for order #{order.id}",
                order.id,
                db,
            )


def create_voucher(
    code: str,
    description: str,
    discount_type: VoucherDiscountType,
    discount_value: float,
    min_order_amount_paise: int,
    max_discount_amount_paise: int | None,
    usage_limit: int | None,
    expires_at: datetime,
    created_by_user_id: int,
    db: Session,
) -> Voucher:
    normalized_code = code.strip().upper()
    if not normalized_code:
        raise ValueError("Voucher code is required")
    if discount_value <= 0:
        raise ValueError("Discount value must be greater than 0")
    if usage_limit is not None and usage_limit < 1:
        raise ValueError("Usage limit must be at least 1")
    if expires_at <= utcnow_naive():
        raise ValueError("Voucher expiry must be in the future")

    existing = db.query(Voucher).filter(Voucher.code == normalized_code).first()
    if existing:
        raise ValueError("Voucher code already exists")

    voucher = Voucher(
        code=normalized_code,
        description=description,
        discount_type=discount_type,
        discount_value=discount_value,
        min_order_amount_paise=min_order_amount_paise,
        max_discount_amount_paise=max_discount_amount_paise,
        usage_limit=usage_limit,
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
        is_active=1,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


def list_vouchers(db: Session, include_inactive: bool = False) -> list[Voucher]:
    query = db.query(Voucher)
    if not include_inactive:
        query = query.filter(Voucher.is_active == 1, Voucher.expires_at > utcnow_naive())
    return query.order_by(Voucher.created_at.desc()).all()


def update_voucher(
    voucher_id: int,
    db: Session,
    description: str | None = None,
    discount_value: float | None = None,
    min_order_amount_paise: int | None = None,
    max_discount_amount_paise: int | None = None,
    usage_limit: int | None = None,
    expires_at: datetime | None = None,
    is_active: bool | None = None,
) -> Voucher:
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise ValueError("Voucher not found")

    if description is not None:
        voucher.description = description
    if discount_value is not None:
        if discount_value <= 0:
            raise ValueError("Discount value must be greater than 0")
        voucher.discount_value = discount_value
    if min_order_amount_paise is not None:
        voucher.min_order_amount_paise = min_order_amount_paise
    if max_discount_amount_paise is not None:
        voucher.max_discount_amount_paise = max_discount_amount_paise
    if usage_limit is not None:
        if usage_limit < 1:
            raise ValueError("Usage limit must be at least 1")
        voucher.usage_limit = usage_limit
    if expires_at is not None:
        if expires_at <= utcnow_naive():
            raise ValueError("Voucher expiry must be in the future")
        voucher.expires_at = expires_at
    if is_active is not None:
        voucher.is_active = 1 if is_active else 0

    db.commit()
    db.refresh(voucher)
    return voucher


def deactivate_voucher(voucher_id: int, db: Session) -> Voucher:
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise ValueError("Voucher not found")
    voucher.is_active = 0
    db.commit()
    db.refresh(voucher)
    return voucher


def redeem_voucher(code: str, user_id: int, order_id: int, db: Session) -> dict:
    voucher = db.query(Voucher).filter(Voucher.code == code.strip().upper()).first()
    if not voucher:
        raise ValueError("Voucher not found")
    if voucher.is_active != 1:
        raise ValueError("Voucher is inactive")
    if voucher.expires_at <= utcnow_naive():
        raise ValueError("Voucher has expired")
    if voucher.usage_limit is not None and voucher.times_redeemed >= voucher.usage_limit:
        raise ValueError("Voucher usage limit reached")

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise ValueError("Order not found")

    existing_redemption = db.query(VoucherRedemption).filter(
        VoucherRedemption.voucher_id == voucher.id,
        VoucherRedemption.order_id == order.id,
        VoucherRedemption.user_id == user_id,
    ).first()
    if existing_redemption:
        raise ValueError("Voucher already redeemed for this order")

    if int(order.total_amount or 0) < int(voucher.min_order_amount_paise or 0):
        raise ValueError("Order does not meet minimum amount for voucher")

    if voucher.discount_type == VoucherDiscountType.FIXED:
        discount_amount = int(voucher.discount_value)
    else:
        discount_amount = int((order.total_amount * voucher.discount_value) / 100)
        if voucher.max_discount_amount_paise is not None:
            discount_amount = min(discount_amount, int(voucher.max_discount_amount_paise))

    discount_amount = min(discount_amount, int(order.total_amount or 0))
    if discount_amount <= 0:
        raise ValueError("Voucher discount resolves to zero")

    order.total_amount = int(order.total_amount or 0) - discount_amount

    redemption = VoucherRedemption(
        voucher_id=voucher.id,
        user_id=user_id,
        order_id=order.id,
        discount_amount_paise=discount_amount,
    )
    db.add(redemption)

    reward_redemption = RewardRedemption(
        user_id=user_id,
        redemption_type=RedemptionType.DISCOUNT_FIXED,
        points_used=0,
        value=discount_amount / 100,
        description=f"Voucher {voucher.code} redeemed",
        order_id=order.id,
    )
    db.add(reward_redemption)

    reward_transaction = RewardTransaction(
        user_id=user_id,
        reward_type=RewardType.VOUCHER_REDEMPTION,
        points=0,
        description=f"Voucher {voucher.code} redeemed for ₹{discount_amount / 100:.2f}",
        order_id=order.id,
    )
    db.add(reward_transaction)

    add_ledger_entry(
        order_id=order.id,
        amount=discount_amount,
        entry_type=LedgerType.DEBIT,
        source=LedgerSource.VOUCHER,
        db=db,
        description=f"Voucher discount applied ({voucher.code})",
    )

    voucher.times_redeemed += 1
    db.commit()
    db.refresh(voucher)
    return {
        "voucher_id": voucher.id,
        "code": voucher.code,
        "discount_amount_paise": discount_amount,
        "updated_order_total_paise": order.total_amount,
    }


def redeem_points_for_order(user_id: int, order_id: int, points_to_redeem: float, db: Session) -> dict:
    """Redeem points at checkout and apply discount directly to the order.
    
    10 points = 1 INR (100 paise) discount.
    """
    from app.modules.rewards.model import RewardPoints, RewardRedemption, RedemptionType, RewardTransaction, RewardType
    from app.modules.orders.model import Order

    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise ValueError("Order not found")

    # Check balance
    reward_points = db.query(RewardPoints).filter(RewardPoints.user_id == user_id).first()
    if not reward_points or reward_points.points < points_to_redeem:
        raise ValueError("Insufficient points")

    # Calculate discount value: 1 point = 10 paise, so points_to_redeem * 10 paise = points_to_redeem * 10 in paise
    discount_amount_paise = int(points_to_redeem * 10)
    discount_amount_paise = min(discount_amount_paise, int(order.total_amount or 0))

    if discount_amount_paise <= 0:
        raise ValueError("Points discount resolves to zero")

    # Deduct discount
    order.total_amount = int(order.total_amount or 0) - discount_amount_paise

    # Create redemption record
    redemption = RewardRedemption(
        user_id=user_id,
        redemption_type=RedemptionType.DISCOUNT_FIXED,
        points_used=points_to_redeem,
        value=discount_amount_paise / 100.0,
        description=f"Redeemed {points_to_redeem} points for discount of ₹{discount_amount_paise / 100.0:.2f}",
        order_id=order_id
    )
    db.add(redemption)

    # Also log a reward transaction so there is audit trail
    transaction = RewardTransaction(
        user_id=user_id,
        reward_type=RewardType.VOUCHER_REDEMPTION,
        points=-points_to_redeem,
        description=f"Redeemed {points_to_redeem} points at checkout for ₹{discount_amount_paise / 100.0:.2f} discount",
        order_id=order_id
    )
    db.add(transaction)

    # Update points balance
    reward_points.points -= points_to_redeem
    reward_points.total_redeemed += points_to_redeem

    # Add ledger entry
    from app.modules.ledger.service import add_ledger_entry
    from app.modules.ledger.model import LedgerType, LedgerSource
    add_ledger_entry(
        order_id=order.id,
        amount=discount_amount_paise,
        entry_type=LedgerType.DEBIT,
        source=LedgerSource.VOUCHER,  # Safe fallback matching model enum definition
        db=db,
        description=f"Rewards discount applied ({points_to_redeem} points)",
    )

    db.commit()
    return {
        "points_used": points_to_redeem,
        "discount_amount_paise": discount_amount_paise,
        "updated_order_total_paise": order.total_amount
    }


def get_offpeak_policy(db: Session) -> dict:
    policy = db.query(OffPeakRewardPolicy).order_by(OffPeakRewardPolicy.id.desc()).first()
    if not policy:
        return {
            "enabled": False,
            "start_hour": 15,
            "end_hour": 17,
            "bonus_points_per_order": 10.0,
        }
    return {
        "enabled": bool(policy.enabled),
        "start_hour": policy.start_hour,
        "end_hour": policy.end_hour,
        "bonus_points_per_order": float(policy.bonus_points_per_order),
    }


def set_offpeak_policy(
    db: Session,
    enabled: bool,
    start_hour: int,
    end_hour: int,
    bonus_points_per_order: float,
    actor_user_id: int,
) -> dict:
    if start_hour < 0 or start_hour > 23 or end_hour < 1 or end_hour > 24:
        raise ValueError("Hours must be within 0-24")
    if end_hour <= start_hour:
        raise ValueError("end_hour must be greater than start_hour")
    if bonus_points_per_order < 0:
        raise ValueError("bonus_points_per_order must be non-negative")

    policy = db.query(OffPeakRewardPolicy).order_by(OffPeakRewardPolicy.id.desc()).first()
    if not policy:
        policy = OffPeakRewardPolicy(
            enabled=1 if enabled else 0,
            start_hour=start_hour,
            end_hour=end_hour,
            bonus_points_per_order=bonus_points_per_order,
            updated_by_user_id=actor_user_id,
        )
        db.add(policy)
    else:
        policy.enabled = 1 if enabled else 0
        policy.start_hour = start_hour
        policy.end_hour = end_hour
        policy.bonus_points_per_order = bonus_points_per_order
        policy.updated_by_user_id = actor_user_id

    db.add(
        OffPeakRewardPolicyAudit(
            enabled=1 if enabled else 0,
            start_hour=start_hour,
            end_hour=end_hour,
            bonus_points_per_order=bonus_points_per_order,
            updated_by_user_id=actor_user_id,
        )
    )

    db.commit()
    return get_offpeak_policy(db)


def list_offpeak_policy_audit(db: Session, limit: int = 20) -> list[OffPeakRewardPolicyAudit]:
    return db.query(OffPeakRewardPolicyAudit).order_by(OffPeakRewardPolicyAudit.changed_at.desc()).limit(limit).all()


def initialize_default_rules(db: Session, actor_user_id: int | None = None):
    """Initialize default reward and redemption rules"""

    # Reward rules
    reward_rules = [
        RewardRule(reward_type=RewardType.ORDER_COMPLETION, points_per_rupee=5.0),  # 5 points per rupee
        RewardRule(reward_type=RewardType.FIRST_ORDER, fixed_points=50.0),
        RewardRule(reward_type=RewardType.REFERRAL, fixed_points=25.0),
        RewardRule(reward_type=RewardType.LOYALTY_MILESTONE, fixed_points=100.0),
    ]

    for rule in reward_rules:
        existing = db.query(RewardRule).filter(RewardRule.reward_type == rule.reward_type).first()
        if not existing:
            db.add(rule)

    # Redemption rules
    redemption_rules = [
        RedemptionRule(
            redemption_type=RedemptionType.DISCOUNT_PERCENTAGE,
            min_points=50.0,
            max_discount_percentage=20.0
        ),
        RedemptionRule(
            redemption_type=RedemptionType.DISCOUNT_FIXED,
            min_points=100.0,  # Voucher for 100 points
            max_discount_amount=50.0
        ),
        RedemptionRule(
            redemption_type=RedemptionType.FREE_ITEM,
            min_points=200.0
        ),
    ]

    for rule in redemption_rules:
        existing = db.query(RedemptionRule).filter(RedemptionRule.redemption_type == rule.redemption_type).first()
        if not existing:
            db.add(rule)

    db.commit()

    if actor_user_id is not None:
        policy = db.query(OffPeakRewardPolicy).order_by(OffPeakRewardPolicy.id.desc()).first()
        if not policy:
            set_offpeak_policy(
                db=db,
                enabled=False,
                start_hour=15,
                end_hour=17,
                bonus_points_per_order=10.0,
                actor_user_id=actor_user_id,
            )
