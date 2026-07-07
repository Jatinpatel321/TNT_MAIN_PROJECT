from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user, require_role
from app.modules.rewards.model import RedemptionType, VoucherDiscountType
from app.modules.users.model import User
from app.modules.rewards.service import (
    create_voucher,
    deactivate_voucher,
    get_available_redemptions,
    get_offpeak_policy,
    get_user_points,
    initialize_default_rules,
    list_offpeak_policy_audit,
    list_vouchers,
    redeem_points,
    redeem_voucher,
    set_offpeak_policy,
    update_voucher,
)

router = APIRouter(prefix="/rewards", tags=["Rewards"])


class RedeemPointsRequest(BaseModel):
    redemption_type: RedemptionType
    points_used: float
    value: float
    order_id: Optional[int] = None


class RewardTransactionResponse(BaseModel):
    id: int
    reward_type: str
    points: float
    description: str
    created_at: str


class RewardRedemptionResponse(BaseModel):
    id: int
    redemption_type: str
    points_used: float
    value: float
    description: str
    created_at: str


class UserPointsResponse(BaseModel):
    current_points: float
    total_earned: float
    total_redeemed: float
    recent_transactions: List[RewardTransactionResponse]
    recent_redemptions: List[RewardRedemptionResponse]


class RedemptionRuleResponse(BaseModel):
    id: int
    redemption_type: str
    min_points: float
    max_discount_percentage: Optional[float]
    max_discount_amount: Optional[float]


class VoucherCreateRequest(BaseModel):
    code: str
    description: str
    discount_type: VoucherDiscountType
    discount_value: float
    min_order_amount_paise: int = 0
    max_discount_amount_paise: Optional[int] = None
    usage_limit: Optional[int] = None
    expires_at: str


class VoucherUpdateRequest(BaseModel):
    description: Optional[str] = None
    discount_value: Optional[float] = None
    min_order_amount_paise: Optional[int] = None
    max_discount_amount_paise: Optional[int] = None
    usage_limit: Optional[int] = None
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None


class VoucherRedeemRequest(BaseModel):
    order_id: int


class RewardTransactionHistoryResponse(BaseModel):
    id: int
    reward_type: str
    points: float
    description: str
    order_id: Optional[int] = None
    created_at: str


class RewardRedemptionHistoryResponse(BaseModel):
    id: int
    redemption_type: str
    points_used: float
    value: float
    description: str
    order_id: Optional[int] = None
    created_at: str


class OffPeakPolicyRequest(BaseModel):
    enabled: bool
    start_hour: int
    end_hour: int
    bonus_points_per_order: float


@router.get("/points", response_model=UserPointsResponse)
def get_points(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get user's current points and history"""
    return get_user_points(user["id"], db)


@router.get("/redemptions", response_model=List[RedemptionRuleResponse])
def get_redemptions(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Get available redemption options"""
    user_points = get_user_points(user["id"], db)["current_points"]
    return get_available_redemptions(user_points, db)


@router.post("/redeem")
def redeem_user_points(
    request: RedeemPointsRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Redeem points for discount or benefit"""
    try:
        redemption = redeem_points(
            user["id"],
            request.redemption_type,
            request.points_used,
            request.value,
            request.order_id,
            db
        )
        return {
            "message": "Points redeemed successfully",
            "redemption_id": redemption.id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/initialize-rules")
def init_rules(db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    """Initialize default reward rules (admin only)"""
    initialize_default_rules(db, actor_user_id=user["id"])
    return {"message": "Reward rules initialized"}


@router.post("/vouchers")
def create_voucher_endpoint(
    request: VoucherCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from datetime import datetime

    try:
        voucher = create_voucher(
            code=request.code,
            description=request.description,
            discount_type=request.discount_type,
            discount_value=request.discount_value,
            min_order_amount_paise=request.min_order_amount_paise,
            max_discount_amount_paise=request.max_discount_amount_paise,
            usage_limit=request.usage_limit,
            expires_at=datetime.fromisoformat(request.expires_at),
            created_by_user_id=user["id"],
            db=db,
        )
        return {"voucher_id": voucher.id, "code": voucher.code}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/vouchers")
def list_vouchers_endpoint(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    can_view_all = user["role"] == "admin"
    vouchers = list_vouchers(db, include_inactive=include_inactive and can_view_all)
    return [
        {
            "id": voucher.id,
            "code": voucher.code,
            "description": voucher.description,
            "discount_type": voucher.discount_type.value,
            "discount_value": voucher.discount_value,
            "min_order_amount_paise": voucher.min_order_amount_paise,
            "max_discount_amount_paise": voucher.max_discount_amount_paise,
            "usage_limit": voucher.usage_limit,
            "times_redeemed": voucher.times_redeemed,
            "expires_at": voucher.expires_at.isoformat(),
            "is_active": bool(voucher.is_active),
        }
        for voucher in vouchers
    ]


@router.put("/vouchers/{voucher_id}")
def update_voucher_endpoint(
    voucher_id: int,
    request: VoucherUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from datetime import datetime

    try:
        voucher = update_voucher(
            voucher_id=voucher_id,
            db=db,
            description=request.description,
            discount_value=request.discount_value,
            min_order_amount_paise=request.min_order_amount_paise,
            max_discount_amount_paise=request.max_discount_amount_paise,
            usage_limit=request.usage_limit,
            expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None,
            is_active=request.is_active,
        )
        return {"voucher_id": voucher.id, "is_active": bool(voucher.is_active)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/vouchers/{voucher_id}")
def delete_voucher_endpoint(
    voucher_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    try:
        voucher = deactivate_voucher(voucher_id, db)
        return {"voucher_id": voucher.id, "is_active": bool(voucher.is_active)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/vouchers/{code}/redeem")
def redeem_voucher_endpoint(
    code: str,
    request: VoucherRedeemRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return redeem_voucher(code=code, user_id=user["id"], order_id=request.order_id, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/transactions", response_model=List[RewardTransactionHistoryResponse])
def get_transaction_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get full transaction history for the authenticated user"""
    from app.modules.rewards.model import RewardTransaction
    transactions = (
        db.query(RewardTransaction)
        .filter(RewardTransaction.user_id == user["id"])
        .order_by(RewardTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": t.id,
            "reward_type": t.reward_type.value,
            "points": t.points,
            "description": t.description,
            "order_id": t.order_id,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        }
        for t in transactions
    ]


@router.get("/redemptions/history", response_model=List[RewardRedemptionHistoryResponse])
def get_redemption_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get full redemption history for the authenticated user"""
    from app.modules.rewards.model import RewardRedemption
    redemptions = (
        db.query(RewardRedemption)
        .filter(RewardRedemption.user_id == user["id"])
        .order_by(RewardRedemption.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "redemption_type": r.redemption_type.value,
            "points_used": r.points_used,
            "value": r.value,
            "description": r.description,
            "order_id": r.order_id,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in redemptions
    ]


@router.get("/offpeak-policy")
def get_offpeak_policy_endpoint(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return get_offpeak_policy(db)


@router.post("/offpeak-policy")
def set_offpeak_policy_endpoint(
    request: OffPeakPolicyRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    try:
        return set_offpeak_policy(
            db=db,
            enabled=request.enabled,
            start_hour=request.start_hour,
            end_hour=request.end_hour,
            bonus_points_per_order=request.bonus_points_per_order,
            actor_user_id=user["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/offpeak-policy/audit")
def list_offpeak_policy_audit_endpoint(
    limit: int = 20,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    audit_rows = list_offpeak_policy_audit(db, limit=limit)
    return [
        {
            "enabled": bool(row.enabled),
            "start_hour": row.start_hour,
            "end_hour": row.end_hour,
            "bonus_points_per_order": row.bonus_points_per_order,
            "updated_by_user_id": row.updated_by_user_id,
            "changed_at": row.changed_at.isoformat(),
        }
        for row in audit_rows
    ]


@router.get("/{user_id}", response_model=UserPointsResponse)
def get_user_rewards(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Get rewards for a specific user

    Students can only query their own rewards.
    Vendors, admins, and superadmins can query any user's rewards.
    """
    from app.modules.users.model import User

    db_caller = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_caller:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    allowed_roles = {"vendor", "admin", "superadmin"}
    caller_role = db_caller.role.value if hasattr(db_caller.role, "value") else str(db_caller.role)
    if db_caller.id != user_id and caller_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Cannot view another user's rewards")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    return get_user_points(user_id, db)
