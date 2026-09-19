from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime, timezone
from .line_item import LineItem


class BillingPeriod(BaseModel):
    start_date: date
    end_date: date


class SourceDocument(BaseModel):
    s3_key: str
    page_count: int = 1


class Bill(BaseModel):
    bill_id: str
    user_id: str
    bill_type: str                        # "internet", "electricity", "utility", "invoice"
    provider: str
    billing_period: Optional[BillingPeriod] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_number: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    discount: Optional[float] = 0.0
    taxable_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    tax: Optional[float] = None
    fees: Optional[float] = 0.0
    total: Optional[float] = None
    line_items: List[LineItem] = []
    source_document: Optional[Any] = None
    extraction_status: str = "completed"
    reported: Dict[str, Optional[float]] = Field(default_factory=dict)
    calculated: Dict[str, Optional[float]] = Field(default_factory=dict)
    validation_status: Dict[str, str] = Field(default_factory=dict)
    # Demo bill metadata — not present on uploaded bills
    is_demo: bool = False
    demo_label: Optional[str] = None
    demo_description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
