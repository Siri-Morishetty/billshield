from typing import List, Dict, Any
import uuid
from ..models.bill import Bill
from ..models.finding import Finding

class ValidationEngine:
    @staticmethod
    def validate_normalized_bill(bill: Bill) -> Dict[str, Any]:
        """Data quality validation before generating findings."""
        errors = []
        warnings = []
        
        if bill.total == 0 and bill.subtotal == 0:
            errors.append("Missing both total and subtotal amounts.")
        
        if not bill.line_items:
            errors.append("No line items found.")
            
        if not bill.provider or bill.provider == "Unknown Provider":
            errors.append("Provider is unknown.")
            
        if not bill.currency:
            errors.append("Currency is missing.")
            
        return {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors
        }

    @staticmethod
    def validate(bill: Bill) -> List[Finding]:
        findings = []
        
        # 0. Data Quality Check
        dq = ValidationEngine.validate_normalized_bill(bill)
        if not dq["valid"]:
            bill.extraction_status = "incomplete: " + ", ".join(dq["errors"])
            return findings # Do not run further anomalies on incomplete data
            
        # Check 1: Arithmetic (Sum of line items vs subtotal)
        calculated_subtotal = sum(item.amount for item in bill.line_items)
        if abs(calculated_subtotal - bill.subtotal) > 0.02: # small tolerance
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                bill_id=bill.bill_id,
                type="CALCULATION_DISCREPANCY",
                priority="HIGH",
                title="Calculation discrepancy",
                description=f"Sum of line items ({calculated_subtotal}) does not match subtotal ({bill.subtotal}).",
                amount=abs(calculated_subtotal - bill.subtotal)
            ))
            
        # Check 2: Duplicate line items
        descriptions = {}
        for item in bill.line_items:
            desc = item.description.lower().strip()
            if desc in descriptions:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=bill.bill_id,
                    type="DUPLICATE_CHARGE",
                    priority="MEDIUM",
                    title="Possible duplicate charge",
                    description=f"The item '{item.description}' appears multiple times.",
                    amount=item.amount
                ))
            descriptions[desc] = True
            
        # Check 3: Overall total validation (subtotal - discount + fees + tax = total)
        expected_total = bill.subtotal - bill.discount + bill.fees + bill.tax
        if abs(expected_total - bill.total) > 0.02:
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                bill_id=bill.bill_id,
                type="TOTAL_MISMATCH",
                priority="HIGH",
                title="Total discrepancy",
                description=f"Subtotal ({bill.subtotal}) - Discount ({bill.discount}) + Fees ({bill.fees}) + Tax ({bill.tax}) does not equal Total ({bill.total}).",
                amount=abs(expected_total - bill.total)
            ))

        return findings
