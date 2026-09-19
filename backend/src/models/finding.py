from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Finding(BaseModel):
    finding_id: str
    bill_id: str
    type: str          # e.g. "NEW_CHARGE", "TOTAL_MISMATCH", "PRICE_INCREASE"
    priority: str      # "HIGH", "MEDIUM", "LOW"
    title: str
    description: str
    amount: Optional[float] = None
    evidence_ids: List[str] = []
    evidence: Optional[Dict[str, Any]] = None  # structured evidence for UI display
