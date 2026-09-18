from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
from .line_item import LineItem

class BillingPeriod(BaseModel):
    start_date: date
    end_date: date

class SourceDocument(BaseModel):
    s3_key: str
    page_count: int

class Bill(BaseModel):
    bill_id: str
    user_id: str
    bill_type: str # "internet", "electricity", etc.
    provider: str
    billing_period: Optional[BillingPeriod] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_number: Optional[str] = None
    currency: str = "USD"
    subtotal: float
    discount: float = 0.0
    taxable_amount: float = 0.0
    tax_rate: float = 0.0
    tax: float = 0.0
    fees: float = 0.0
    total: float
    line_items: List[LineItem] = []
    source_document: Optional[SourceDocument] = None
    extraction_status: str = "completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
