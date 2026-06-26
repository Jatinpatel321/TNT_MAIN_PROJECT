from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.complaints.model import Complaint, ComplaintCategory, ComplaintStatus
from app.modules.orders.model import Order
from app.modules.users.model import User

router = APIRouter(prefix="/complaints", tags=["Complaints"])


class ComplaintCreateRequest(BaseModel):
    category: ComplaintCategory
    title: str = Field(min_length=3, max_length=150)
    description: str | None = None
    order_id: int | None = None


class ComplaintStatusUpdateRequest(BaseModel):
    status: ComplaintStatus


@router.post("/")
def create_complaint(
    body: ComplaintCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor_id = None
    if body.order_id is not None:
        order = db.query(Order).filter(Order.id == body.order_id, Order.user_id == db_user.id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        vendor_id = order.vendor_id

    complaint = Complaint(
        user_id=db_user.id,
        vendor_id=vendor_id,
        order_id=body.order_id,
        category=body.category,
        title=body.title,
        description=body.description,
        status=ComplaintStatus.OPEN,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {"message": "Complaint filed", "complaint_id": complaint.id}


@router.get("/my")
def my_complaints(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    rows = (
        db.query(Complaint)
        .filter(Complaint.user_id == db_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "order_id": row.order_id,
            "vendor_id": row.vendor_id,
            "assigned_to_vendor_id": row.assigned_to_vendor_id,
            "category": row.category.value,
            "status": row.status.value,
            "title": row.title,
            "description": row.description,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.get("/")
def list_complaints(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    role = (db_user.role.value or "").lower()
    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Access denied")

    q = db.query(Complaint)
    total = q.count()
    rows = q.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "order_id": row.order_id,
                "vendor_id": row.vendor_id,
                "assigned_to_vendor_id": row.assigned_to_vendor_id,
                "category": row.category.value,
                "status": row.status.value,
                "title": row.title,
                "description": row.description,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/{complaint_id}/assign")
def assign_complaint(
    complaint_id: int,
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    role = (db_user.role.value or "").lower()
    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Access denied")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor or (vendor.role.value or "").lower() != "vendor":
        raise HTTPException(status_code=404, detail="Vendor not found")

    complaint.assigned_to_vendor_id = vendor.id
    complaint.status = ComplaintStatus.ASSIGNED
    db.commit()

    return {"message": "Complaint assigned", "complaint_id": complaint.id, "assigned_to_vendor_id": vendor.id}


@router.post("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    body: ComplaintStatusUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    role = (db_user.role.value or "").lower()
    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Access denied")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = body.status
    db.commit()

    return {"message": "Complaint status updated", "complaint_id": complaint.id, "status": complaint.status.value}


@router.post("/{complaint_id}/escalate")
def escalate_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    role = (db_user.role.value or "").lower()
    if role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Access denied")

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.status in {ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED}:
        raise HTTPException(status_code=400, detail="Cannot escalate a closed complaint")

    complaint.status = ComplaintStatus.ESCALATED
    db.commit()

    return {"message": "Complaint escalated", "complaint_id": complaint.id, "status": complaint.status.value}
