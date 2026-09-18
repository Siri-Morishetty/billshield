from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import os
import tempfile
import uuid
from datetime import datetime

from .models.bill import Bill
from .models.finding import Finding
from .models.line_item import LineItem
from .services.local_parser import LocalParser
from .services.validation_engine import ValidationEngine
from .services.anomaly_engine import AnomalyEngine
from .services.history_engine import HistoryEngine

app = FastAPI(title="BillShield Local Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _make_july_bill() -> Bill:
    """Create the July historical reference bill. Called on startup and on reset."""
    return Bill(
        bill_id="bill-jul-001",
        user_id="local-user",
        bill_type="internet",
        provider="ACME CONNECT INTERNET SERVICES",
        currency="INR",
        subtotal=1968.0,
        discount=0.0,
        taxable_amount=1968.0,
        tax_rate=0.0,
        tax=0.0,
        total=1968.0,
        line_items=[
            # July bill line items — used by anomaly engine for new-charge detection
            LineItem(description="Fiber Internet Plan - 200 Mbps", quantity=1, unit_price=1500.0, amount=1500.0, page=1, line_number=1),
            LineItem(description="Internet Usage", quantity=1, unit_price=318.0, amount=318.0, page=1, line_number=2),
            LineItem(description="Router Maintenance", quantity=1, unit_price=150.0, amount=150.0, page=1, line_number=3),
        ],
        extraction_status="completed"
    )


# ---- In-memory database ----
DB_BILLS: List[Bill] = [_make_july_bill()]
DB_FINDINGS: List[Finding] = []


# ---- API routes ----

@app.get("/api/bills")
def get_bills():
    return DB_BILLS


@app.get("/api/bills/{bill_id}")
def get_bill(bill_id: str):
    for b in DB_BILLS:
        if b.bill_id == bill_id:
            return b
    raise HTTPException(status_code=404, detail="Bill not found")


@app.get("/api/bills/{bill_id}/findings")
def get_findings(bill_id: str):
    return [f for f in DB_FINDINGS if f.bill_id == bill_id]


@app.post("/api/upload")
async def upload_bill(file: UploadFile = File(...)):
    # 1. Save uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    safe_filename = os.path.basename(file.filename or "upload.pdf")
    file_path = os.path.join(temp_dir, safe_filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # 2. Parse
    if safe_filename.lower().endswith('.pdf'):
        parsed_bill = LocalParser.parse_pdf(file_path, safe_filename)
    else:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # 3. Get historical bills for this provider for comparison
    historical_bills = [
        b for b in DB_BILLS
        if b.provider == parsed_bill.provider
    ]

    # 4. Validation (math checks — no false positives)
    validation_findings = ValidationEngine.validate(parsed_bill)

    # 5. Historical comparison
    history_comparison = HistoryEngine.compare(parsed_bill, historical_bills)

    # 6. Anomaly detection (new charges, unusual increases)
    anomaly_findings = AnomalyEngine.detect(parsed_bill, historical_bills, history_comparison)

    # 7. Combine all findings
    all_findings = validation_findings + anomaly_findings

    # 8. Save to DB — new bill goes to front
    DB_BILLS.insert(0, parsed_bill)
    DB_FINDINGS.extend(all_findings)

    return {
        "status": "success",
        "bill_id": parsed_bill.bill_id,
        "findings_count": len(all_findings),
        "subtotal": parsed_bill.subtotal,
        "tax": parsed_bill.tax,
        "total": parsed_bill.total,
        "line_items": len(parsed_bill.line_items),
    }


@app.get("/api/investigate/{bill_id}")
def investigate_bill(bill_id: str):
    from .agent.investigator import BillInvestigatorAgent

    current_bill = None
    for b in DB_BILLS:
        if b.bill_id == bill_id:
            current_bill = b
            break

    if not current_bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    historical_bills = [
        b for b in DB_BILLS
        if b.provider == current_bill.provider and b.bill_id != bill_id
    ]

    current_findings = [f for f in DB_FINDINGS if f.bill_id == bill_id]

    agent = BillInvestigatorAgent()
    return agent.investigate(current_bill, historical_bills, current_findings)


@app.post("/api/clear")
def clear_db():
    """Reset to initial state — keeps the July historical bill."""
    global DB_BILLS, DB_FINDINGS
    DB_BILLS = [_make_july_bill()]
    DB_FINDINGS = []
    return {"status": "success"}
