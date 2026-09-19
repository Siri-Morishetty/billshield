"""
BillShield Deterministic Analysis Engine
Checks: line-item arithmetic, subtotal, total, duplicates.
No AI/LLM is used for calculations.
"""
from typing import List, Dict, Any
import uuid
from ..models.bill import Bill
from ..models.line_item import LineItem
from ..models.finding import Finding


class ValidationEngine:

    @staticmethod
    def validate_normalized_bill(bill: Bill) -> Dict[str, Any]:
        """Data quality validation before generating findings."""
        errors: List[str] = []
        warnings: List[str] = []

        if bill.total == 0 and bill.subtotal == 0:
            errors.append("Missing both total and subtotal amounts.")

        if not bill.line_items:
            warnings.append("No line items found — cannot verify arithmetic.")

        if not bill.provider or bill.provider.lower() in ("unknown provider", "unknown", ""):
            warnings.append("Provider could not be determined.")

        if not bill.currency:
            warnings.append("Currency is missing.")

        return {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
        }

    @staticmethod
    def validate(bill: Bill) -> List[Finding]:
        findings: List[Finding] = []

        # 0. Data quality gate
        dq = ValidationEngine.validate_normalized_bill(bill)
        if not dq["valid"]:
            bill.extraction_status = "incomplete: " + ", ".join(dq["errors"])
            return findings

        # ── Check 1: Individual line-item arithmetic (qty × unit_price = amount) ──
        for item in bill.line_items:
            if item.quantity > 0 and item.unit_price > 0:
                expected_line = round(item.quantity * item.unit_price, 2)
                if abs(expected_line - item.amount) > 0.02:
                    findings.append(Finding(
                        finding_id=str(uuid.uuid4()),
                        bill_id=bill.bill_id,
                        type="LINE_ITEM_MISMATCH",
                        priority="HIGH",
                        title=f"Line item arithmetic error: {item.description}",
                        description=(
                            f"For '{item.description}': qty {item.quantity} × "
                            f"unit price ₹{item.unit_price:,.2f} = ₹{expected_line:,.2f}, "
                            f"but bill shows ₹{item.amount:,.2f}."
                        ),
                        amount=abs(expected_line - item.amount),
                        evidence={
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "calculated": expected_line,
                            "reported": item.amount,
                            "difference": abs(expected_line - item.amount),
                        }
                    ))

        # ── Check 2: Sum of line items vs subtotal ──
        if bill.line_items:
            calculated_subtotal = round(sum(item.amount for item in bill.line_items), 2)
            if abs(calculated_subtotal - bill.subtotal) > 0.02:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="CALCULATION_DISCREPANCY",
                    priority="HIGH",
                    title="Subtotal does not match sum of line items",
                    description=(
                        f"Sum of all line items: ₹{calculated_subtotal:,.2f}. "
                        f"Bill shows subtotal: ₹{bill.subtotal:,.2f}. "
                        f"Difference: ₹{abs(calculated_subtotal - bill.subtotal):,.2f}."
                    ),
                    amount=abs(calculated_subtotal - bill.subtotal),
                    evidence={
                        "line_items": [
                            {"description": i.description, "amount": i.amount}
                            for i in bill.line_items
                        ],
                        "calculated_sum": calculated_subtotal,
                        "reported_subtotal": bill.subtotal,
                        "difference": abs(calculated_subtotal - bill.subtotal),
                    }
                ))

        # ── Check 3: Tax math (only if tax_rate is known) ──
        if bill.tax_rate > 0 and bill.taxable_amount > 0:
            calculated_tax = round(bill.taxable_amount * bill.tax_rate / 100, 2)
            if abs(calculated_tax - bill.tax) > 0.50:  # allow 50p rounding
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="TAX_MISMATCH",
                    priority="MEDIUM",
                    title="Tax amount could not be verified",
                    description=(
                        f"Taxable amount ₹{bill.taxable_amount:,.2f} × {bill.tax_rate:.0f}% "
                        f"= ₹{calculated_tax:,.2f}, but bill shows GST ₹{bill.tax:,.2f}. "
                        f"Difference: ₹{abs(calculated_tax - bill.tax):,.2f}."
                    ),
                    amount=abs(calculated_tax - bill.tax),
                    evidence={
                        "taxable_amount": bill.taxable_amount,
                        "tax_rate": bill.tax_rate,
                        "calculated_tax": calculated_tax,
                        "reported_tax": bill.tax,
                    }
                ))

        # ── Check 4: Overall total (subtotal - discount + fees + tax = total) ──
        expected_total = round(bill.subtotal - bill.discount + bill.fees + bill.tax, 2)
        if abs(expected_total - bill.total) > 0.02:
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                bill_id=bill.bill_id,
                type="TOTAL_MISMATCH",
                priority="HIGH",
                title="Total does not match calculated amount",
                description=(
                    f"Calculated: subtotal ₹{bill.subtotal:,.2f}"
                    + (f" − discount ₹{bill.discount:,.2f}" if bill.discount else "")
                    + (f" + fees ₹{bill.fees:,.2f}" if bill.fees else "")
                    + (f" + tax ₹{bill.tax:,.2f}" if bill.tax else "")
                    + f" = ₹{expected_total:,.2f}. "
                    f"Bill total: ₹{bill.total:,.2f}. "
                    f"Mismatch: ₹{abs(expected_total - bill.total):,.2f}."
                ),
                amount=abs(expected_total - bill.total),
                evidence={
                    "subtotal": bill.subtotal,
                    "discount": bill.discount,
                    "fees": bill.fees,
                    "tax": bill.tax,
                    "calculated_total": expected_total,
                    "reported_total": bill.total,
                    "difference": abs(expected_total - bill.total),
                }
            ))

        # ── Check 5: Duplicate line items ──
        seen: Dict[str, LineItem] = {}
        for item in bill.line_items:
            key = item.description.lower().strip()
            if key in seen:
                # Only flag if amounts also match (genuine duplicate, not a different charge)
                if abs(seen[key].amount - item.amount) < 0.02:
                    findings.append(Finding(
                        finding_id=str(uuid.uuid4()),
                        bill_id=bill.bill_id,
                        type="DUPLICATE_CHARGE",
                        priority="MEDIUM",
                        title=f"Possible duplicate charge: {item.description}",
                        description=(
                            f"'{item.description}' appears more than once on this bill "
                            f"with the same amount (₹{item.amount:,.2f}). "
                            f"This may be a duplicate entry."
                        ),
                        amount=item.amount,
                        evidence={
                            "description": item.description,
                            "amount": item.amount,
                            "occurrences": 2,
                        }
                    ))
            else:
                seen[key] = item

        return findings
