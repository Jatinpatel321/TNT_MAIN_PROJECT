from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.feedback.model import Feedback, VendorReview
from app.modules.feedback.schemas import (
    FeedbackCreateRequest,
    FeedbackResponse,
    VendorFeedbackSummaryResponse,
    VendorReviewCreateRequest,
    VendorReviewResponse,
)
from app.modules.orders.model import Order, OrderStatus
from app.modules.users.model import User

router = APIRouter(prefix="/feedback", tags=["Feedback"])

FEEDBACK_ALLOWED_STATUSES = {OrderStatus.PICKED, OrderStatus.COMPLETED}


@router.post("/orders/{order_id}", response_model=FeedbackResponse)
def submit_feedback(
    order_id: int,
    body: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.user_id != db_user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in FEEDBACK_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Feedback allowed only for picked or completed orders",
        )

    existing = (
        db.query(Feedback)
        .filter(Feedback.order_id == order_id, Feedback.user_id == db_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this order")

    overall = body.overall_rating or round(
        (body.quality_rating + body.time_rating + body.behavior_rating) / 3
    )

    feedback = Feedback(
        order_id=order_id,
        user_id=db_user.id,
        vendor_id=order.vendor_id,
        overall_rating=overall,
        quality_rating=body.quality_rating,
        time_rating=body.time_rating,
        behavior_rating=body.behavior_rating,
        comment=body.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return _feedback_to_response(feedback)


@router.get("/me", response_model=list[FeedbackResponse])
def my_feedback(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    records = (
        db.query(Feedback)
        .filter(Feedback.user_id == db_user.id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return [_feedback_to_response(r) for r in records]


@router.get("/orders/{order_id}", response_model=FeedbackResponse)
def get_order_feedback(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    feedback = (
        db.query(Feedback)
        .filter(Feedback.order_id == order_id, Feedback.user_id == db_user.id)
        .first()
    )
    if not feedback:
        raise HTTPException(status_code=404, detail="No feedback found for this order")
    return _feedback_to_response(feedback)


@router.post("/vendors/{vendor_id}/reviews", response_model=VendorReviewResponse)
def submit_vendor_review(
    vendor_id: int,
    body: VendorReviewCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor = db.query(User).filter(User.id == vendor_id, User.role == "VENDOR").first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    review = VendorReview(
        vendor_id=vendor_id,
        user_id=db_user.id,
        order_id=body.order_id,
        rating=body.rating,
        title=body.title,
        review_text=body.review_text,
        is_anonymous=body.is_anonymous,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_to_response(review, db_user)


@router.get("/vendors/{vendor_id}/reviews", response_model=list[VendorReviewResponse])
def list_vendor_reviews(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    reviews = (
        db.query(VendorReview)
        .filter(VendorReview.vendor_id == vendor_id)
        .order_by(VendorReview.created_at.desc())
        .all()
    )

    user_map = _user_name_map(db, [r.user_id for r in reviews])
    result = []
    for r in reviews:
        name = None if r.is_anonymous else user_map.get(r.user_id)
        result.append(_review_to_response(r, None, name))
    return result


@router.get("/vendors/{vendor_id}/summary", response_model=VendorFeedbackSummaryResponse)
def vendor_feedback_summary(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    summary = (
        db.query(
            func.count(Feedback.id).label("total_reviews"),
            func.avg(Feedback.quality_rating).label("avg_quality"),
            func.avg(Feedback.time_rating).label("avg_time"),
            func.avg(Feedback.behavior_rating).label("avg_behavior"),
            func.avg(Feedback.overall_rating).label("avg_overall"),
        )
        .filter(Feedback.vendor_id == vendor_id)
        .first()
    )

    total = int(summary.total_reviews or 0)
    dist_rows = (
        db.query(Feedback.overall_rating, func.count(Feedback.id))
        .filter(Feedback.vendor_id == vendor_id, Feedback.overall_rating.isnot(None))
        .group_by(Feedback.overall_rating)
        .all()
    )
    rating_distribution = {r[0]: r[1] for r in dist_rows}

    return VendorFeedbackSummaryResponse(
        vendor_id=vendor_id,
        total_reviews=total,
        avg_quality_rating=round(float(summary.avg_quality or 0), 2),
        avg_time_rating=round(float(summary.avg_time or 0), 2),
        avg_behavior_rating=round(float(summary.avg_behavior or 0), 2),
        avg_overall_rating=round(float(summary.avg_overall or 0), 2),
        rating_distribution=rating_distribution,
    )


def _feedback_to_response(f: Feedback) -> FeedbackResponse:
    return FeedbackResponse(
        id=f.id,
        order_id=f.order_id,
        user_id=f.user_id,
        vendor_id=f.vendor_id,
        overall_rating=f.overall_rating,
        quality_rating=f.quality_rating,
        time_rating=f.time_rating,
        behavior_rating=f.behavior_rating,
        comment=f.comment,
        created_at=f.created_at.isoformat() if f.created_at else "",
    )


def _review_to_response(
    r: VendorReview,
    db_user: User | None = None,
    name_override: str | None = None,
) -> VendorReviewResponse:
    reviewer_name: str | None = None
    if not r.is_anonymous:
        if name_override is not None:
            reviewer_name = name_override
        elif db_user is not None:
            reviewer_name = db_user.name

    return VendorReviewResponse(
        id=r.id,
        vendor_id=r.vendor_id,
        user_id=r.user_id,
        order_id=r.order_id,
        rating=r.rating,
        title=r.title,
        review_text=r.review_text,
        is_anonymous=r.is_anonymous,
        reviewer_name=reviewer_name,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


def _user_name_map(db: Session, user_ids: list[int]) -> dict[int, str | None]:
    if not user_ids:
        return {}
    users = db.query(User).filter(User.id.in_(set(user_ids))).all()
    return {u.id: u.name for u in users}
