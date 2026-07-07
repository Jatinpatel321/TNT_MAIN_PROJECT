"""Streaming CSV export service for admin reports."""
import csv
import io
from datetime import datetime
from typing import Generator, List

from fastapi.responses import StreamingResponse
from sqlalchemy import Date, func
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole


def _stream_csv(headers: List[str], rows: Generator) -> StreamingResponse:
    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(headers)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for row in rows:
            writer.writerow(row)
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    now = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"tnt_export_{now}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def export_orders_csv(
    db: Session,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
) -> StreamingResponse:
    from app.modules.orders.model import Order

    query = db.query(Order)
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))
    if status:
        query = query.filter(Order.status == status)
    query = query.order_by(Order.created_at.desc())

    headers = [
        "order_id", "user_id", "vendor_id", "status",
        "total_amount", "payment_method", "created_at", "updated_at",
    ]

    def rows():
        for order in query.yield_per(200):
            yield [
                order.id,
                order.user_id,
                order.vendor_id,
                order.status.value if hasattr(order.status, "value") else order.status,
                order.total_amount,
                getattr(order, "payment_method", ""),
                order.created_at.isoformat() if order.created_at else "",
                order.updated_at.isoformat() if order.updated_at else "",
            ]

    return _stream_csv(headers, rows())


def export_users_csv(
    db: Session,
    role: str | None = None,
    is_active: bool | None = None,
) -> StreamingResponse:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    headers = ["user_id", "name", "full_name", "phone", "role", "is_active", "created_at"]

    def rows():
        for user in query.yield_per(200):
            yield [
                user.id,
                user.name or "",
                user.full_name or "",
                user.phone,
                user.role.value if hasattr(user.role, "value") else user.role,
                user.is_active,
                user.created_at.isoformat() if user.created_at else "",
            ]

    return _stream_csv(headers, rows())


def export_vendors_csv(db: Session) -> StreamingResponse:
    query = db.query(User).filter(User.role == UserRole.VENDOR)
    headers = ["vendor_id", "name", "full_name", "phone", "is_active", "created_at"]

    def rows():
        for vendor in query.yield_per(200):
            yield [
                vendor.id,
                vendor.name or "",
                vendor.full_name or "",
                vendor.phone,
                vendor.is_active,
                vendor.created_at.isoformat() if vendor.created_at else "",
            ]

    return _stream_csv(headers, rows())


def export_complaints_csv(
    db: Session,
    status: str | None = None,
) -> StreamingResponse:
    from app.modules.complaints.model import Complaint

    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    query = query.order_by(Complaint.created_at.desc())

    headers = [
        "complaint_id", "user_id", "order_id", "category",
        "status", "description", "created_at",
    ]

    def rows():
        for c in query.yield_per(200):
            yield [
                c.id,
                c.user_id,
                getattr(c, "order_id", ""),
                c.category,
                c.status,
                (c.description or "").replace("\n", " "),
                c.created_at.isoformat() if c.created_at else "",
            ]

    return _stream_csv(headers, rows())


def export_revenue_csv(
    db: Session,
    date_from: str | None = None,
    date_to: str | None = None,
) -> StreamingResponse:
    from app.modules.payments.model import Payment, PaymentStatus

    query = (
        db.query(
            func.cast(Payment.created_at, Date).label("date"),
            func.count(Payment.id).label("transaction_count"),
            func.sum(Payment.amount).label("total_revenue"),
        )
        .filter(Payment.status == PaymentStatus.SUCCESS)
        .group_by(func.cast(Payment.created_at, Date))
        .order_by(func.cast(Payment.created_at, Date).asc())
    )

    if date_from:
        query = query.filter(Payment.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Payment.created_at <= datetime.fromisoformat(date_to))

    headers = ["date", "transaction_count", "total_revenue_inr"]

    def rows():
        for row in query:
            yield [row.date, row.transaction_count, float(row.total_revenue or 0)]

    return _stream_csv(headers, rows())
