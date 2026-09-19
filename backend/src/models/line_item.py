from pydantic import BaseModel
from typing import Optional

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float
    adjustment: Optional[float] = None
    page: Optional[int] = None
    line_number: Optional[int] = None
