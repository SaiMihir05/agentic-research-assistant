from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class QueryBase(BaseModel):
    topic: str

class QueryCreate(QueryBase):
    user_id: int

class QueryResponse(QueryBase):
    id: int
    user_id: int
    result: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
