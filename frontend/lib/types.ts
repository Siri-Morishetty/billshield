export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  page?: number;
  line_number?: number;
}

export interface BillingPeriod {
  start_date: string;
  end_date: string;
}

export interface Bill {
  bill_id: string;
  user_id: string;
  bill_type: string;
  provider: string;
  billing_period?: BillingPeriod;
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
  is_demo: boolean;
  demo_label?: string;
  demo_description?: string;
  created_at: string;
}

export interface Finding {
  finding_id: string;
  bill_id: string;
  type: FindingType;
  priority: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  description: string;
  amount?: number;
  evidence_ids: string[];
  evidence?: Record<string, unknown>;
}

export type FindingType =
  | "TOTAL_MISMATCH"
  | "CALCULATION_DISCREPANCY"
  | "LINE_ITEM_MISMATCH"
  | "TAX_MISMATCH"
  | "DUPLICATE_CHARGE"
  | "NEW_CHARGE"
  | "PRICE_INCREASE"
  | "PRICE_DECREASE"
  | "QUANTITY_CHANGE"
  | "UNUSUAL_INCREASE"
  | "MISSING_INFORMATION";

export interface DemoBill {
  bill_id: string;
  provider: string;
  total: number;
  demo_label: string;
  demo_description: string;
  findings_count: number;
  high_findings: number;
}

export interface HistoryComparison {
  previous_total: number;
  current_total: number;
  absolute_difference: number;
  percentage_difference: number;
  average: number;
  minimum: number;
  maximum: number;
}

export interface InvestigationResult {
  bill_id: string;
  provider: string;
  summary: string;
  findings: Finding[];
  evidence: EvidenceItem[];
  comparison: HistoryComparison;
  questions: string[];
  explanation: string;
  explanation_source: "amazon_bedrock" | "deterministic";
}

export interface EvidenceItem {
  evidence_id: string;
  finding_type: string;
  title: string;
  source: string;
  current_bill_text: string;
  historical_check: string;
  amount?: number;
  percentage_change?: number;
}
