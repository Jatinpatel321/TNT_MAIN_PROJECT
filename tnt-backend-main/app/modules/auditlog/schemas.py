"""Pydantic schemas for audit log module (pydantic v2)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
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


class TopActor(BaseModel):
    actor_id: Optional[int] = None
    actor_name: str
    event_count: int


class AuditStatsResponse(BaseModel):
    total_events: int
    today_events: int
    week_events: int
    auth_events: int
    order_events: int
    flagged_events: int
    category_counts: Dict[str, int]
    top_actors: List[TopActor]
    total_logs_30d: int = 0
    active_users_30d: int = 0
    critical_actions_30d: int = 0
    actions_by_category: Dict[str, int] = {}


class AuditTimelineResponse(BaseModel):
    logs: List[AuditLogEntry] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1