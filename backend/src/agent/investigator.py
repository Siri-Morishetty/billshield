from typing import List
from ..models.bill import Bill
from ..models.finding import Finding
from ..services.history_engine import HistoryEngine


class BillInvestigatorAgent:
    """
    Simulates the Strands Agent SDK behavior.
    All tool calls use REAL data from the backend — no hardcoded strings.
    """

    def investigate(self, current_bill: Bill, historical_bills: List[Bill], findings: List[Finding]) -> dict:
        print("[Agent] Investigation starting...")

        # Step 1 — get_bill()
        print(f"[Agent] get_bill({current_bill.bill_id})")

        # Step 2 — get_previous_bill()
        print(f"[Agent] get_previous_bill() -> {len(historical_bills)} found")

        # Step 3 — compare_bills()
        comparison = HistoryEngine.compare(current_bill, historical_bills)
        print(f"[Agent] compare_bills() -> {comparison}")

        # Step 4 — validate_bill() — findings already passed in
        validation_findings = [f for f in findings if f.type in ("CALCULATION_DISCREPANCY", "TOTAL_MISMATCH", "DUPLICATE_CHARGE")]
        print(f"[Agent] validate_bill() → {len(validation_findings)} validation findings")

        # Step 5 — find_anomalies()
        anomaly_findings = [f for f in findings if f.type in ("NEW_CHARGE", "UNUSUAL_INCREASE")]
        print(f"[Agent] find_anomalies() → {len(anomaly_findings)} anomalies")

        # Step 6 — get_evidence()
        evidence_list = []
        for f in findings:
            if f.type == "NEW_CHARGE":
                evidence = {
                    "evidence_id": f.finding_id,
                    "bill_id": current_bill.bill_id,
                    "type": f.type,
                    "title": f.title,
                    "source": f"Current bill ({current_bill.provider})",
                    "current_bill_text": f"{f.description}",
                    "historical_check": "Not present in any previous bill.",
                    "page": 1,
                    "amount": f.amount,
                }
            elif f.type == "UNUSUAL_INCREASE":
                evidence = {
                    "evidence_id": f.finding_id,
                    "bill_id": current_bill.bill_id,
                    "type": f.type,
                    "title": f.title,
                    "source": "Historical comparison",
                    "current_bill_text": f"Current total: ₹{current_bill.total:,.2f}",
                    "historical_check": f"Previous total: ₹{comparison.get('previous_total', 0):,.2f}",
                    "page": 1,
                    "amount": f.amount,
                }
            else:
                evidence = {
                    "evidence_id": f.finding_id,
                    "bill_id": current_bill.bill_id,
                    "type": f.type,
                    "title": f.title,
                    "source": "Validation engine",
                    "current_bill_text": f.description,
                    "historical_check": "N/A",
                    "page": 1,
                    "amount": f.amount,
                }
            evidence_list.append(evidence)
            print(f"[Agent] get_evidence({f.finding_id}) → {evidence['type']}")

        # Step 7 — generate_explanation()
        explanation = self._build_explanation(current_bill, historical_bills, findings, comparison)
        print("[Agent] Generated explanation.")

        # Step 8 — generate_questions()
        questions = self._generate_questions(findings)

        return {
            "summary": f"Found {len(findings)} item(s) worth reviewing.",
            "findings": [f.model_dump() for f in findings],
            "evidence": evidence_list,
            "questions": questions,
            "explanation": explanation,
            "comparison": comparison,
        }

    def _build_explanation(self, current_bill: Bill, historical_bills: List[Bill], findings: List[Finding], comparison: dict) -> str:
        """Build a structured, data-driven investigation explanation."""
        lines = ["### INVESTIGATION SUMMARY\n"]

        # Bill total summary
        prev_total = comparison.get("previous_total", 0)
        abs_diff = comparison.get("absolute_difference", 0)
        pct_diff = comparison.get("percentage_difference", 0)

        lines.append(f"**{current_bill.provider}** — {current_bill.bill_type.capitalize()} Bill")
        lines.append(f"- Current total: ₹{current_bill.total:,.2f}")
        if prev_total > 0:
            lines.append(f"- Previous total: ₹{prev_total:,.2f}")
            direction = "higher" if abs_diff > 0 else "lower"
            lines.append(f"- This bill is **₹{abs(abs_diff):,.2f} {direction}** than the previous bill ({abs(pct_diff):.2f}% {'increase' if abs_diff > 0 else 'decrease'}).")

        lines.append("")

        # Findings
        new_charges = [f for f in findings if f.type == "NEW_CHARGE"]
        if new_charges:
            lines.append("**New charges detected:**")
            for f in new_charges:
                lines.append(f"- **{f.description.strip(chr(39))}** — ₹{f.amount:,.2f}")
                lines.append(f"  - First appearance on this bill. Not present in previous bills.")
            lines.append("")

        unusual = [f for f in findings if f.type == "UNUSUAL_INCREASE"]
        if unusual:
            for f in unusual:
                lines.append(f"**{f.title}:** {f.description}")
            lines.append("")

        calc_issues = [f for f in findings if f.type in ("CALCULATION_DISCREPANCY", "TOTAL_MISMATCH")]
        if calc_issues:
            lines.append("**Calculation issues detected:**")
            for f in calc_issues:
                lines.append(f"- ⚠️ {f.description}")
            lines.append("")

        if not findings:
            lines.append("✅ No issues found. All calculations are mathematically consistent.")

        # Line item breakdown
        if current_bill.line_items:
            lines.append("**Line item breakdown:**")
            for item in current_bill.line_items:
                lines.append(f"- {item.description}: ₹{item.amount:,.2f}")
            lines.append(f"- **Subtotal: ₹{current_bill.subtotal:,.2f}**")
            if current_bill.discount > 0:
                lines.append(f"- Discount: -₹{current_bill.discount:,.2f}")
            if current_bill.tax > 0:
                lines.append(f"- GST ({current_bill.tax_rate:.0f}%): ₹{current_bill.tax:,.2f}")
            lines.append(f"- **Total: ₹{current_bill.total:,.2f}**")

        return "\n".join(lines)

    def _generate_questions(self, findings: List[Finding]) -> List[str]:
        """Generate evidence-based questions from findings."""
        questions = []
        for f in findings:
            if f.type == "NEW_CHARGE":
                desc = f.description.strip("'\"")
                # Extract item name from description like "'Premium Support' appeared for the first time"
                name_match = desc.split("'")[1] if "'" in desc else desc.split('"')[1] if '"' in desc else desc
                questions.append(f"When was '{name_match}' added to my plan, and what does the ₹{f.amount:,.2f} charge cover?")
                questions.append(f"Was I notified before '{name_match}' was added to my bill?")
                questions.append(f"Is '{name_match}' a recurring monthly charge?")
            elif f.type == "UNUSUAL_INCREASE":
                questions.append(f"Can you explain the {f.description.split('by')[-1].strip() if 'by' in f.description else 'significant'} increase in my bill?")
        return questions
