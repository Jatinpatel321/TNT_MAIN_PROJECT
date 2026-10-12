from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, validator


class OrderHistoryResponse(BaseModel):
    status: Any
    changed_at: datetime
    actor: Optional[str] = None
    note: Optional[str] = None

    @validator("status", pre=True)
    def normalize_status(cls, v):
        if hasattr(v, "value"):
            return str(v.value)
        return str(v) if v is not None else ""

    model_config = ConfigDict(from_attributes=True)

