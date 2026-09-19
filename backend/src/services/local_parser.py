import os
import io
import re
import uuid
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any, Union
from datetime import datetime
import pdfplumber

from ..models.bill import Bill, BillingPeriod
from ..models.line_item import LineItem


def _parse_amount(s: Any) -> Optional[float]:
    """
    Parse a currency string to float safely.
    Handles: $85.00 / ₹2,249.00 / €120.50 / £45.00 / 1,000.00 / 85.00
    Does NOT confuse percentages (e.g. 0.00%) with monetary amounts.
    """
    if s is None:
        return None
    val_str = str(s).strip()
    if not val_str:
        return None
    if val_str.endswith('%'):
        return None
    # Strip leading/trailing currency symbols and common currency words
    cleaned = re.sub(r'^[₹\$€£\s:]+|^(?:Rs\.?|INR|USD|EUR|GBP|AUD|CAD)\s*', '', val_str, flags=re.IGNORECASE)
    cleaned = cleaned.replace(',', '').strip()
    m = re.search(r'[-+]?\d+(?:\.\d+)?', cleaned)
    if m:
        try:
            return float(m.group(0))
        except (ValueError, TypeError):
            return None
    return None


def _normalize_description(desc: str) -> str:
    """Lowercase + strip for comparison."""
    return re.sub(r'\s+', ' ', desc.lower().strip())


def _is_subtotal_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9]', ' ', str(label).lower())
    return bool(re.search(r'\b(sub\s*total|subtotal|sub-total|net\s*total|net\s*amount|amount\s*before\s*tax|taxable\s*amount|charges\s*subtotal)\b', norm))


def _is_tax_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9]', ' ', str(label).lower())
    return bool(re.search(r'\b(tax|sales\s*tax|gst|vat|cgst|sgst|igst)\b', norm))


def _is_total_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9]', ' ', str(label).lower())
    if _is_subtotal_label(label):
        return False
    return bool(re.search(r'\b(grand\s*total|total\s*due|amount\s*due|balance\s*due|total\s*amount|invoice\s*total|total)\b', norm))


def _is_discount_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9]', ' ', str(label).lower())
    return bool(re.search(r'\b(discount|adjust|adjustment|credit|less\s*discount)\b', norm))


def _is_fees_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9]', ' ', str(label).lower())
    return bool(re.search(r'\b(fee|fees|convenience\s*fee|service\s*fee|delivery\s*fee)\b', norm))


def _is_summary_row_label(label: str) -> bool:
    norm = re.sub(r'[^a-z0-9%]', ' ', str(label).lower())
    norm = re.sub(r'\s+', ' ', norm).strip()
    if not norm:
        return False
    if any(norm.startswith(p) for p in ['service ', 'plan ', 'router ', 'internet ']):
        return False
    if _is_subtotal_label(norm) or _is_total_label(norm) or _is_tax_label(norm) or _is_discount_label(norm) or _is_fees_label(norm):
        return True
    return bool(re.search(r'^(?:sub\s*total|subtotal|sub-total|net\s*total|net\s*amount|tax(?:\s*\d+(?:\.\d+)?%)?|sales\s*tax|state\s*tax|gst(?:\s*\d+%)?|vat(?:\s*\d+%)?|cgst|sgst|igst|grand\s*total|total\s*due|amount\s*due|balance\s*due|total\s*amount|total|discount|adjustment|adjust|credit|taxable\s*amount|fee|fees)$', norm))


def _detect_currency(text: str, tables: Optional[list] = None) -> str:
    """Detect currency from document text or tables."""
    if "₹" in text or re.search(r'\b(?:INR|Rs\.?|GST|CGST|SGST)\b', text, re.IGNORECASE):
        return "INR"
    if "€" in text or re.search(r'\bEUR\b', text):
        return "EUR"
    if "£" in text or re.search(r'\bGBP\b', text):
        return "GBP"
    if re.search(r'\bAUD\b|A\$', text):
        return "AUD"
    if re.search(r'\bCAD\b|C\$', text):
        return "CAD"
    if "$" in text or re.search(r'\bUSD\b', text):
        return "USD"

    for t in (tables or []):
        for row in t.get("rows", []):
            for cell in row:
                cs = str(cell or "")
                if "₹" in cs or re.search(r'\b(?:INR|Rs\.?|GST)\b', cs, re.IGNORECASE):
                    return "INR"
                if "€" in cs:
                    return "EUR"
                if "£" in cs:
                    return "GBP"
                if "$" in cs:
                    return "USD"

    # Default to USD for global invoices
    return "USD"


class LocalParser:
    """
    Robust, generalized document parser for invoices and utility bills.
    Dynamic column header mapping, robust summary extraction,
    currency preservation, and fallback text parsing.
    """

    @staticmethod
    def parse_pdf(file_input: Union[str, bytes, io.BytesIO], original_filename: str) -> Bill:
        all_tables = []
        full_text = ""
        page_count = 0
        try:
            fp = io.BytesIO(file_input) if isinstance(file_input, bytes) else file_input
            with pdfplumber.open(fp) as pdf:
                page_count = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages):
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            all_tables.append({
                                "page": page_num + 1,
                                "rows": table
                            })
        except Exception as e:
            print(f"[LocalParser] Error parsing PDF: {e}")

        print(f"[LocalParser] Extracted text length: {len(full_text)}")
        print(f"[LocalParser] Tables found: {len(all_tables)}")

        return LocalParser._build_bill(full_text, all_tables, original_filename, page_count)

    @staticmethod
    def _build_bill(text: str, tables: list, filename: str, page_count: int) -> Bill:
        provider = LocalParser._extract_provider(text)
        bill_type = "internet" if any(k in text.lower() for k in ["internet", "broadband", "fiber"]) else "invoice"
        currency = _detect_currency(text, tables)

        invoice_number = None
        issue_date = None
        due_date = None
        billing_period = None

        invoice_match = re.search(r'(?:Invoice\s*(?:No|Number|#)?|Inv\s*#?)\s*[:.]?\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
        if invoice_match:
            invoice_number = invoice_match.group(1).strip()

        period_match = re.search(
            r'Billing\s+Period\s+(\d{2}-\w{3}-\d{4})\s+to\s+(\d{2}-\w{3}-\d{4})',
            text, re.IGNORECASE
        )
        if period_match:
            try:
                start = datetime.strptime(period_match.group(1), "%d-%b-%Y").date()
                end = datetime.strptime(period_match.group(2), "%d-%b-%Y").date()
                billing_period = BillingPeriod(start_date=start, end_date=end)
            except Exception:
                pass

        issue_match = re.search(r'(?:Issue\s+Date|Date|Invoice\s+Date)\s*[:.]?\s*(\d{2}-\w{3}-\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if issue_match:
            raw_d = issue_match.group(1)
            for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
                try:
                    issue_date = datetime.strptime(raw_d, fmt).date()
                    break
                except Exception:
                    pass

        due_match = re.search(r'Due\s+Date\s*[:.]?\s*(\d{2}-\w{3}-\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})', text, re.IGNORECASE)
        if due_match:
            raw_d = due_match.group(1)
            for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
                try:
                    due_date = datetime.strptime(raw_d, fmt).date()
                    break
                except Exception:
                    pass

        # Summary values extracted explicitly from source document
        extracted_subtotal: Optional[float] = None
        extracted_tax: Optional[float] = None
        extracted_total: Optional[float] = None
        extracted_discount: Optional[float] = None
        extracted_fees: Optional[float] = None
        extracted_tax_rate: Optional[float] = None
        extracted_taxable_amount: Optional[float] = None

        line_items: List[LineItem] = []

        # ---- Process extracted tables ----
        for table_data in tables:
            rows = table_data.get("rows", [])
            page = table_data.get("page", 1)
            if not rows:
                continue

            # First, check each row in this table to see if it's a summary row (label + amount)
            for r_idx, row in enumerate(rows):
                if not row:
                    continue
                non_empty = [c for c in row if c is not None and str(c).strip() != ""]
                if len(non_empty) >= 2:
                    # Look for label cell and value cell
                    label_candidate = None
                    val_candidate = None
                    for cell in non_empty:
                        cs = str(cell).strip()
                        if _is_summary_row_label(cs) and label_candidate is None:
                            label_candidate = cs
                        else:
                            parsed_v = _parse_amount(cs)
                            if parsed_v is not None:
                                val_candidate = parsed_v

                    if label_candidate and val_candidate is not None:
                        if _is_subtotal_label(label_candidate) and extracted_subtotal is None:
                            extracted_subtotal = val_candidate
                        elif _is_tax_label(label_candidate) and extracted_tax is None:
                            extracted_tax = val_candidate
                            rate_m = re.search(r'\((\d+(?:\.\d+)?)%\)', label_candidate) or re.search(r'(\d+(?:\.\d+)?)%', label_candidate)
                            if rate_m:
                                extracted_tax_rate = float(rate_m.group(1))
                        elif _is_total_label(label_candidate) and extracted_total is None:
                            extracted_total = val_candidate
                        elif _is_discount_label(label_candidate) and extracted_discount is None:
                            extracted_discount = val_candidate
                        elif _is_fees_label(label_candidate) and extracted_fees is None:
                            extracted_fees = val_candidate

            # Second, detect if this table is a Line-Item table
            header = [str(c).lower().strip() if c else "" for c in rows[0]]
            has_amount_col = any("amount" in h or "sub total" in h or "line total" in h or "total" in h or "price" in h for h in header)
            has_desc_col = any("desc" in h or "item" in h or "service" in h or "charge" in h or "particulars" in h or "product" in h for h in header)

            if has_desc_col and has_amount_col:
                desc_idx = next((i for i, h in enumerate(header) if "desc" in h or "item" in h or "service" in h or "charge" in h or "particulars" in h or "product" in h), 0)
                qty_idx = next((i for i, h in enumerate(header) if "qty" in h or "quantity" in h or "hrs" in h or "hours" in h or "units" in h or "count" in h), -1)
                unit_price_idx = next((i for i, h in enumerate(header) if "rate" in h or "unit" in h), -1)
                adjust_idx = next((i for i, h in enumerate(header) if "adjust" in h or "discount" in h), -1)

                # Amount column: prefer sub total / line total / amount, else fallback to last price column
                amt_idx = next((i for i, h in enumerate(header) if "sub total" in h or "subtotal" in h or "line total" in h or h == "amount"), -1)
                if amt_idx == -1:
                    amt_idx = next((i for i, h in enumerate(header) if "amount" in h), -1)
                if amt_idx == -1:
                    # pick right-most column with total or price that isn't unit_price_idx
                    candidates = [i for i, h in enumerate(header) if ("total" in h or "price" in h) and i != unit_price_idx and i != desc_idx]
                    amt_idx = candidates[-1] if candidates else len(header) - 1

                for row in rows[1:]:
                    if not row or all(c is None or str(c).strip() == "" for c in row):
                        continue
                    desc_raw = str(row[desc_idx]).strip() if len(row) > desc_idx and row[desc_idx] else ""
                    # Check if this row is actually a summary row
                    is_sum = False
                    for cell in row:
                        if cell and _is_summary_row_label(str(cell)):
                            is_sum = True
                            break
                    if is_sum or not desc_raw:
                        continue

                    amt_raw = str(row[amt_idx]).strip() if len(row) > amt_idx and row[amt_idx] else ""
                    amt = _parse_amount(amt_raw)

                    unit_price = 0.0
                    if unit_price_idx >= 0 and len(row) > unit_price_idx and row[unit_price_idx]:
                        parsed_up = _parse_amount(str(row[unit_price_idx]).strip())
                        if parsed_up is not None:
                            unit_price = parsed_up

                    qty = 1.0
                    if qty_idx >= 0 and len(row) > qty_idx and row[qty_idx]:
                        try:
                            clean_q = re.sub(r'[^\d\.]', '', str(row[qty_idx]))
                            qty = float(clean_q) if clean_q else 1.0
                        except Exception:
                            qty = 1.0

                    adjust = None
                    if adjust_idx >= 0 and len(row) > adjust_idx and row[adjust_idx]:
                        adjust_str = str(row[adjust_idx]).strip()
                        adjust = _parse_amount(adjust_str)

                    # Deduce amount or unit_price if one was missing
                    if amt is None and unit_price > 0:
                        amt = round(qty * unit_price, 2)
                    elif amt is not None and unit_price == 0.0 and qty > 0:
                        unit_price = round(amt / qty, 2)

                    if amt is not None:
                        line_items.append(LineItem(
                            description=desc_raw,
                            quantity=qty,
                            unit_price=unit_price,
                            amount=amt,
                            adjustment=adjust,
                            page=page,
                            line_number=rows.index(row)
                        ))

        # ---- Fallback from Raw Text if missing ----
        if extracted_subtotal is None:
            m = re.search(r'(?:sub[ \t]*total|sub-total|net[ \t]*total|net[ \t]*amount)[ \t]*[:\-]?[ \t]*([\$₹€£]?[ \t]*[\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
            if m:
                extracted_subtotal = _parse_amount(m.group(1))

        if extracted_tax is None:
            m = re.search(r'(?:sales[ \t]*tax|tax|gst|vat)[ \t]*(?:\([^\)]+\))?[ \t]*[:\-]?[ \t]*([\$₹€£]?[ \t]*[\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
            if m:
                extracted_tax = _parse_amount(m.group(1))

        if extracted_total is None:
            m = re.search(r'(?<!sub[ \t])(?<!sub-)(?<!net[ \t])(?:grand[ \t]*total|total[ \t]*due|amount[ \t]*due|balance[ \t]*due|total)[ \t]*[:\-]?[ \t]*([\$₹€£]?[ \t]*[\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
            if m:
                extracted_total = _parse_amount(m.group(1))

        if extracted_discount is None:
            m = re.search(r'(?:discount|adjustment|adjust)[ \t]*[:\-]?[ \t]*([\$₹€£]?[ \t]*[\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
            if m:
                extracted_discount = _parse_amount(m.group(1))

        if extracted_tax_rate is None:
            m = re.search(r'(?:tax|gst|vat)\s*(?:\@|\()?(\d+(?:\.\d+)?)%\)?', text, re.IGNORECASE)
            if m:
                extracted_tax_rate = float(m.group(1))

        # ---- Fallback Line Items from Text (e.g. "1.00 Web Design $85.00 0.00% $85.00") ----
        if not line_items:
            for line in text.split('\n'):
                line_str = line.strip()
                if not line_str or _is_summary_row_label(line_str):
                    continue
                # Match: QTY + DESCRIPTION + UNIT_PRICE (+ OPTIONAL ADJUST) + AMOUNT
                m = re.match(
                    r'^(\d+(?:\.\d+)?)\s+([A-Za-z][A-Za-z0-9\s\-_/&]+?)\s+([\$₹€£]?\s*[\d,]+(?:\.\d{2})?)\s+(?:([\d\.]+%?)\s+)?([\$₹€£]?\s*[\d,]+(?:\.\d{2})?)$',
                    line_str
                )
                if m:
                    q = float(m.group(1))
                    d = m.group(2).strip()
                    up = _parse_amount(m.group(3)) or 0.0
                    adj = _parse_amount(m.group(4)) if m.group(4) else None
                    am = _parse_amount(m.group(5))
                    if am is not None:
                        line_items.append(LineItem(
                            description=d,
                            quantity=q,
                            unit_price=up,
                            amount=am,
                            adjustment=adj,
                            page=1,
                            line_number=len(line_items) + 1
                        ))

        # Calculated values
        calculated_subtotal = round(sum(i.amount for i in line_items), 2) if line_items else None

        # Determine reported vs calculated
        # Explicit totals take precedence for reported values
        reported_subtotal = extracted_subtotal
        reported_tax = extracted_tax
        reported_total = extracted_total
        reported_discount = extracted_discount if extracted_discount is not None else 0.0
        reported_fees = extracted_fees if extracted_fees is not None else 0.0

        # Subtotal: if reported is available, use it; otherwise fallback to sum of line items if available
        final_subtotal = reported_subtotal if reported_subtotal is not None else calculated_subtotal

        # Taxable amount
        taxable_amount = extracted_taxable_amount
        if taxable_amount is None and final_subtotal is not None:
            taxable_amount = round(final_subtotal - reported_discount, 2)

        # Expected total for verification
        expected_total = None
        if final_subtotal is not None:
            expected_total = round(final_subtotal - reported_discount + reported_fees + (reported_tax or 0.0), 2)

        final_total = reported_total if reported_total is not None else expected_total

        bill_id = f"bill-{uuid.uuid4().hex[:8]}"

        print(f"[LocalParser] Parsed: provider={provider}, currency={currency}, subtotal={final_subtotal}, tax={reported_tax}, total={final_total}, line_items={len(line_items)}")

        return Bill(
            bill_id=bill_id,
            user_id="local-user",
            bill_type=bill_type,
            provider=provider,
            billing_period=billing_period,
            issue_date=issue_date,
            due_date=due_date,
            invoice_number=invoice_number,
            currency=currency,
            subtotal=final_subtotal,
            discount=reported_discount,
            taxable_amount=taxable_amount,
            tax_rate=extracted_tax_rate,
            tax=reported_tax,
            fees=reported_fees,
            total=final_total,
            line_items=line_items,
            source_document={
                "s3_key": filename,
                "page_count": page_count
            },
            extraction_status="completed",
            reported={
                "subtotal": reported_subtotal,
                "tax": reported_tax,
                "total": reported_total,
                "discount": reported_discount,
                "fees": reported_fees,
            },
            calculated={
                "subtotal": calculated_subtotal,
                "total": expected_total,
            },
            validation_status={}
        )

    @staticmethod
    def _extract_provider(text: str) -> str:
        """Best-effort provider extraction from bill text."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        skip_kw = [
            'shield', 'sample', 'note', 'testing', 'expected', 'invoice',
            'inv-', 'hrs/qty', 'sub total', 'subtotal', 'rate/price',
            'due date', 'issue date', 'billing period', 'page ', 'charges',
            'particulars', 'customer id', 'unit price'
        ]
        for line in lines:
            lower = line.lower()
            if any(k in lower for k in skip_kw):
                continue
            if len(line) > 2:
                return line
        return lines[0] if lines else "Unknown Provider"
