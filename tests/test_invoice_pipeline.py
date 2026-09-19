"""
BillShield Comprehensive Invoice Pipeline & Deterministic Validation Test Suite.
Tests:
1. INV-3337 sample invoice extraction & validation (no false mismatch, correct $85/$8.50/$93.50).
2. Genuine calculation discrepancy detection (catches actual arithmetic errors).
3. Missing/incomplete fields (null safety, UNKNOWN status, no false 0.0 conversions).
4. Line item quantity calculation & sum verification.
5. Line item adjustment handling (percentages vs monetary amounts).
6. Currency preservation ($ -> USD, ₹ -> INR, € -> EUR, £ -> GBP).
7. Rounding tolerance (up to 0.02 difference does not trigger false alerts).
8. 3 distinct invoice structures (5-column service table, 2-column utility table, unstructured text).

Run with:
    .\\backend\\venv\\Scripts\\python.exe -m pytest tests/test_invoice_pipeline.py -v
"""
import sys
import os
import pytest

# Ensure backend and src are on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from backend.src.models.bill import Bill, BillingPeriod
from backend.src.models.line_item import LineItem
from backend.src.services.local_parser import LocalParser, _parse_amount, _detect_currency
from backend.src.services.validation_engine import ValidationEngine, _curr_sym


# ==============================================================================
# TEST 1: INV-3337 End-to-End Extraction & Validation (Core User Bug)
# ==============================================================================
def test_inv_3337_extraction_and_zero_false_mismatch():
    """
    Simulates the exact structure of invoice INV-3337:
      Invoice Number: INV-3337
      5-column table: Quantity, Service, Rate/Price, Adjustment, Sub Total
      1.00 | Web Design | $85.00 | 0.00% | $85.00
      Totals below:
      Sub Total: $85.00
      Tax: $8.50
      Total: $93.50

    Must extract:
      - subtotal: 85.00 (NOT 0.0)
      - tax: 8.50
      - total: 93.50
      - currency: USD
      - validation: PASS, ZERO findings
    """
    text = (
        "Acme Creative Agency\n"
        "Invoice Number: INV-3337\n"
        "Date: 2026-08-15\n"
        "Due Date: 2026-08-30\n"
        "\n"
        "Quantity  Service      Rate/Price  Adjustment  Sub Total\n"
        "1.00      Web Design   $85.00      0.00%       $85.00\n"
        "\n"
        "Sub Total: $85.00\n"
        "Tax: $8.50\n"
        "Total: $93.50\n"
    )
    tables = [
        {
            "page": 1,
            "rows": [
                ["Quantity", "Service", "Rate/Price", "Adjustment", "Sub Total"],
                ["1.00", "Web Design", "$85.00", "0.00%", "$85.00"],
            ]
        }
    ]

    bill = LocalParser._build_bill(text, tables, "INV-3337.pdf", 1)

    assert bill.invoice_number == "INV-3337"
    assert bill.currency == "USD"
    assert bill.subtotal == 85.00, f"Expected subtotal 85.00, got {bill.subtotal}"
    assert bill.tax == 8.50, f"Expected tax 8.50, got {bill.tax}"
    assert bill.total == 93.50, f"Expected total 93.50, got {bill.total}"
    assert len(bill.line_items) == 1
    assert bill.line_items[0].description == "Web Design"
    assert bill.line_items[0].unit_price == 85.00
    assert bill.line_items[0].quantity == 1.00
    assert bill.line_items[0].amount == 85.00

    findings = ValidationEngine.validate(bill)

    # Must produce ZERO findings (no false TOTAL_MISMATCH or CALCULATION_DISCREPANCY)
    assert len(findings) == 0, f"Expected 0 findings for clean bill, got: {[f.title for f in findings]}"
    assert bill.validation_status.get("total_calculation") == "PASS"
    assert bill.validation_status.get("subtotal_matches_items") == "PASS"
    assert bill.validation_status.get("line_items_arithmetic") == "PASS"


# ==============================================================================
# TEST 2: Genuine Calculation Discrepancy Detection
# ==============================================================================
def test_genuine_total_mismatch_detected():
    """
    Subtotal: $85.00, Tax: $8.50, but bill charges Total: $100.00.
    Must flag TOTAL_MISMATCH with difference $6.50 and priority HIGH.
    """
    bill = Bill(
        bill_id="test-mismatch-1",
        user_id="user-1",
        bill_type="service",
        provider="Acme Agency",
        currency="USD",
        subtotal=85.00,
        tax=8.50,
        total=100.00,  # 85 + 8.50 = 93.50 != 100.00
        line_items=[
            LineItem(description="Web Design", quantity=1.0, unit_price=85.0, amount=85.0)
        ]
    )

    findings = ValidationEngine.validate(bill)
    assert len(findings) == 1
    f = findings[0]
    assert f.type == "TOTAL_MISMATCH"
    assert f.priority == "HIGH"
    assert abs(f.amount - 6.50) < 0.01
    assert "$6.50" in f.description
    assert bill.validation_status.get("total_calculation") == "FAIL"


# ==============================================================================
# TEST 3: Missing Fields & Null Safety (Never Default to 0.0)
# ==============================================================================
def test_missing_subtotal_is_none_and_status_unknown():
    """
    When subtotal is missing from an invoice without line items:
    - subtotal must remain None (NOT 0.0).
    - Validation engine must NOT flag a false total mismatch of $93.50.
    - total_calculation status must be UNKNOWN.
    """
    bill = Bill(
        bill_id="test-null-subtotal",
        user_id="user-1",
        bill_type="utility",
        provider="Power Co",
        currency="USD",
        subtotal=None,
        tax=8.50,
        total=93.50,
        line_items=[]
    )

    assert bill.subtotal is None
    findings = ValidationEngine.validate(bill)

    # Should not raise false total mismatch because subtotal is unknown
    mismatch_findings = [f for f in findings if f.type == "TOTAL_MISMATCH"]
    assert len(mismatch_findings) == 0
    assert bill.validation_status.get("total_calculation") == "UNKNOWN"


# ==============================================================================
# TEST 4: Line Item Quantity Arithmetic & Sum Verification
# ==============================================================================
def test_line_item_quantity_math():
    """
    3 units @ $20.00 = $60.00
    1 unit  @ $85.00 = $85.00
    Subtotal: $145.00
    Tax: $14.50
    Total: $159.50
    """
    bill = Bill(
        bill_id="test-qty-1",
        user_id="user-1",
        bill_type="retail",
        provider="Design Depot",
        currency="USD",
        subtotal=145.00,
        tax=14.50,
        total=159.50,
        line_items=[
            LineItem(description="Icon Pack", quantity=3.0, unit_price=20.0, amount=60.0),
            LineItem(description="Consulting", quantity=1.0, unit_price=85.0, amount=85.0),
        ]
    )

    findings = ValidationEngine.validate(bill)
    assert len(findings) == 0
    assert bill.validation_status.get("line_items_arithmetic") == "PASS"
    assert bill.validation_status.get("subtotal_matches_items") == "PASS"
    assert bill.validation_status.get("total_calculation") == "PASS"


def test_line_item_arithmetic_error_detected():
    """
    Line item shows 3 @ $20.00 = $70.00 (arithmetic error on bill).
    Must generate LINE_ITEM_MISMATCH with difference $10.00.
    """
    bill = Bill(
        bill_id="test-qty-err",
        user_id="user-1",
        bill_type="retail",
        provider="Design Depot",
        currency="USD",
        subtotal=155.00,
        tax=15.50,
        total=170.50,
        line_items=[
            LineItem(description="Icon Pack", quantity=3.0, unit_price=20.0, amount=70.0),
            LineItem(description="Consulting", quantity=1.0, unit_price=85.0, amount=85.0),
        ]
    )

    findings = ValidationEngine.validate(bill)
    line_errs = [f for f in findings if f.type == "LINE_ITEM_MISMATCH"]
    assert len(line_errs) == 1
    assert abs(line_errs[0].amount - 10.00) < 0.01
    assert bill.validation_status.get("line_items_arithmetic") == "FAIL"


# ==============================================================================
# TEST 5: Currency Preservation Across Supported Locales
# ==============================================================================
@pytest.mark.parametrize("text,expected_curr,expected_sym", [
    ("Total Due: $93.50 USD", "USD", "$"),
    ("Grand Total: ₹2,653.82 GST included", "INR", "₹"),
    ("Total: €120.50 EUR", "EUR", "€"),
    ("Amount Due: £89.00 GBP", "GBP", "£"),
])
def test_currency_detection_and_symbol_mapping(text, expected_curr, expected_sym):
    detected = _detect_currency(text)
    assert detected == expected_curr, f"For '{text}', expected {expected_curr}, got {detected}"
    sym = _curr_sym(detected)
    assert sym == expected_sym, f"For {detected}, expected symbol {expected_sym}, got {sym}"


# ==============================================================================
# TEST 6: Rounding Tolerance (Up to 0.02)
# ==============================================================================
def test_rounding_tolerance_no_false_alarm():
    """
    Subtotal 10.00 + Tax 0.83 = 10.83, but bill says 10.84 due to half-cent rounding.
    Within 0.02 tolerance -> Must PASS without raising false alarm.
    """
    bill = Bill(
        bill_id="test-rounding",
        user_id="user-1",
        bill_type="utility",
        provider="Metro Water",
        currency="USD",
        subtotal=10.00,
        tax=0.83,
        total=10.84,  # difference = 0.01
        line_items=[
            LineItem(description="Water Consumption", quantity=1.0, unit_price=10.0, amount=10.0)
        ]
    )

    findings = ValidationEngine.validate(bill)
    mismatch = [f for f in findings if f.type == "TOTAL_MISMATCH"]
    assert len(mismatch) == 0
    assert bill.validation_status.get("total_calculation") == "PASS"


# ==============================================================================
# TEST 7: Diverse Invoice Structures (3 Distinct Formats)
# ==============================================================================
def test_invoice_structure_a_service_table():
    """
    Structure A: 5-column table with Qty, Description, Unit Price, Adjustment, Total.
    Totals rendered in table footer rows.
    """
    text = (
        "Global Dev Studio\n"
        "Invoice: INV-4491\n"
        "Sub Total: $250.00\n"
        "Tax: $25.00\n"
        "Total: $275.00\n"
    )
    tables = [
        {
            "page": 1,
            "rows": [
                ["Qty", "Description", "Rate", "Adj", "Amount"],
                ["2.0", "Logo Design", "$100.00", "0%", "$200.00"],
                ["1.0", "Domain Setup", "$50.00", "0%", "$50.00"],
                ["", "Sub Total", "", "", "$250.00"],
                ["", "Tax (10%)", "", "", "$25.00"],
                ["", "Grand Total", "", "", "$275.00"],
            ]
        }
    ]

    bill = LocalParser._build_bill(text, tables, "Structure_A.pdf", 1)
    assert bill.subtotal == 250.00
    assert bill.tax == 25.00
    assert bill.total == 275.00
    assert len(bill.line_items) == 2
    findings = ValidationEngine.validate(bill)
    assert len(findings) == 0


def test_invoice_structure_b_two_column_utility():
    """
    Structure B: 2-column key-value utility bill.
    Item/Particulars in column 1, Amount in column 2.
    """
    text = (
        "City Electric Utility\n"
        "Account: ELEC-9912\n"
        "Issue Date: 2026-08-01\n"
        "Base Energy Charge: $65.00\n"
        "Grid Maintenance: $15.00\n"
        "Subtotal: $80.00\n"
        "State Tax: $8.00\n"
        "Total Due: $88.00\n"
    )
    tables = [
        {
            "page": 1,
            "rows": [
                ["Charges", "Amount"],
                ["Base Energy Charge", "$65.00"],
                ["Grid Maintenance", "$15.00"],
                ["Subtotal", "$80.00"],
                ["State Tax", "$8.00"],
                ["Total Due", "$88.00"],
            ]
        }
    ]

    bill = LocalParser._build_bill(text, tables, "Structure_B.pdf", 1)
    assert bill.subtotal == 80.00
    assert bill.tax == 8.00
    assert bill.total == 88.00
    assert len(bill.line_items) == 2
    findings = ValidationEngine.validate(bill)
    assert len(findings) == 0


def test_invoice_structure_c_unstructured_text_only():
    """
    Structure C: Raw unstructured text without table grids.
    Extracted purely via horizontal regex matchers and text line item heuristics.
    """
    text = (
        "Apex Cloud Hosting Services\n"
        "Invoice: INV-8821\n"
        "Date: 2026-08-10\n"
        "\n"
        "Cloud Server Pro: $40.00\n"
        "Storage Addon 100GB: $10.00\n"
        "\n"
        "Sub Total: $50.00\n"
        "Tax: $5.00\n"
        "Total: $55.00\n"
    )
    # No tables extracted by pdfplumber
    tables = []

    bill = LocalParser._build_bill(text, tables, "Structure_C.pdf", 1)
    assert bill.subtotal == 50.00
    assert bill.tax == 5.00
    assert bill.total == 55.00
    assert bill.currency == "USD"
    findings = ValidationEngine.validate(bill)
    assert len(findings) == 0
    assert bill.validation_status.get("total_calculation") == "PASS"
