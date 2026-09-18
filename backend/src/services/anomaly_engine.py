from typing import List
import uuid
from ..models.bill import Bill
from ..models.finding import Finding

class AnomalyEngine:
    @staticmethod
    def detect(current_bill: Bill, historical_bills: List[Bill], history_comparison: dict) -> List[Finding]:
        findings = []
        
        if not historical_bills:
            return findings
            
        # 1. Significant total increase
        pct_diff = history_comparison.get("percentage_difference", 0)
        if pct_diff > 15: # 15% threshold
            findings.append(Finding(
                finding_id=str(uuid.uuid4()),
                bill_id=current_bill.bill_id,
                type="UNUSUAL_INCREASE",
                priority="LOW" if pct_diff < 40 else "MEDIUM",
                title="Significant bill increase",
                description=f"Bill total increased by {pct_diff:.2f}% compared to the previous bill.",
                amount=history_comparison.get("absolute_difference", 0)
            ))
            
        # 2. New charge detection
        historical_items = set()
        for hb in historical_bills:
            for item in hb.line_items:
                historical_items.add(item.description.lower().strip())
                
        for item in current_bill.line_items:
            # normalize the string
            norm_desc = item.description.lower().strip()
            if norm_desc not in historical_items:
                findings.append(Finding(
                    finding_id=str(uuid.uuid4()),
                    bill_id=current_bill.bill_id,
                    type="NEW_CHARGE",
                    priority="MEDIUM",
                    title="New charge detected",
                    description=f"'{item.description}' appeared for the first time on the current bill.",
                    amount=item.amount
                ))
                
        return findings
