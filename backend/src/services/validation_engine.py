"""
BillShield Deterministic Analysis Engine
Checks: line-item arithmetic, subtotal, total, duplicates.
No AI/LLM is used for calculations.
"""
from typing import List, Dict, Any, Optional
import uuid
from ..models.bill import Bill
from ..models.line_item import LineItem
from ..models.finding import Finding


def _curr_sym(currency: Optional[str]) -> str:
    """Return symbol for currency string."""
    c = (currency or "USD").upper()
    if c == "USD":
        return "$"
    elif c == "INR":
        return "₹"
    elif c == "EUR":
        return "€"
    elif c == "GBP":
        return "£"
    elif c == "AUD":
        return "A$"
    elif c == "CAD":
        return "C$"
    return f"{c} "


class ValidationEngine:

    @staticmethod
    def validate_normalized_bill(bill: Bill) -> Dict[str, Any]:
        """Data quality validation before generating findings."""
        errors: List[str] = []
        warnings: List[str] = []

        if bill.total is None and bill.subtotal is None and not bill.line_items:
            errors.append("Missing total, subtotal, and line item amounts.")

        if not bill.line_items:
            warnings.append("No line items found — cannot verify line-item arithmetic.")

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
        sym = _curr_sym(bill.currency)
        if bill.validation_status is None:
            bill.validation_status = {}

        # 0. Data quality gate
        dq = ValidationEngine.validate_normalized_bill(bill)
        if not dq["valid"]:
            bill.extraction_status = "incomplete: " + ", ".join(dq["errors"])
            return findings

        # ── Check 1: Individual line-item arithmetic (qty × unit_price = amount) ──
        items_with_math = [i for i in bill.line_items if i.quantity > 0 and i.unit_price > 0]
        has_line_math_error = False
        for item in items_with_math:
            expected_line = round(item.quantity * item.unit_price, 2)
            diff = abs(expected_line - item.amount)
            if diff > 0.02:
                has_line_math_error = True
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="LINE_ITEM_MISMATCH",
                    priority="HIGH",
                    title=f"Line item arithmetic error: {item.description}",
                    description=(
                        f"For '{item.description}': qty {item.quantity} × "
                        f"unit price {sym}{item.unit_price:,.2f} = {sym}{expected_line:,.2f}, "
                        f"but bill shows {sym}{item.amount:,.2f}."
                    ),
                    amount=diff,
                    evidence={
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "calculated": expected_line,
                        "reported": item.amount,
                        "difference": diff,
                        "currency": bill.currency,
                    }
                ))
        if items_with_math:
            bill.validation_status["line_items_arithmetic"] = "FAIL" if has_line_math_error else "PASS"
        else:
            bill.validation_status["line_items_arithmetic"] = "SKIPPED"

        # ── Check 2: Sum of line items vs subtotal ──
        if bill.line_items and bill.subtotal is not None:
            calculated_subtotal = round(sum(item.amount for item in bill.line_items), 2)
            diff = abs(calculated_subtotal - bill.subtotal)
            if diff > 0.02:
                bill.validation_status["subtotal_matches_items"] = "FAIL"
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="CALCULATION_DISCREPANCY",
                    priority="HIGH",
                    title="Subtotal does not match sum of line items",
                    description=(
                        f"Sum of all line items: {sym}{calculated_subtotal:,.2f}. "
                        f"Bill shows subtotal: {sym}{bill.subtotal:,.2f}. "
                        f"Difference: {sym}{diff:,.2f}."
                    ),
                    amount=diff,
                    evidence={
                        "line_items": [
                            {"description": i.description, "amount": i.amount}
                            for i in bill.line_items
                        ],
                        "calculated_sum": calculated_subtotal,
                        "reported_subtotal": bill.subtotal,
                        "difference": diff,
                        "currency": bill.currency,
                    }
                ))
            else:
                bill.validation_status["subtotal_matches_items"] = "PASS"
        else:
            bill.validation_status["subtotal_matches_items"] = "SKIPPED"

        # ── Check 3: Tax math (only if tax_rate and taxable_amount are known) ──
        if (bill.tax_rate is not None and bill.tax_rate > 0 and
            bill.taxable_amount is not None and bill.taxable_amount > 0 and
            bill.tax is not None):
            calculated_tax = round(bill.taxable_amount * bill.tax_rate / 100, 2)
            diff = abs(calculated_tax - bill.tax)
            if diff > 0.50:  # allow rounding tolerance
                bill.validation_status["tax_calculation"] = "FAIL"
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="TAX_MISMATCH",
                    priority="MEDIUM",
                    title="Tax amount could not be verified",
                    description=(
                        f"Taxable amount {sym}{bill.taxable_amount:,.2f} × {bill.tax_rate:.0f}% "
                        f"= {sym}{calculated_tax:,.2f}, but bill shows tax {sym}{bill.tax:,.2f}. "
                        f"Difference: {sym}{diff:,.2f}."
                    ),
                    amount=diff,
                    evidence={
                        "taxable_amount": bill.taxable_amount,
                        "tax_rate": bill.tax_rate,
                        "calculated_tax": calculated_tax,
                        "reported_tax": bill.tax,
                        "currency": bill.currency,
                    }
                ))
            else:
                bill.validation_status["tax_calculation"] = "PASS"
        else:
            bill.validation_status["tax_calculation"] = "SKIPPED"

        # ── Check 4: Overall total (subtotal - discount + fees + tax = total) ──
        # Determine base subtotal: explicit reported subtotal, or sum of line items if subtotal was unextracted
        subtotal_for_total = bill.subtotal
        if subtotal_for_total is None and bill.line_items:
            subtotal_for_total = round(sum(i.amount for i in bill.line_items), 2)

        if bill.total is not None and subtotal_for_total is not None:
            discount_val = bill.discount if bill.discount is not None else 0.0
            fees_val = bill.fees if bill.fees is not None else 0.0
            tax_val = bill.tax if bill.tax is not None else 0.0
            expected_total = round(subtotal_for_total - discount_val + fees_val + tax_val, 2)
            diff = abs(expected_total - bill.total)

            if diff > 0.02:
                bill.validation_status["total_calculation"] = "FAIL"
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="TOTAL_MISMATCH",
                    priority="HIGH",
                    title="Total does not match calculated amount",
                    description=(
                        f"Calculated: subtotal {sym}{subtotal_for_total:,.2f}"
                        + (f" − discount {sym}{discount_val:,.2f}" if discount_val else "")
                        + (f" + fees {sym}{fees_val:,.2f}" if fees_val else "")
                        + (f" + tax {sym}{tax_val:,.2f}" if tax_val else "")
                        + f" = {sym}{expected_total:,.2f}. "
                        f"Bill total: {sym}{bill.total:,.2f}. "
                        f"Mismatch: {sym}{diff:,.2f}."
                    ),
                    amount=diff,
                    evidence={
                        "subtotal": subtotal_for_total,
                        "discount": discount_val,
                        "fees": fees_val,
                        "tax": tax_val,
                        "calculated_total": expected_total,
                        "reported_total": bill.total,
                        "difference": diff,
                        "currency": bill.currency,
                    }
                ))
            else:
                bill.validation_status["total_calculation"] = "PASS"
        else:
            bill.validation_status["total_calculation"] = "UNKNOWN"

        # ── Check 5: Duplicate line items ──
        seen: Dict[str, LineItem] = {}
        for item in bill.line_items:
            key = item.description.lower().strip()
            if key in seen:
                if abs(seen[key].amount - item.amount) < 0.02:
                    findings.append(Finding(
                        finding_id=str(uuid.uuid4()),
                        bill_id=bill.bill_id,
                        type="DUPLICATE_CHARGE",
                        priority="MEDIUM",
                        title=f"Possible duplicate charge: {item.description}",
                        description=(
                            f"'{item.description}' appears more than once on this bill "
                            f"with the same amount ({sym}{item.amount:,.2f}). "
                            f"This may be a duplicate entry."
                        ),
                        amount=item.amount,
                        evidence={
                            "description": item.description,
                            "amount": item.amount,
                            "occurrences": 2,
                            "currency": bill.currency,
                        }
                    ))
            else:
                seen[key] = item

        return findings
