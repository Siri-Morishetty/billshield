from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone

class User(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
