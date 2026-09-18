from pydantic import BaseModel
from typing import Optional

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    page: Optional[int] = None
    line_number: Optional[int] = None
