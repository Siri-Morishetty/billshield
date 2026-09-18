# Mock definitions for Agent Tools
# In a real scenario using Strands Agents SDK, these would be decorated tool functions.

def get_bill(bill_id: str):
    """Retrieve the normalized bill data for a given bill ID."""
    return {"bill_id": bill_id, "status": "retrieved"}

def get_previous_bill(user_id: str, provider: str):
    """Retrieve the previous bill for comparison."""
    return {"status": "retrieved"}

def compare_bills(current_bill_id: str):
    """Compare the current bill with historical bills."""
    return {
        "total_change": 1420,
        "percentage_change": 26.2,
        "new_items": ["Premium Support", "New Service Fee"],
        "removed_items": [],
        "changed_items": ["Usage"]
    }

def validate_bill(bill_id: str):
    """Run deterministic mathematical validation on a bill."""
    return [{"type": "CALCULATION_DISCREPANCY", "amount": 1000}]

def find_anomalies(bill_id: str):
    """Run statistical anomaly detection on a bill."""
    return [{"type": "NEW_CHARGE", "amount": 299}]

def get_evidence(finding_id: str):
    """Retrieve structured evidence supporting a finding."""
    return {"page": 2, "line": 14, "text": "Premium Support ₹299"}

def generate_questions(evidence_id: str):
    """Generate clarifying questions based on evidence."""
    return ["What is this charge for?"]
