from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BroadcastCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    severity: str = Field(default="info", pattern=r"^(info|warning|critical)$")
    audience: str = Field(default="all", pattern=r"^(all|faculty|vendor_customers)$")
    vendor_id: Optional[int] = Field(default=None, ge=1)


class BroadcastResponse(BaseModel):
    id: int
    title: str
    message: str
    severity: str
    audience: str
    sent_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class BroadcastListResponse(BaseModel):
    broadcasts: List[BroadcastResponse]
    total: int
