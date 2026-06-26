"""Pydantic schemas for audit log module (pydantic v2)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: str
    action_category: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    metadata_field: Optional[Dict[str, Any]] = Field(None, alias="metadata")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogEntry] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1