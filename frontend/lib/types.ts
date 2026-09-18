export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  page?: number;
  line_number?: number;
}

export interface Bill {
  bill_id: string;
  user_id: string;
  bill_type: string;
  provider: string;
  billing_period?: { start_date: string; end_date: string };
  issue_date?: string;
  due_date?: string;
  invoice_number?: string;
  currency: string;
  subtotal: number;
  discount: number;
  taxable_amount: number;
  tax_rate: number;
  tax: number;
  fees: number;
  total: number;
  line_items: LineItem[];
  extraction_status: string;
  created_at: string;
}

export interface Finding {
  finding_id: string;
  bill_id: string;
  type: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  description: string;
  amount?: number;
  evidence_ids: string[];
}

export interface Evidence {
  evidence_id: string;
  bill_id: string;
  page?: number;
  line_number?: number;
  text: string;
  source: string;
}
