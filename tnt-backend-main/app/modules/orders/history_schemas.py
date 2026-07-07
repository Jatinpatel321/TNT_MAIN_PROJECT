from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrderHistoryResponse(BaseModel):
    status: str
    changed_at: datetime
    actor: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
