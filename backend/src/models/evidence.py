from pydantic import BaseModel
from typing import Optional

class Evidence(BaseModel):
    evidence_id: str
    bill_id: str
    page: Optional[int] = None
    line_number: Optional[int] = None
    text: str
    source: str = "current_bill"
