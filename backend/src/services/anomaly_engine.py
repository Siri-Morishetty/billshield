"""
BillShield Anomaly Engine
Checks: new charges, price changes, quantity changes, unusual total increase.
All calculations are deterministic — no AI/LLM.
"""
from typing import List, Dict, Any
import uuid
from ..models.bill import Bill
from ..models.finding import Finding


def _normalize(s: str) -> str:
    return s.lower().strip()


def _curr_sym(currency: Any) -> str:
    c = str(currency or "USD").upper()
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


class AnomalyEngine:

    @staticmethod
    def detect(current_bill: Bill, historical_bills: List[Bill], history_comparison: Dict[str, Any]) -> List[Finding]:
        if not historical_bills:
            return []

        findings: List[Finding] = []
        previous_bill = historical_bills[-1]  # most recent past bill
        sym = _curr_sym(current_bill.currency)

        # Build historical item lookup: normalized_description -> item
        hist_items: Dict[str, Any] = {}
        for hb in historical_bills:
            for item in hb.line_items:
                key = _normalize(item.description)
                # Keep the most recent occurrence
                if key not in hist_items:
                    hist_items[key] = {"item": item, "bill": hb}

        # ── A: New charges ──
        for item in current_bill.line_items:
            key = _normalize(item.description)
            if key not in hist_items:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=current_bill.bill_id,
                    type="NEW_CHARGE",
                    priority="MEDIUM",
                    title=f"New charge: {item.description}",
                    description=(
                        f"'{item.description}' ({sym}{item.amount:,.2f}) "
                        f"appears for the first time. "
                        f"Not present on any previous {current_bill.provider} bill."
                    ),
                    amount=item.amount,
                    evidence={
                        "description": item.description,
                        "amount": item.amount,
                        "previous_bills_checked": len(historical_bills),
                        "first_appearance": True,
                    }
                ))

        # ── B: Price changes and quantity changes for recurring items ──
        for item in current_bill.line_items:
            key = _normalize(item.description)
            if key not in hist_items:
                continue  # already flagged as new charge

            hist = hist_items[key]
            hist_item = hist["item"]
            hist_bill = hist["bill"]

            # Price change
            if abs(item.unit_price - hist_item.unit_price) > 0.02 and hist_item.unit_price > 0:
                price_diff = item.unit_price - hist_item.unit_price
                pct = (price_diff / hist_item.unit_price) * 100  # calculated by code, not LLM
                finding_type = "PRICE_INCREASE" if price_diff > 0 else "PRICE_DECREASE"
                priority = "HIGH" if abs(pct) >= 20 else "MEDIUM"
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=current_bill.bill_id,
                    type=finding_type,
                    priority=priority,
                    title=f"Price {'increase' if price_diff > 0 else 'decrease'}: {item.description}",
                    description=(
                        f"'{item.description}' price changed from "
                        f"{sym}{hist_item.unit_price:,.2f} to {sym}{item.unit_price:,.2f} "
                        f"({'↑' if price_diff > 0 else '↓'}{sym}{abs(price_diff):,.2f}, "
                        f"{abs(pct):.1f}% {'increase' if price_diff > 0 else 'decrease'})."
                    ),
                    amount=abs(price_diff),
                    evidence={
                        "description": item.description,
                        "previous_price": hist_item.unit_price,
                        "current_price": item.unit_price,
                        "difference": price_diff,
                        "percentage_change": round(pct, 2),
                        "previous_bill_id": hist_bill.bill_id,
                    }
                ))

            # Quantity change
            if abs(item.quantity - hist_item.quantity) > 0.01 and hist_item.quantity > 0:
                qty_diff = item.quantity - hist_item.quantity
                pct_qty = (qty_diff / hist_item.quantity) * 100
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=current_bill.bill_id,
                    type="QUANTITY_CHANGE",
                    priority="LOW",
                    title=f"Quantity change: {item.description}",
                    description=(
                        f"'{item.description}' quantity changed from "
                        f"{hist_item.quantity} to {item.quantity} "
                        f"({'↑' if qty_diff > 0 else '↓'}{abs(qty_diff):.1f} units, "
                        f"{abs(pct_qty):.1f}% change)."
                    ),
                    amount=abs(item.amount - hist_item.amount),
                    evidence={
                        "description": item.description,
                        "previous_quantity": hist_item.quantity,
                        "current_quantity": item.quantity,
                        "quantity_difference": qty_diff,
                        "percentage_change": round(pct_qty, 2),
                    }
                ))

        # ── C: Significant overall total increase ──
        pct_diff = history_comparison.get("percentage_difference", 0)
        abs_diff = history_comparison.get("absolute_difference", 0)
        current_total = current_bill.total if current_bill.total is not None else 0.0
        prev_total = history_comparison.get("previous_total", 0)

        if pct_diff > 20 and abs_diff > 0:
            already_flagged_amount = sum(
                f.amount or 0 for f in findings
                if f.type in ("NEW_CHARGE", "PRICE_INCREASE")
            )
            unexplained = abs_diff - already_flagged_amount
            if unexplained > 50:
                priority = "HIGH" if pct_diff > 40 else "MEDIUM"
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=current_bill.bill_id,
                    type="UNUSUAL_INCREASE",
                    priority=priority,
                    title=f"Significant bill increase ({abs(pct_diff):.1f}%)",
                    description=(
                        f"Bill total increased by {sym}{abs_diff:,.2f} "
                        f"({abs(pct_diff):.1f}%) compared to previous bill "
                        f"({sym}{prev_total:,.2f} → "
                        f"{sym}{current_total:,.2f}). "
                        f"{sym}{unexplained:,.2f} of this increase is not yet explained by "
                        f"detected new charges or price changes."
                    ),
                    amount=abs_diff,
                    evidence={
                        "previous_total": prev_total,
                        "current_total": current_total,
                        "absolute_difference": abs_diff,
                        "percentage_difference": round(pct_diff, 2),
                        "unexplained_amount": round(unexplained, 2),
                    }
                ))

        return findings
