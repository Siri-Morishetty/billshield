from typing import List, Dict, Any
from ..models.bill import Bill

class HistoryEngine:
    @staticmethod
    def compare(current_bill: Bill, historical_bills: List[Bill]) -> Dict[str, Any]:
        current_total = current_bill.total if current_bill.total is not None else 0.0
        if not historical_bills:
            return {
                "previous_total": 0,
                "current_total": current_total,
                "absolute_difference": 0,
                "percentage_difference": 0,
                "average": 0,
                "minimum": 0,
                "maximum": 0
            }
            
        totals = [b.total for b in historical_bills if b.total is not None] or [0.0]
        previous_bill = historical_bills[-1]
        
        previous_total = previous_bill.total if previous_bill.total is not None else 0.0
        absolute_difference = current_total - previous_total
        
        percentage_difference = 0
        if previous_total > 0:
            percentage_difference = (absolute_difference / previous_total) * 100
            
        average = sum(totals) / len(totals)
        
        return {
            "previous_total": previous_total,
            "current_total": current_total,
            "absolute_difference": absolute_difference,
            "percentage_difference": percentage_difference,
            "average": average,
            "minimum": min(totals),
            "maximum": max(totals)
        }
