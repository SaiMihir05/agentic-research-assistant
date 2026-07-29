from pydantic import BaseModel
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

    class Config:
        from_attributes = True
