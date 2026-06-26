"""Pydantic schemas for admin module (pydantic v2)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone: str = ""
    role: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None


class AdminUserDetailResponse(AdminUserSummary):
    preferences: Optional[Dict[str, Any]] = None
    order_count: Optional[int] = None
    last_active_at: Optional[datetime] = None


class AdminUserListResponse(BaseModel):
    users: List[AdminUserSummary] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    role_summary: Dict[str, int] = {}


class AdminUserStatusUpdate(BaseModel):
    is_active: bool = True


class AdminUserRoleUpdate(BaseModel):
    role: str