import { Bill, Finding, DemoBill, InvestigationResult, HistoryComparison } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

/** Format amount dynamically based on detected currency. Single source of truth. */
export function formatCurrency(amount: number | null | undefined, currency?: string): string {
  if (amount == null || isNaN(amount)) {
    return "—";
  }
  const curr = (currency || "INR").toUpperCase();
  const localeMap: Record<string, string> = {
    USD: "en-US",
    INR: "en-IN",
    EUR: "de-DE",
    GBP: "en-GB",
    AUD: "en-AU",
    CAD: "en-CA",
  };
  const locale = localeMap[curr] || "en-US";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: curr,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${curr} ${amount.toFixed(2)}`;
  }
}

/** Calculate % change between two values. Returns null if previous is 0 or values are missing. */
export function calculatePercentageChange(current?: number | null, previous?: number | null): number | null {
  if (current == null || previous == null || previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function getBills(): Promise<Bill[]> {
  try {
    return await apiFetch<Bill[]>("/bills");
  } catch {
    return [];
  }
}

export async function getBill(id: string): Promise<Bill | null> {
  if (!id || id === "undefined") return null;
  try {
    return await apiFetch<Bill>(`/bills/${id}`);
  } catch {
    return null;
  }
}

export async function getFindings(billId: string): Promise<Finding[]> {
  if (!billId || billId === "undefined") return [];
  try {
    return await apiFetch<Finding[]>(`/bills/${billId}/findings`);
  } catch {
    return [];
  }
}

export async function getHistoryComparison(billId: string): Promise<HistoryComparison | null> {
  if (!billId) return null;
  try {
    return await apiFetch<HistoryComparison>(`/bills/${billId}/history-comparison`);
  } catch {
    return null;
  }
}

export async function getDemoBills(): Promise<DemoBill[]> {
  try {
    return await apiFetch<DemoBill[]>("/demo-bills");
  } catch {
    return [];
  }
}

export async function investigateBill(billId: string): Promise<InvestigationResult> {
  if (!billId || billId === "undefined") throw new Error("Invalid bill ID");
  return apiFetch<InvestigationResult>(`/investigate/${billId}`);
}

export async function processUploadedBill(file: File): Promise<{
  bill_id: string;
  extraction_mode: string;
  findings_count: number;
  high_findings: number;
  provider: string;
  total: number;
}> {
  const formData = new FormData();
  formData.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error("Cannot connect to backend at http://localhost:8000. Please ensure the backend server is running with 'python -m uvicorn src.main:app --port 8000'.");
  }
  if (!res.ok) {
    let errMsg = `Upload failed (${res.status})`;
    try {
      const data = await res.json();
      errMsg = data.detail || JSON.stringify(data);
    } catch {
      const text = await res.text().catch(() => "");
      if (text) errMsg = text;
    }
    throw new Error(errMsg);
  }
  return res.json();
}

export async function clearUploadedBills(): Promise<void> {
  await fetch(`${API_BASE}/clear`, { method: "POST" });
}

export async function getHealthStatus(): Promise<{
  status: string;
  mode: string;
  demo_bills: number;
  uploaded_bills: number;
} | null> {
  try {
    return await apiFetch("/health");
  } catch {
    return null;
  }
}
