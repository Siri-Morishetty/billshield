import { getBill, getFindings, getBills, formatCurrency, calculatePercentageChange } from "@/lib/api";
import Link from "next/link";
import { ArrowUpRight, ChevronRight, FileText, Bot } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function BillPage({ params }: { params: { id: string } }) {
  const [bill, findings, allBills] = await Promise.all([
    getBill(params.id),
    getFindings(params.id),
    getBills(),
  ]);

  if (!bill) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-6">
        <h2 className="text-3xl font-bold text-white">Bill Not Found</h2>
        <p className="text-gray-400">This bill may have been reset or does not exist.</p>
        <Link href="/dashboard" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  // Find the previous bill (same provider, different ID)
  const sameBills = allBills.filter((b) => b.provider === bill.provider);
  const currentIdx = sameBills.findIndex((b) => b.bill_id === params.id);
  const previousBill = sameBills[currentIdx + 1] || null;

  const pctChange = previousBill
    ? calculatePercentageChange(bill.total, previousBill.total)
    : null;

  const newCharges = findings.filter((f: any) => f.type === "NEW_CHARGE");

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white">Bill Details</span>
      </div>

      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-extrabold uppercase">
            {bill.issue_date
              ? new Date(bill.issue_date).toLocaleString("default", { month: "long", year: "numeric" })
              : "Current"}{" "}BILL
          </h1>
          <p className="text-gray-400 mt-2 text-lg">{bill.provider}</p>
          {bill.invoice_number && (
            <p className="text-gray-600 text-sm mt-1">Invoice: {bill.invoice_number}</p>
          )}
        </div>
        <div className="text-right">
          <p className="text-4xl font-extrabold">{formatCurrency(bill.total)}</p>
          {pctChange !== null && pctChange !== 0 && (
            <p className={`${pctChange > 0 ? "text-red-400" : "text-green-400"} font-medium flex items-center justify-end gap-1 mt-2`}>
              <ArrowUpRight className={`w-4 h-4 ${pctChange < 0 ? "rotate-180" : ""}`} />
              {Math.abs(pctChange).toFixed(2)}% vs previous
            </p>
          )}
        </div>
      </div>

      {/* Details + Findings */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Details */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold flex items-center gap-2">
            <FileText className="w-5 h-5 text-gray-400" /> DETAILS
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Type</span>
              <span className="capitalize">{bill.bill_type}</span>
            </div>
            {bill.billing_period && (
              <div className="flex justify-between">
                <span className="text-gray-400">Billing Period</span>
                <span>{bill.billing_period.start_date} – {bill.billing_period.end_date}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-400">Due Date</span>
              <span>{bill.due_date || "N/A"}</span>
            </div>
          </div>

          {/* Financial summary */}
          <div className="pt-4 border-t border-gray-800 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Subtotal</span>
              <span>{formatCurrency(bill.subtotal)}</span>
            </div>
            {bill.discount > 0 && (
              <div className="flex justify-between text-green-400">
                <span>Discount</span>
                <span>-{formatCurrency(bill.discount)}</span>
              </div>
            )}
            {bill.tax > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-400">GST ({bill.tax_rate}%)</span>
                <span>{formatCurrency(bill.tax)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold text-base pt-1 border-t border-gray-700">
              <span>Total</span>
              <span>{formatCurrency(bill.total)}</span>
            </div>
          </div>

          <div className="pt-4">
            <Link
              href={`/investigate/${bill.bill_id}`}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-bold flex justify-center items-center gap-2 transition-colors"
            >
              <Bot className="w-5 h-5" /> Investigate Bill
            </Link>
          </div>
        </div>

        {/* Findings */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-orange-500" /> FINDINGS
          </h3>
          <div className="space-y-3">
            {findings.length > 0 ? (
              findings.map((f: any) => (
                <div key={f.finding_id} className="flex gap-3 text-sm">
                  <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                    f.priority === "HIGH" ? "bg-red-500" :
                    f.priority === "MEDIUM" ? "bg-orange-500" : "bg-yellow-500"
                  }`} />
                  <div>
                    <p className="font-semibold">{f.title}</p>
                    <p className="text-gray-400">{f.description}</p>
                    {f.amount != null && (
                      <p className="text-white font-mono mt-0.5">{formatCurrency(f.amount)}</p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-sm">No issues detected — all calculations are valid.</p>
            )}
          </div>
        </div>
      </div>

      {/* Line items */}
      {bill.line_items && bill.line_items.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold">LINE ITEMS</h3>
          <div className="space-y-2">
            {bill.line_items.map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-gray-300">{item.description}</span>
                <span className="font-mono">{formatCurrency(item.amount)}</span>
              </div>
            ))}
            <div className="flex justify-between font-bold pt-2 border-t border-gray-700">
              <span>Sum of line items</span>
              <span className="font-mono">{formatCurrency(bill.line_items.reduce((s: number, i: any) => s + i.amount, 0))}</span>
            </div>
          </div>
        </div>
      )}

      {/* Why did it increase? */}
      {pctChange !== null && pctChange > 0 && previousBill && (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-6">
          <h3 className="font-bold">WHY DID IT INCREASE?</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Previous bill</span>
              <span className="font-mono">{formatCurrency(previousBill.total)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Current bill</span>
              <span className="font-mono">{formatCurrency(bill.total)}</span>
            </div>
            <div className="flex justify-between font-bold border-t border-gray-700 pt-2 text-red-400">
              <span>Increase</span>
              <span className="font-mono">+{formatCurrency(bill.total - previousBill.total)} (+{Math.abs(pctChange).toFixed(2)}%)</span>
            </div>
          </div>

          {newCharges.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-300">New charges driving the increase:</p>
              {newCharges.map((f: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-48 text-gray-400 text-sm truncate">{f.title}</div>
                  <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-orange-500 rounded-full" style={{
                      width: `${Math.min(100, ((f.amount || 0) / (bill.total - previousBill.total)) * 100)}%`
                    }} />
                  </div>
                  <div className="w-28 text-right font-mono text-sm">+{formatCurrency(f.amount || 0)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
