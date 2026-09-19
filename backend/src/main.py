"""
BillShield FastAPI Backend
Local mode: USE_MOCK_AWS=true (default) — no AWS credentials needed.
AWS mode:   USE_MOCK_AWS=false — uses S3, Textract, DynamoDB, Bedrock.
"""
import os
import tempfile
import uuid
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models.bill import Bill, BillingPeriod
from .models.finding import Finding
from .models.line_item import LineItem
from .services.local_parser import LocalParser
from .services.validation_engine import ValidationEngine
from .services.anomaly_engine import AnomalyEngine
from .services.history_engine import HistoryEngine

app = FastAPI(title="BillShield API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# DEMO / SEED BILLS
# ─────────────────────────────────────────────

def _make_demo_bills() -> List[Bill]:
    """
    Five deterministic synthetic demo bills.
    All numbers are internally consistent with the findings they produce.
    No real personal data — synthetic only.
    """

    # ── Demo 1: Clean bill — no issues ──
    clean = Bill(
        bill_id="demo-clean-001",
        user_id="demo-user",
        bill_type="internet",
        provider="ACME CONNECT INTERNET SERVICES",
        billing_period=BillingPeriod(start_date="2026-06-01", end_date="2026-06-30"),
        issue_date="2026-07-01",
        due_date="2026-07-15",
        invoice_number="INV-2026-JUN-001",
        currency="INR",
        subtotal=1968.0,
        discount=0.0,
        taxable_amount=1968.0,
        tax_rate=0.0,
        tax=0.0,
        fees=0.0,
        total=1968.0,
        line_items=[
            LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1500.0, amount=1500.0),
            LineItem(description="Internet Usage", quantity=1, unit_price=318.0, amount=318.0),
            LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0),
        ],
        extraction_status="completed",
        is_demo=True,
        demo_label="Clean Bill",
        demo_description="No issues detected — all calculations verified.",
    )

    # ── Demo 2: Total mismatch ──
    # Line items: 1000 + 500 + 300 = 1800 subtotal. Bill shows 1880. Mismatch = 80.
    total_mismatch = Bill(
        bill_id="demo-mismatch-002",
        user_id="demo-user",
        bill_type="electricity",
        provider="POWERHOUSE ELECTRICITY BOARD",
        billing_period=BillingPeriod(start_date="2026-07-01", end_date="2026-07-31"),
        issue_date="2026-08-01",
        due_date="2026-08-15",
        invoice_number="INV-2026-JUL-002",
        currency="INR",
        subtotal=1800.0,
        discount=0.0,
        taxable_amount=1800.0,
        tax_rate=0.0,
        tax=0.0,
        fees=0.0,
        total=1880.0,  # ← intentional mismatch: should be 1800
        line_items=[
            LineItem(description="Energy Consumption - 200 Units", quantity=200, unit_price=5.0, amount=1000.0),
            LineItem(description="Fixed Charges", quantity=1, unit_price=500.0, amount=500.0),
            LineItem(description="Meter Rent", quantity=1, unit_price=300.0, amount=300.0),
        ],
        extraction_status="completed",
        is_demo=True,
        demo_label="Total Mismatch",
        demo_description="Bill total ₹1,880 does not match sum of charges ₹1,800.",
    )

    # ── Demo 3: New charge ──
    # Previous: Internet 899. Current: Internet 899 + Convenience Fee 199.
    new_charge = Bill(
        bill_id="demo-newcharge-003",
        user_id="demo-user",
        bill_type="internet",
        provider="SWIFT BROADBAND LTD",
        billing_period=BillingPeriod(start_date="2026-08-01", end_date="2026-08-31"),
        issue_date="2026-09-01",
        due_date="2026-09-15",
        invoice_number="INV-2026-AUG-003",
        currency="INR",
        subtotal=1098.0,
        discount=0.0,
        taxable_amount=1098.0,
        tax_rate=0.0,
        tax=0.0,
        fees=0.0,
        total=1098.0,
        line_items=[
            LineItem(description="Internet Plan - 100 Mbps", quantity=1, unit_price=899.0, amount=899.0),
            LineItem(description="Convenience Fee", quantity=1, unit_price=199.0, amount=199.0),
        ],
        extraction_status="completed",
        is_demo=True,
        demo_label="New Charge",
        demo_description="'Convenience Fee' (₹199) appears for the first time.",
    )

    # ── Demo 4: Price increase ──
    # Previous: Internet 899. Current: Internet 1099. Increase = 200 (22.2%).
    price_increase = Bill(
        bill_id="demo-priceinc-004",
        user_id="demo-user",
        bill_type="internet",
        provider="GLOBALNET TELECOM",
        billing_period=BillingPeriod(start_date="2026-08-01", end_date="2026-08-31"),
        issue_date="2026-09-01",
        due_date="2026-09-15",
        invoice_number="INV-2026-AUG-004",
        currency="INR",
        subtotal=1099.0,
        discount=0.0,
        taxable_amount=1099.0,
        tax_rate=0.0,
        tax=0.0,
        fees=0.0,
        total=1099.0,
        line_items=[
            LineItem(description="Broadband Plan", quantity=1, unit_price=1099.0, amount=1099.0),
        ],
        extraction_status="completed",
        is_demo=True,
        demo_label="Price Increase",
        demo_description="Internet plan rose from ₹899 → ₹1,099 (↑22.2%).",
    )

    # ── Demo 5: Multiple findings ──
    # Issues: new charge, price increase, subtotal mismatch
    multiple = Bill(
        bill_id="demo-multi-005",
        user_id="demo-user",
        bill_type="internet",
        provider="ACME CONNECT INTERNET SERVICES",
        billing_period=BillingPeriod(start_date="2026-08-01", end_date="2026-08-31"),
        issue_date="2026-09-01",
        due_date="2026-09-15",
        invoice_number="INV-2026-AUG-005",
        currency="INR",
        subtotal=2249.0,
        discount=0.0,
        taxable_amount=2249.0,
        tax_rate=18.0,
        tax=404.82,
        fees=0.0,
        total=2653.82,
        line_items=[
            LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1000.0, amount=1000.0),  # was 1500
            LineItem(description="Internet Usage", quantity=1, unit_price=300.0, amount=300.0),  # was 318
            LineItem(description="Premium Support", quantity=1, unit_price=299.0, amount=299.0),  # new charge
            LineItem(description="Service Adjustment", quantity=1, unit_price=500.0, amount=500.0),  # new charge
            LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0),
        ],
        extraction_status="completed",
        is_demo=True,
        demo_label="Multiple Findings",
        demo_description="Price drop on Internet Plan, 2 new charges, 34.9% bill increase.",
    )

    return [clean, total_mismatch, new_charge, price_increase, multiple]


# ── Historical bills for comparison ──
def _make_historical_bills() -> Dict[str, List[Bill]]:
    """Historical bills keyed by provider for comparison."""
    return {
        # ACME clean June bill — referenced by demo-multi-005
        "ACME CONNECT INTERNET SERVICES": [
            Bill(
                bill_id="hist-acme-jun-001",
                user_id="demo-user",
                bill_type="internet",
                provider="ACME CONNECT INTERNET SERVICES",
                billing_period=BillingPeriod(start_date="2026-06-01", end_date="2026-06-30"),
                issue_date="2026-07-01",
                currency="INR",
                subtotal=1968.0,
                discount=0.0,
                taxable_amount=1968.0,
                tax_rate=0.0,
                tax=0.0,
                fees=0.0,
                total=1968.0,
                line_items=[
                    LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1500.0, amount=1500.0),
                    LineItem(description="Internet Usage", quantity=1, unit_price=318.0, amount=318.0),
                    LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0),
                ],
                extraction_status="completed",
            )
        ],
        # SWIFT BROADBAND previous bill (no Convenience Fee)
        "SWIFT BROADBAND LTD": [
            Bill(
                bill_id="hist-swift-jul-001",
                user_id="demo-user",
                bill_type="internet",
                provider="SWIFT BROADBAND LTD",
                billing_period=BillingPeriod(start_date="2026-07-01", end_date="2026-07-31"),
                issue_date="2026-08-01",
                currency="INR",
                subtotal=899.0,
                discount=0.0,
                taxable_amount=899.0,
                tax_rate=0.0,
                tax=0.0,
                fees=0.0,
                total=899.0,
                line_items=[
                    LineItem(description="Internet Plan - 100 Mbps", quantity=1, unit_price=899.0, amount=899.0),
                ],
                extraction_status="completed",
            )
        ],
        # GLOBALNET previous bill (lower price)
        "GLOBALNET TELECOM": [
            Bill(
                bill_id="hist-gnet-jul-001",
                user_id="demo-user",
                bill_type="internet",
                provider="GLOBALNET TELECOM",
                billing_period=BillingPeriod(start_date="2026-07-01", end_date="2026-07-31"),
                issue_date="2026-08-01",
                currency="INR",
                subtotal=899.0,
                discount=0.0,
                taxable_amount=899.0,
                tax_rate=0.0,
                tax=0.0,
                fees=0.0,
                total=899.0,
                line_items=[
                    LineItem(description="Broadband Plan", quantity=1, unit_price=899.0, amount=899.0),
                ],
                extraction_status="completed",
            )
        ],
    }


DEMO_BILLS = _make_demo_bills()
HISTORICAL_BILLS = _make_historical_bills()


def _run_analysis(bill: Bill, historical_bills: List[Bill]) -> List[Finding]:
    """Run the full deterministic analysis pipeline on a bill."""
    validation_findings = ValidationEngine.validate(bill)
    history_comparison = HistoryEngine.compare(bill, historical_bills)
    anomaly_findings = AnomalyEngine.detect(bill, historical_bills, history_comparison)
    return validation_findings + anomaly_findings


# ── Pre-compute demo findings ──
DEMO_FINDINGS: List[Finding] = []
for _demo_bill in DEMO_BILLS:
    _hist = HISTORICAL_BILLS.get(_demo_bill.provider, [])
    _findings = _run_analysis(_demo_bill, _hist)
    DEMO_FINDINGS.extend(_findings)


# ─────────────────────────────────────────────
# IN-MEMORY DATABASE (uploaded bills)
# ─────────────────────────────────────────────

DB_UPLOADED_BILLS: List[Bill] = []
DB_UPLOADED_FINDINGS: List[Finding] = []


# ─────────────────────────────────────────────
# API ROUTES
# ─────────────────────────────────────────────

@app.get("/api/bills")
def get_bills():
    """Returns all demo bills + user-uploaded bills."""
    return DEMO_BILLS + DB_UPLOADED_BILLS


@app.get("/api/bills/{bill_id}")
def get_bill(bill_id: str):
    all_bills = DEMO_BILLS + DB_UPLOADED_BILLS
    for b in all_bills:
        if b.bill_id == bill_id:
            return b
    raise HTTPException(status_code=404, detail="Bill not found")


@app.get("/api/bills/{bill_id}/findings")
def get_findings(bill_id: str):
    all_findings = DEMO_FINDINGS + DB_UPLOADED_FINDINGS
    return [f for f in all_findings if f.bill_id == bill_id]


@app.get("/api/bills/{bill_id}/history-comparison")
def get_history_comparison(bill_id: str):
    all_bills = DEMO_BILLS + DB_UPLOADED_BILLS
    bill = next((b for b in all_bills if b.bill_id == bill_id), None)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    historical = [
        b for b in all_bills
        if b.provider == bill.provider and b.bill_id != bill_id
    ]
    return HistoryEngine.compare(bill, historical)


@app.post("/api/upload")
async def upload_bill(file: UploadFile = File(...)):
    """
    Upload a real bill document.
    Local mode: parsed with pdfplumber (PDF only).
    AWS mode (USE_MOCK_AWS=false): upload to S3, process with Textract.
    """
    use_mock = os.getenv("USE_MOCK_AWS", "true").lower() == "true"

    # Validate file type
    allowed_ext = {".pdf", ".png", ".jpg", ".jpeg", ".json"}
    original_name = file.filename or "upload.bin"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: PDF, JSON, PNG, JPG."
        )

    # Validate file size (10 MB limit)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10 MB.")

    # Save to temp
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(contents)
    tmp.close()

    extraction_mode = "local"

    if ext == ".json":
        import json
        try:
            data = json.loads(contents.decode("utf-8"))
            if "bill_id" not in data:
                data["bill_id"] = f"bill-{uuid.uuid4().hex[:8]}"
            parsed_bill = Bill(**data)
            extraction_mode = "json"
        except Exception as e:
            os.unlink(tmp.name)
            raise HTTPException(status_code=400, detail=f"Invalid JSON bill format: {e}")
    elif use_mock or ext != ".pdf":
        # Local mode: only PDF parsing is supported without Textract
        if ext != ".pdf":
            os.unlink(tmp.name)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Image extraction ({ext}) requires AWS Textract (set USE_MOCK_AWS=false with AWS credentials). "
                    "In local demo mode, please upload a PDF or JSON bill."
                )
            )
        parsed_bill = LocalParser.parse_pdf(tmp.name, original_name)
    else:
        # AWS mode — Textract
        try:
            from .services.textract_service import TextractService
            from .services.s3_service import S3Service

            s3_key = f"uploads/{uuid.uuid4().hex}/{original_name}"
            S3Service.upload(tmp.name, s3_key)
            parsed_bill = TextractService.extract(s3_key, original_name)
            extraction_mode = "textract"
        except Exception as e:
            print(f"[AWS] Textract failed: {e}. Falling back to local parser.")
            if ext == ".pdf":
                parsed_bill = LocalParser.parse_pdf(tmp.name, original_name)
                extraction_mode = "local_fallback"
            else:
                os.unlink(tmp.name)
                raise HTTPException(
                    status_code=500,
                    detail=f"AWS Textract unavailable and local fallback requires PDF. Error: {e}"
                )

    os.unlink(tmp.name)

    # Find historical bills for this provider
    all_bills_for_provider = [
        b for b in (DEMO_BILLS + DB_UPLOADED_BILLS)
        if b.provider == parsed_bill.provider and b.bill_id != parsed_bill.bill_id
    ]

    # Run analysis
    all_findings = _run_analysis(parsed_bill, all_bills_for_provider)

    # Persist
    DB_UPLOADED_BILLS.insert(0, parsed_bill)
    DB_UPLOADED_FINDINGS.extend(all_findings)

    return {
        "status": "success",
        "bill_id": parsed_bill.bill_id,
        "extraction_mode": extraction_mode,   # "local" | "textract" | "local_fallback"
        "findings_count": len(all_findings),
        "provider": parsed_bill.provider,
        "currency": parsed_bill.currency,
        "subtotal": parsed_bill.subtotal,
        "tax": parsed_bill.tax,
        "total": parsed_bill.total,
        "line_items_count": len(parsed_bill.line_items),
        "high_findings": sum(1 for f in all_findings if f.priority == "HIGH"),
    }


@app.get("/api/investigate/{bill_id}")
def investigate_bill(bill_id: str):
    """Run the investigator agent on a bill — uses Bedrock if configured."""
    from .agent.investigator import BillInvestigatorAgent

    all_bills = DEMO_BILLS + DB_UPLOADED_BILLS
    bill = next((b for b in all_bills if b.bill_id == bill_id), None)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    historical = [
        b for b in all_bills
        if b.provider == bill.provider and b.bill_id != bill_id
    ]

    all_findings = DEMO_FINDINGS + DB_UPLOADED_FINDINGS
    findings = [f for f in all_findings if f.bill_id == bill_id]

    agent = BillInvestigatorAgent()
    return agent.investigate(bill, historical, findings)


@app.post("/api/clear")
def clear_uploaded_bills():
    """Clear only user-uploaded bills. Demo bills are always preserved."""
    global DB_UPLOADED_BILLS, DB_UPLOADED_FINDINGS
    DB_UPLOADED_BILLS = []
    DB_UPLOADED_FINDINGS = []
    return {"status": "success", "message": "Uploaded bills cleared. Demo bills remain."}


@app.get("/api/demo-bills")
def list_demo_bills():
    """List demo bills with their labels and expected findings count."""
    result = []
    for b in DEMO_BILLS:
        findings = [f for f in DEMO_FINDINGS if f.bill_id == b.bill_id]
        result.append({
            "bill_id": b.bill_id,
            "provider": b.provider,
            "total": b.total,
            "demo_label": getattr(b, "demo_label", "Demo Bill"),
            "demo_description": getattr(b, "demo_description", ""),
            "findings_count": len(findings),
            "high_findings": sum(1 for f in findings if f.priority == "HIGH"),
        })
    return result


@app.get("/api/health")
def health():
    use_mock = os.getenv("USE_MOCK_AWS", "true").lower() == "true"
    return {
        "status": "ok",
        "mode": "local_demo" if use_mock else "aws",
        "demo_bills": len(DEMO_BILLS),
        "uploaded_bills": len(DB_UPLOADED_BILLS),
    }
