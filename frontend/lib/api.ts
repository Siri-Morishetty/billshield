import { Bill, Finding } from './types';

const API_BASE = "http://localhost:8000/api";

/** Format any amount as INR currency with 2 decimal places. Single source of truth. */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/** Calculate percentage change between two values. Returns null if previous is 0. */
export function calculatePercentageChange(current: number, previous: number): number | null {
  if (previous === 0) return current === 0 ? 0 : null;
  return ((current - previous) / previous) * 100;
}

export async function processUploadedBill(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Upload failed: ${err}`);
  }
  return res.json();
}

export async function clearAllData() {
  await fetch(`${API_BASE}/clear`, { method: "POST" });
}

export async function getBills(): Promise<Bill[]> {
  try {
    const res = await fetch(`${API_BASE}/bills`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function getBill(id: string): Promise<Bill | null> {
  if (!id || id === "undefined") return null;
  try {
    const res = await fetch(`${API_BASE}/bills/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getFindings(billId: string): Promise<Finding[]> {
  if (!billId || billId === "undefined") return [];
  try {
    const res = await fetch(`${API_BASE}/bills/${billId}/findings`, { cache: "no-store" });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function investigateBill(billId: string): Promise<any> {
  if (!billId || billId === "undefined") throw new Error("Invalid bill ID");
  const res = await fetch(`${API_BASE}/investigate/${billId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to investigate");
  return await res.json();
}
