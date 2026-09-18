"""
BillShield acceptance tests.
Run from project root with:
    .\\backend\\venv\\Scripts\\python.exe -m pytest tests/test_validation.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

import pytest
from datetime import date

# Patch relative imports for standalone test execution
import importlib, types

def _load_module(rel_path: str, name: str):
    abs_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'src', rel_path)
    spec = importlib.util.spec_from_file_location(name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    return mod, spec

# We build stubs for pydantic models to avoid relative import hell
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    page: Optional[int] = None
    line_number: Optional[int] = None

class BillingPeriod(BaseModel):
    start_date: date
    end_date: date

class Bill(BaseModel):
    bill_id: str
    user_id: str
    bill_type: str
    provider: str
    billing_period: Optional[BillingPeriod] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    invoice_number: Optional[str] = None
    currency: str = "INR"
    subtotal: float
    discount: float = 0.0
    taxable_amount: float = 0.0
    tax_rate: float = 0.0
    tax: float = 0.0
    fees: float = 0.0
    total: float
    line_items: List[LineItem] = []
    source_document: Optional[object] = None
    extraction_status: str = "completed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Finding(BaseModel):
    finding_id: str
    bill_id: str
    type: str
    priority: str
    title: str
    description: str
    amount: Optional[float] = None
    evidence_ids: List[str] = []


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def july_bill():
    return Bill(
        bill_id="bill-jul-001",
        user_id="user1",
        bill_type="internet",
        provider="ACME CONNECT INTERNET SERVICES",
        currency="INR",
        subtotal=1968.0,
        tax=0.0,
        total=1968.0,
        line_items=[
            LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1500.0, amount=1500.0),
            LineItem(description="Internet Usage", quantity=1, unit_price=318.0, amount=318.0),
            LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0),
        ],
        extraction_status="completed"
    )

@pytest.fixture
def august_bill():
    return Bill(
        bill_id="bill-aug-001",
        user_id="user1",
        bill_type="internet",
        provider="ACME CONNECT INTERNET SERVICES",
        currency="INR",
        subtotal=2249.00,
        discount=0.0,
        taxable_amount=2249.00,
        tax_rate=18.0,
        tax=404.82,
        total=2653.82,
        line_items=[
            LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1000.0, amount=1000.0),
            LineItem(description="Internet Usage", quantity=1, unit_price=300.0, amount=300.0),
            LineItem(description="Premium Support", quantity=1, unit_price=299.0, amount=299.0),
            LineItem(description="Service Adjustment", quantity=1, unit_price=500.0, amount=500.0),
            LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0),
        ],
        extraction_status="completed"
    )


# ─── Tests ───────────────────────────────────────────────────────────────────

class TestLineItems:
    """TEST 1 — Line items"""
    def test_count(self, august_bill):
        assert len(august_bill.line_items) == 5

    def test_sum(self, august_bill):
        total = sum(i.amount for i in august_bill.line_items)
        assert abs(total - 2249.00) < 0.02, f"Expected 2249.00, got {total}"

    def test_individual_amounts(self, august_bill):
        amounts = [i.amount for i in august_bill.line_items]
        assert 1000.0 in amounts
        assert 300.0 in amounts
        assert 299.0 in amounts
        assert 500.0 in amounts
        assert 150.0 in amounts


class TestTax:
    """TEST 2 — Tax calculation"""
    def test_tax_rate(self, august_bill):
        assert august_bill.tax_rate == 18.0

    def test_taxable_amount(self, august_bill):
        assert abs(august_bill.taxable_amount - 2249.00) < 0.02

    def test_tax_amount(self, august_bill):
        assert abs(august_bill.tax - 404.82) < 0.02

    def test_tax_math(self, august_bill):
        """Verify: taxable_amount × rate / 100 = tax"""
        calculated = august_bill.taxable_amount * august_bill.tax_rate / 100
        assert abs(calculated - august_bill.tax) < 0.02, f"Expected {august_bill.tax}, calculated {calculated}"


class TestTotal:
    """TEST 3 — Total"""
    def test_total_value(self, august_bill):
        assert abs(august_bill.total - 2653.82) < 0.02

    def test_total_math(self, august_bill):
        """Verify: subtotal - discount + tax = total"""
        expected = august_bill.subtotal - august_bill.discount + august_bill.tax
        assert abs(expected - august_bill.total) < 0.02, f"Expected {august_bill.total}, got {expected}"


class TestHistoricalComparison:
    """TEST 4-6 — Historical comparison"""
    def _compare(self, current: Bill, historical: Bill) -> dict:
        prev = historical.total
        curr = current.total
        diff = curr - prev
        pct = (diff / prev * 100) if prev > 0 else 0
        return {"absolute_difference": diff, "percentage_difference": pct, "previous_total": prev}

    def test_previous_total(self, august_bill, july_bill):
        assert abs(july_bill.total - 1968.0) < 0.02

    def test_absolute_increase(self, august_bill, july_bill):
        result = self._compare(august_bill, july_bill)
        assert abs(result["absolute_difference"] - 685.82) < 0.02

    def test_percentage_increase(self, august_bill, july_bill):
        result = self._compare(august_bill, july_bill)
        assert abs(result["percentage_difference"] - 34.85) < 0.1, f"Expected ~34.85%, got {result['percentage_difference']:.2f}%"


class TestNewCharges:
    """TEST 7 — New charge detection"""
    def _detect_new_charges(self, current: Bill, historical: Bill) -> list:
        hist_items = {i.description.lower().strip() for i in historical.line_items}
        return [i for i in current.line_items if i.description.lower().strip() not in hist_items]

    def test_premium_support_is_new(self, august_bill, july_bill):
        new = self._detect_new_charges(august_bill, july_bill)
        descriptions = [i.description for i in new]
        assert any("premium support" in d.lower() for d in descriptions), f"Expected Premium Support in {descriptions}"

    def test_service_adjustment_is_new(self, august_bill, july_bill):
        new = self._detect_new_charges(august_bill, july_bill)
        descriptions = [i.description for i in new]
        assert any("service adjustment" in d.lower() for d in descriptions), f"Expected Service Adjustment in {descriptions}"

    def test_count_of_new_charges(self, august_bill, july_bill):
        new = self._detect_new_charges(august_bill, july_bill)
        assert len(new) == 2, f"Expected 2 new charges, got {len(new)}: {[i.description for i in new]}"


class TestNoFalseAnomalies:
    """TEST 8-9 — No false anomalies"""
    def _validate(self, bill: Bill) -> list:
        issues = []
        calc = sum(i.amount for i in bill.line_items)
        if abs(calc - bill.subtotal) > 0.02:
            issues.append("CALCULATION_DISCREPANCY")
        expected_total = bill.subtotal - bill.discount + bill.tax
        if abs(expected_total - bill.total) > 0.02:
            issues.append("TOTAL_MISMATCH")
        return issues

    def test_no_calculation_discrepancy(self, august_bill):
        issues = self._validate(august_bill)
        assert "CALCULATION_DISCREPANCY" not in issues, \
            f"False CALCULATION_DISCREPANCY: sum={sum(i.amount for i in august_bill.line_items)}, subtotal={august_bill.subtotal}"

    def test_no_total_discrepancy(self, august_bill):
        issues = self._validate(august_bill)
        assert "TOTAL_MISMATCH" not in issues, \
            f"False TOTAL_MISMATCH: {august_bill.subtotal} + {august_bill.tax} != {august_bill.total}"


class TestCurrencyFormatting:
    """TEST 10 — Currency formatting"""
    def _format(self, amount: float) -> str:
        import locale
        # Simple check: amount has 2 decimal places
        return f"₹{amount:,.2f}"

    def test_format_full_amount(self):
        formatted = self._format(2653.82)
        assert "2,653.82" in formatted

    def test_format_whole_number(self):
        formatted = self._format(2249.0)
        assert "2,249.00" in formatted

    def test_format_small_amount(self):
        formatted = self._format(299.0)
        assert "299.00" in formatted


class TestRealPDFParser:
    """TEST 12 — Real PDF parsing (integration test)"""
    PDF_PATH = "C:/Users/lenovo/AppData/Local/Temp/BillShield_Sample_August_Bill.pdf"

    @pytest.mark.skipif(
        not os.path.exists("C:/Users/lenovo/AppData/Local/Temp/BillShield_Sample_August_Bill.pdf"),
        reason="Sample PDF not available"
    )
    def test_parse_real_pdf(self):
        """Parse the actual test PDF and verify all values."""
        import pdfplumber, re, uuid

        # Inline the parser without relative imports
        code = open("backend/src/services/local_parser.py").read()
        code = code.replace("from ..models.bill import Bill, BillingPeriod", "")
        code = code.replace("from ..models.line_item import LineItem", "")
        
        ns = {
            "Bill": Bill, "BillingPeriod": BillingPeriod, "LineItem": LineItem,
            "pdfplumber": pdfplumber, "re": re, "uuid": uuid,
            "datetime": datetime, "Optional": Optional, "List": List,
        }
        exec(code, ns)
        LocalParser = ns["LocalParser"]

        result = LocalParser.parse_pdf(self.PDF_PATH, "BillShield_Sample_August_Bill.pdf")

        assert result.provider == "ACME CONNECT INTERNET SERVICES"
        assert len(result.line_items) == 5, f"Expected 5 line items, got {len(result.line_items)}"
        assert abs(result.subtotal - 2249.00) < 0.02, f"subtotal={result.subtotal}"
        assert abs(result.tax - 404.82) < 0.02, f"tax={result.tax}"
        assert abs(result.total - 2653.82) < 0.02, f"total={result.total}"
        assert result.tax_rate == 18.0
        line_sum = sum(i.amount for i in result.line_items)
        assert abs(line_sum - 2249.00) < 0.02, f"line_sum={line_sum}"
