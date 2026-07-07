"""Admin service layer — user listing, status management."""

from typing import Optional

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.users.model import User


def list_users(
    db: Session,
    page: int,
    page_size: int,
    search: Optional[str],
    role: Optional[str],
    is_active: Optional[bool],
) -> dict:
    query = db.query(User)

    # --- Filtering ---
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(pattern),
                User.name.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # --- Totals (before pagination) ---
    total = query.count()

    # --- Role-based summary counts ---
    role_counts = (
        db.query(User.role, func.count(User.id))
        .filter(*_build_filters(search, role, is_active))
        .group_by(User.role)
        .all()
    )
    role_summary = {str(r): c for r, c in role_counts}

    # --- Pagination ---
    offset = (page - 1) * page_size
    users = (
        query.order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),  # ceiling division
        "role_summary": role_summary,
    }


def _make_filters(search, role, is_active):
    """Helper to rebuild filter conditions for the role summary subquery."""
    conditions = []
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.full_name.ilike(pattern),
                User.name.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    return conditions


_build_filters = _make_filters


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def set_user_active(db: Session, user_id: int, is_active: bool) -> Optional[User]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user