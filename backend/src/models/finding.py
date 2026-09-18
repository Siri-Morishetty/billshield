from typing import List, Optional
from pydantic import BaseModel

class Finding(BaseModel):
    finding_id: str
    bill_id: str
    type: str # e.g. "NEW_CHARGE", "CALCULATION_DISCREPANCY"
    priority: str # "HIGH", "MEDIUM", "LOW"
    title: str
    description: str
    amount: Optional[float] = None
    evidence_ids: List[str] = []
