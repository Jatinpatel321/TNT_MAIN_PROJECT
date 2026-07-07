"""Vendor-facing Reviews Router.

Lets a vendor read the reviews customers left for them, see aggregate stats,
and reply to individual reviews. Reviews are stored in the ``vendor_reviews``
table (see ``app.modules.feedback.model.VendorReview``) and are created by
customers via ``POST /feedback/vendors/{vendor_id}/reviews``.

Authentication uses ``get_current_user`` which transparently accepts a vendor
access token and returns ``id`` == the vendor owner's ``users.id`` — the same id
that ``VendorReview.vendor_id`` references.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.core.time_utils import utcnow_naive
from app.modules.feedback.model import VendorReview
from app.modules.users.model import User

router = APIRouter(prefix="/vendors", tags=["Vendor Reviews"])


def _review_stats(db: Session, vendor_user_id: int) -> dict[str, Any]:
    rows = (
        db.query(VendorReview.rating, func.count(VendorReview.id))
        .filter(VendorReview.vendor_id == vendor_user_id)
        .group_by(VendorReview.rating)
        .all()
    )
    distribution = {str(i): 0 for i in range(1, 6)}
    total = 0
    weighted = 0
    for rating, count in rows:
        if rating is None:
            continue
        distribution[str(int(rating))] = int(count)
        total += int(count)
        weighted += int(rating) * int(count)
    average = round(weighted / total, 2) if total else 0.0
    return {
        "average_rating": average,
        "total_reviews": total,
        "distribution": distribution,
    }


def _serialize(review: VendorReview, user_name: str | None) -> dict[str, Any]:
    return {
        "id": review.id,
        "user_id": review.user_id,
        "user_name": None if review.is_anonymous else user_name,
        "order_id": review.order_id,
        "rating": review.rating,
        "title": review.title,
        "comment": review.review_text,
        "vendor_reply": review.vendor_reply,
        "vendor_reply_at": review.vendor_reply_at.isoformat() if review.vendor_reply_at else None,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


@router.get("/reviews", summary="List reviews for the authenticated vendor")
def list_reviews(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    rating: int | None = Query(None, ge=1, le=5),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_user_id = user["id"]

    base = db.query(VendorReview).filter(VendorReview.vendor_id == vendor_user_id)
    if rating is not None:
        base = base.filter(VendorReview.rating == rating)

    total = base.count()
    reviews = (
        base.order_by(VendorReview.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    name_map: dict[int, str | None] = {}
    user_ids = {r.user_id for r in reviews if not r.is_anonymous}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            name_map[u.id] = u.full_name or u.name

    return {
        "reviews": [_serialize(r, name_map.get(r.user_id)) for r in reviews],
        "total": total,
        "page": page,
        "per_page": per_page,
        "stats": _review_stats(db, vendor_user_id),
    }


@router.get("/reviews/stats", summary="Aggregate review stats for the vendor")
def review_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    return _review_stats(db, user["id"])


@router.post("/reviews/{review_id}/reply", summary="Reply to a review")
def reply_to_review(
    review_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    reply = (body or {}).get("reply")
    if not reply or not isinstance(reply, str) or not reply.strip():
        raise HTTPException(status_code=400, detail="'reply' text is required")

    review = (
        db.query(VendorReview)
        .filter(VendorReview.id == review_id, VendorReview.vendor_id == user["id"])
        .first()
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.vendor_reply = reply.strip()
    review.vendor_reply_at = utcnow_naive()
    db.commit()
    db.refresh(review)

    name = None
    if not review.is_anonymous:
        u = db.query(User).filter(User.id == review.user_id).first()
        name = (u.full_name or u.name) if u else None

    return _serialize(review, name)
