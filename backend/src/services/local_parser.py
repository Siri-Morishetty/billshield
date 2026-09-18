import os
import re
import pdfplumber
import uuid
from typing import List, Optional, Tuple
from datetime import datetime
from ..models.bill import Bill, BillingPeriod
from ..models.line_item import LineItem


def _parse_amount(s: str) -> Optional[float]:
    """Parse a currency string to float. Handles: n1,000.00 / ₹1,000.00 / 1000.00 / 1,000"""
    if not s:
        return None
    # Strip any leading currency symbols (₹, Rs, INR, n, $, €, £) and whitespace
    cleaned = re.sub(r'^[₹Rs\.INRn\$€£\s]+', '', str(s).strip())
    # Remove commas
    cleaned = cleaned.replace(',', '').strip()
    try:
        val = float(cleaned)
        return val
    except (ValueError, TypeError):
        return None


def _normalize_description(desc: str) -> str:
    """Lowercase + strip for comparison."""
    return re.sub(r'\s+', ' ', desc.lower().strip())


class LocalParser:
    """
    Robust local PDF parser that uses pdfplumber table extraction
    to parse structured bill data. Works with any currency encoding
    (₹, Rs, n, $) and any table layout.
    
    In production this would be replaced by AWS Textract, but the
    normalized Bill schema is identical in both modes.
    """

    @staticmethod
    def parse_pdf(file_path: str, original_filename: str) -> Bill:
        all_tables = []
        full_text = ""
        page_count = 0
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages):
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            # tag each row with page number
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
        """
        Build a normalized Bill object from raw text + tables.
        Priority: table data > text data.
        """
        # ---- 1. Metadata from text ----
        provider = LocalParser._extract_provider(text)
        bill_type = "internet" if any(k in text.lower() for k in ["internet", "broadband", "fiber"]) else "utility"
        invoice_number = None
        customer_id = None
        issue_date = None
        due_date = None
        billing_period = None
        invoice_match = re.search(r'Invoice\s*(?:No|Number|#)?[:.]?\s*(\S+)', text, re.IGNORECASE)
        if invoice_match:
            invoice_number = invoice_match.group(1).strip()

        # Billing period
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

        # Issue / Due dates
        issue_match = re.search(r'Issue\s+Date\s+(\d{2}-\w{3}-\d{4})', text, re.IGNORECASE)
        if issue_match:
            try:
                issue_date = datetime.strptime(issue_match.group(1), "%d-%b-%Y").date()
            except Exception:
                pass

        due_match = re.search(r'Due\s+Date\s+(\d{2}-\w{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            try:
                due_date = datetime.strptime(due_match.group(1), "%d-%b-%Y").date()
            except Exception:
                pass

        # ---- 2. Line items from tables ----
        line_items: List[LineItem] = []
        subtotal = 0.0
        discount = 0.0
        taxable_amount = 0.0
        tax_rate = 0.0
        tax = 0.0
        total = 0.0

        # CHARGES_SKIP_KEYWORDS — rows that are NOT line items
        SUMMARY_KEYWORDS = {
            "subtotal", "discount", "taxable amount", "gst", "total due",
            "total", "vat", "cgst", "sgst", "tax", "balance due"
        }

        for table_data in tables:
            rows = table_data["rows"]
            page = table_data["page"]
            if not rows:
                continue

            # Detect header row
            header = [str(c).lower().strip() if c else "" for c in rows[0]]
            has_amount_col = any("amount" in h or "price" in h for h in header)
            has_desc_col = any("desc" in h or "item" in h or "service" in h or "charge" in h for h in header)

            # --- CHARGES TABLE ---
            if has_desc_col and has_amount_col:
                desc_idx = next((i for i, h in enumerate(header) if "desc" in h or "item" in h or "service" in h or "charge" in h), 0)
                amt_idx = next((i for i, h in enumerate(header) if h == "amount"), -1)
                if amt_idx == -1:
                    amt_idx = next((i for i, h in enumerate(header) if "amount" in h or "price" in h), len(header) - 1)
                qty_idx = next((i for i, h in enumerate(header) if "qty" in h or "quantity" in h), -1)
                unit_price_idx = next((i for i, h in enumerate(header) if "unit" in h), -1)

                for row in rows[1:]:  # skip header
                    if not row or all(c is None or str(c).strip() == "" for c in row):
                        continue
                    desc_raw = str(row[desc_idx]).strip() if row[desc_idx] else ""
                    if not desc_raw or _normalize_description(desc_raw) in SUMMARY_KEYWORDS:
                        continue
                    # Check if this row is a summary row
                    is_summary = any(kw in _normalize_description(desc_raw) for kw in SUMMARY_KEYWORDS)
                    if is_summary:
                        continue

                    amt_raw = str(row[amt_idx]).strip() if len(row) > amt_idx and row[amt_idx] else ""
                    amt = _parse_amount(amt_raw)
                    if amt is None:
                        continue

                    qty = 1.0
                    unit_price = amt
                    if qty_idx >= 0 and len(row) > qty_idx and row[qty_idx]:
                        try:
                            qty = float(str(row[qty_idx]).strip())
                        except Exception:
                            qty = 1.0
                    if unit_price_idx >= 0 and len(row) > unit_price_idx and row[unit_price_idx]:
                        parsed_up = _parse_amount(str(row[unit_price_idx]).strip())
                        if parsed_up is not None:
                            unit_price = parsed_up

                    line_items.append(LineItem(
                        description=desc_raw,
                        quantity=qty,
                        unit_price=unit_price,
                        amount=amt,
                        page=page,
                        line_number=rows.index(row)
                    ))
                continue

            # --- SUMMARY TABLE (2 columns: label | value) ---
            if len(rows[0]) == 2:
                for row in rows:
                    if not row or len(row) < 2:
                        continue
                    label = str(row[0]).strip().lower() if row[0] else ""
                    val_raw = str(row[1]).strip() if row[1] else ""
                    val = _parse_amount(val_raw)

                    if "subtotal" in label:
                        if val is not None:
                            subtotal = val
                    elif "discount" in label:
                        if val is not None:
                            discount = val
                    elif "taxable amount" in label:
                        if val is not None:
                            taxable_amount = val
                    elif "gst" in label or "vat" in label or "tax" in label:
                        # Could be "GST (18%)" — extract rate and amount separately
                        rate_match = re.search(r'\((\d+(?:\.\d+)?)%\)', label)
                        if rate_match:
                            tax_rate = float(rate_match.group(1))
                        if val is not None:
                            tax = val
                    elif "total" in label:
                        if val is not None:
                            total = val
                continue

        # ---- 3. Fallback: parse summary from raw text if tables didn't capture it ----
        if subtotal == 0:
            m = re.search(r'Subtotal\s+[n₹Rs\.INR]*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                subtotal = _parse_amount(m.group(1)) or 0.0
        if tax == 0:
            m = re.search(r'GST\s*(?:\(\d+%\))?\s+[n₹Rs\.INR]*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                tax = _parse_amount(m.group(1)) or 0.0
        if total == 0:
            m = re.search(r'TOTAL\s+(?:DUE\s+)?[n₹Rs\.INR]*([\d,]+\.?\d*)', text, re.IGNORECASE)
            if m:
                total = _parse_amount(m.group(1)) or 0.0
        if tax_rate == 0:
            m = re.search(r'GST\s*\((\d+(?:\.\d+)?)%\)', text, re.IGNORECASE)
            if m:
                tax_rate = float(m.group(1))

        # ---- 4. Calculate derived fields if missing ----
        if subtotal == 0 and line_items:
            subtotal = round(sum(i.amount for i in line_items), 2)
        if taxable_amount == 0:
            taxable_amount = round(subtotal - discount, 2)
        if tax == 0 and tax_rate > 0 and taxable_amount > 0:
            tax = round(taxable_amount * tax_rate / 100, 2)
        if total == 0:
            total = round(subtotal - discount + tax, 2)

        bill_id = f"bill-{uuid.uuid4().hex[:8]}"

        print(f"[LocalParser] Parsed: provider={provider}, subtotal={subtotal}, tax={tax}, total={total}, line_items={len(line_items)}")

        return Bill(
            bill_id=bill_id,
            user_id="local-user",
            bill_type=bill_type,
            provider=provider,
            billing_period=billing_period,
            issue_date=issue_date,
            due_date=due_date,
            invoice_number=invoice_number,
            currency="INR",
            subtotal=subtotal,
            discount=discount,
            taxable_amount=taxable_amount,
            tax_rate=tax_rate,
            tax=tax,
            total=total,
            line_items=line_items,
            source_document={
                "s3_key": filename,
                "page_count": page_count
            },
            extraction_status="completed"
        )

    @staticmethod
    def _extract_provider(text: str) -> str:
        """Best-effort provider extraction from bill text."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        # Skip first line if it's a header/banner like "BILL SHIELD SAMPLE BILL"
        for line in lines:
            if re.search(r'(shield|sample|bill|note|testing|expected)', line, re.IGNORECASE):
                continue
            if len(line) > 5 and line.isupper():
                return line
            if len(line) > 10:
                return line
        return lines[0] if lines else "Unknown Provider"
