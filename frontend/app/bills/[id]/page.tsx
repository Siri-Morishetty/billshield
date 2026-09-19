import { getBill, getFindings, getHistoryComparison, formatCurrency, calculatePercentageChange } from "@/lib/api";
import { Finding } from "@/lib/types";
import Link from "next/link";
import {
  ArrowUpRight, ChevronRight, FileText, Bot,
  ShieldCheck, AlertTriangle, TrendingUp, TrendingDown, Info
} from "lucide-react";

export const dynamic = "force-dynamic";

function SeverityIcon({ priority }: { priority: string }) {
  if (priority === "HIGH") return <span className="text-lg" aria-label="High priority">🔴</span>;
  if (priority === "MEDIUM") return <span className="text-lg" aria-label="Medium priority">🟡</span>;
  return <span className="text-lg" aria-label="Low priority">🔵</span>;
}

function FindingTypeIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    TOTAL_MISMATCH:           <AlertTriangle className="w-4 h-4 text-red-400" />,
    CALCULATION_DISCREPANCY:  <AlertTriangle className="w-4 h-4 text-red-400" />,
    LINE_ITEM_MISMATCH:       <AlertTriangle className="w-4 h-4 text-red-400" />,
    NEW_CHARGE:               <TrendingUp className="w-4 h-4 text-orange-400" />,
    PRICE_INCREASE:           <TrendingUp className="w-4 h-4 text-orange-400" />,
    PRICE_DECREASE:           <TrendingDown className="w-4 h-4 text-blue-400" />,
    QUANTITY_CHANGE:          <Info className="w-4 h-4 text-yellow-400" />,
    DUPLICATE_CHARGE:         <AlertTriangle className="w-4 h-4 text-orange-400" />,
    UNUSUAL_INCREASE:         <TrendingUp className="w-4 h-4 text-orange-400" />,
  };
  return <>{icons[type] ?? <Info className="w-4 h-4 text-gray-400" />}</>;
}

function EvidenceCard({ finding, currency }: { finding: Finding; currency?: string }) {
  const ev = finding.evidence as Record<string, unknown> | null;
  if (!ev) return null;
  const cur = (ev.currency as string) || currency || "USD";

  return (
    <div className="mt-3 bg-black/40 rounded-xl p-4 border border-white/5 space-y-2 text-sm">
      <p className="text-xs font-bold text-gray-500 uppercase tracking-widest">Evidence</p>

      {finding.type === "TOTAL_MISMATCH" && (
        <div className="space-y-1.5 font-mono">
          {typeof ev.subtotal === "number" && (
            <div className="flex justify-between"><span className="text-gray-400">Subtotal</span><span>{formatCurrency(ev.subtotal as number, cur)}</span></div>
          )}
          {typeof ev.discount === "number" && ev.discount > 0 && (
            <div className="flex justify-between text-green-400"><span>Discount</span><span>−{formatCurrency(ev.discount as number, cur)}</span></div>
          )}
          {typeof ev.fees === "number" && ev.fees > 0 && (
            <div className="flex justify-between"><span className="text-gray-400">Fees</span><span>{formatCurrency(ev.fees as number, cur)}</span></div>
          )}
          {typeof ev.tax === "number" && ev.tax > 0 && (
            <div className="flex justify-between"><span className="text-gray-400">Tax</span><span>{formatCurrency(ev.tax as number, cur)}</span></div>
          )}
          <div className="flex justify-between pt-1 border-t border-white/10 text-emerald-400 font-bold">
            <span>Calculated total</span>
            <span>{formatCurrency(ev.calculated_total as number, cur)}</span>
          </div>
          <div className="flex justify-between text-red-400 font-bold">
            <span>Reported total</span>
            <span>{formatCurrency(ev.reported_total as number, cur)}</span>
          </div>
          <div className="flex justify-between text-orange-400 font-bold">
            <span>Difference</span>
            <span>{formatCurrency(((ev.difference as number) || 0), cur)}</span>
          </div>
        </div>
      )}

      {finding.type === "CALCULATION_DISCREPANCY" && Array.isArray(ev.line_items) && (
        <div className="space-y-1 font-mono">
          {(ev.line_items as Array<{description: string; amount: number}>).map((li, i) => (
            <div key={i} className="flex justify-between text-gray-300">
              <span className="truncate pr-4">{li.description}</span>
              <span>{formatCurrency(li.amount, cur)}</span>
            </div>
          ))}
          <div className="flex justify-between pt-1 border-t border-white/10 text-emerald-400 font-bold">
            <span>Sum of line items</span>
            <span>{formatCurrency(ev.calculated_sum as number, cur)}</span>
          </div>
          <div className="flex justify-between text-red-400 font-bold">
            <span>Reported subtotal</span>
            <span>{formatCurrency(ev.reported_subtotal as number, cur)}</span>
          </div>
        </div>
      )}

      {(finding.type === "PRICE_INCREASE" || finding.type === "PRICE_DECREASE") && (
        <div className="space-y-1.5 font-mono">
          <div className="flex justify-between">
            <span className="text-gray-400">Previous price</span>
            <span>{formatCurrency(ev.previous_price as number, cur)}</span>
          </div>
          <div className="flex justify-between font-bold">
            <span className="text-gray-400">Current price</span>
            <span className={finding.type === "PRICE_INCREASE" ? "text-red-400" : "text-green-400"}>
              {formatCurrency(ev.current_price as number, cur)}
            </span>
          </div>
          <div className={`flex justify-between font-bold pt-1 border-t border-white/10 ${finding.type === "PRICE_INCREASE" ? "text-red-400" : "text-green-400"}`}>
            <span>Change</span>
            <span>
              {finding.type === "PRICE_INCREASE" ? "+" : "−"}
              {formatCurrency(Math.abs(ev.difference as number), cur)}
              {" "}({Math.abs(ev.percentage_change as number).toFixed(1)}%)
            </span>
          </div>
        </div>
      )}

      {finding.type === "NEW_CHARGE" && (
        <div className="space-y-1 text-gray-300">
          <p>First appeared on this bill.</p>
          <p>Checked <strong className="text-white">{ev.previous_bills_checked as number}</strong> previous bill(s) — not found in any.</p>
          <p className="font-mono text-orange-400 font-bold">{formatCurrency(ev.amount as number, cur)}</p>
        </div>
      )}

      {finding.type === "DUPLICATE_CHARGE" && (
        <div className="space-y-1 text-gray-300 font-mono">
          <p>Appears <strong className="text-white">{ev.occurrences as number} times</strong> at {formatCurrency(ev.amount as number, cur)} each.</p>
        </div>
      )}
    </div>
  );
}

export default async function BillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [bill, findings, comparison] = await Promise.all([
    getBill(id),
    getFindings(id),
    getHistoryComparison(id),
  ]);

  if (!bill) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-6">
        <div className="w-20 h-20 bg-gray-900 rounded-full flex items-center justify-center border border-gray-800">
          <FileText className="w-10 h-10 text-gray-600" />
        </div>
        <h2 className="text-2xl font-bold text-white">Bill Not Found</h2>
        <p className="text-gray-400">This bill does not exist or has been cleared.</p>
        <Link href="/dashboard" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-bold transition-colors">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  const prevTotal = comparison?.previous_total ?? 0;
  const pctChange = prevTotal > 0 ? calculatePercentageChange(bill.total, prevTotal) : null;
  const highFindings = findings.filter((f: Finding) => f.priority === "HIGH");
  const medFindings = findings.filter((f: Finding) => f.priority === "MEDIUM");
  const lowFindings = findings.filter((f: Finding) => f.priority === "LOW");

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
        <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white truncate">{bill.provider}</span>
      </div>

      {/* Demo label banner */}
      {bill.is_demo && (
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl px-5 py-3 flex items-center gap-3">
          <span className="text-purple-400 text-sm font-bold">📊 DEMO BILL</span>
          <span className="text-gray-400 text-sm">{bill.demo_description}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-start gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white leading-tight">
            {bill.issue_date
              ? new Date(bill.issue_date).toLocaleString("default", { month: "long", year: "numeric" })
              : "Current"}{" "}Bill
          </h1>
          <p className="text-gray-400 mt-1 text-lg">{bill.provider}</p>
          {bill.invoice_number && (
            <p className="text-gray-600 text-sm mt-0.5">Invoice: {bill.invoice_number}</p>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-3xl md:text-4xl font-extrabold text-white">{formatCurrency(bill.total, bill.currency)}</p>
          {pctChange !== null && pctChange !== 0 && (
            <p className={`${pctChange > 0 ? "text-red-400" : "text-green-400"} font-semibold flex items-center justify-end gap-1 mt-1 text-sm`}>
              <ArrowUpRight className={`w-4 h-4 ${pctChange < 0 ? "rotate-180" : ""}`} />
              {Math.abs(pctChange).toFixed(1)}% vs previous
            </p>
          )}
          {bill.due_date && <p className="text-gray-500 text-sm mt-1">Due {bill.due_date}</p>}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid md:grid-cols-2 gap-5">
        {/* Bill details */}
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold text-sm uppercase tracking-widest text-gray-400 flex items-center gap-2">
            <FileText className="w-4 h-4" /> Bill Details
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Type</span>
              <span className="capitalize font-medium">{bill.bill_type}</span>
            </div>
            {bill.billing_period && (
              <div className="flex justify-between">
                <span className="text-gray-400">Period</span>
                <span className="font-medium">{bill.billing_period.start_date} – {bill.billing_period.end_date}</span>
              </div>
            )}
            {bill.due_date && (
              <div className="flex justify-between">
                <span className="text-gray-400">Due Date</span>
                <span className="font-medium">{bill.due_date}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-400">Extraction</span>
              <span className="text-xs font-mono text-blue-400">{bill.extraction_status}</span>
            </div>
          </div>
          <div className="pt-3 border-t border-white/8 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Subtotal</span>
              <span className="font-mono">{formatCurrency(bill.subtotal, bill.currency)}</span>
            </div>
            {bill.discount != null && bill.discount > 0 && (
              <div className="flex justify-between text-green-400">
                <span>Discount</span>
                <span className="font-mono">−{formatCurrency(bill.discount, bill.currency)}</span>
              </div>
            )}
            {bill.tax != null && bill.tax > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-400">
                  {bill.tax_rate ? (bill.currency === "INR" ? `GST (${bill.tax_rate}%)` : `Tax (${bill.tax_rate}%)`) : "Tax"}
                </span>
                <span className="font-mono">{formatCurrency(bill.tax, bill.currency)}</span>
              </div>
            )}
            {bill.fees != null && bill.fees > 0 && (
              <div className="flex justify-between">
                <span className="text-gray-400">Fees</span>
                <span className="font-mono">{formatCurrency(bill.fees, bill.currency)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold text-base pt-2 border-t border-white/8">
              <span>Total</span>
              <span className="font-mono">{formatCurrency(bill.total, bill.currency)}</span>
            </div>
          </div>
          <Link
            href={`/investigate/${bill.bill_id}`}
            id={`btn-investigate-${bill.bill_id}`}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white px-4 py-3 rounded-xl font-bold flex justify-center items-center gap-2 transition-colors text-sm"
          >
            <Bot className="w-4 h-4" /> Investigate with AI
          </Link>
        </div>

        {/* Findings summary */}
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold text-sm uppercase tracking-widest text-gray-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-orange-400" /> Findings ({findings.length})
          </h3>
          {findings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 space-y-3">
              <ShieldCheck className="w-12 h-12 text-green-500" />
              <p className="font-bold text-green-300">No issues detected</p>
              <p className="text-gray-500 text-sm text-center">All calculations verified. No unusual charges found.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {findings.map((f: Finding) => (
                <div key={f.finding_id} className="flex gap-3 text-sm">
                  <SeverityIcon priority={f.priority} />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-white">{f.title}</p>
                    <p className="text-gray-400 text-xs mt-0.5 line-clamp-2">{f.description}</p>
                    {f.amount != null && (
                      <p className="font-mono text-white font-bold mt-1">{formatCurrency(f.amount, bill.currency)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detailed findings with evidence */}
      {findings.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-white">Findings & Evidence</h2>
          <div className="space-y-4">
            {([...highFindings, ...medFindings, ...lowFindings] as Finding[]).map((f) => (
              <div
                key={f.finding_id}
                className={`rounded-2xl p-5 border space-y-1 ${
                  f.priority === "HIGH"
                    ? "bg-red-500/5 border-red-500/20"
                    : f.priority === "MEDIUM"
                    ? "bg-orange-500/5 border-orange-500/20"
                    : "bg-yellow-500/5 border-yellow-500/20"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <FindingTypeIcon type={f.type} />
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-bold text-white">{f.title}</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                          f.priority === "HIGH"
                            ? "bg-red-500/20 text-red-400"
                            : f.priority === "MEDIUM"
                            ? "bg-orange-500/20 text-orange-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}>{f.priority}</span>
                      </div>
                      <p className="text-gray-400 text-sm mt-1">{f.description}</p>
                    </div>
                  </div>
                  {f.amount != null && (
                    <p className="font-mono font-bold text-white whitespace-nowrap text-lg flex-shrink-0">
                      {formatCurrency(f.amount, bill.currency)}
                    </p>
                  )}
                </div>
                <EvidenceCard finding={f} currency={bill.currency} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Line items table */}
      {bill.line_items && bill.line_items.length > 0 && (
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold text-sm uppercase tracking-widest text-gray-400">Line Items</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/8">
                  <th className="text-left py-2 text-gray-500 font-semibold">Description</th>
                  <th className="text-right py-2 text-gray-500 font-semibold">Qty</th>
                  <th className="text-right py-2 text-gray-500 font-semibold">Unit Price</th>
                  <th className="text-right py-2 text-gray-500 font-semibold">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {bill.line_items.map((item, i) => {
                  const lineTotal = item.quantity * item.unit_price;
                  const mismatch = Math.abs(lineTotal - item.amount) > 0.02;
                  return (
                    <tr key={i} className={mismatch ? "bg-red-500/5" : ""}>
                      <td className="py-3 text-gray-200">{item.description}</td>
                      <td className="py-3 text-right text-gray-400 font-mono">{item.quantity}</td>
                      <td className="py-3 text-right text-gray-400 font-mono">{formatCurrency(item.unit_price, bill.currency)}</td>
                      <td className={`py-3 text-right font-mono font-semibold ${mismatch ? "text-red-400" : "text-white"}`}>
                        {formatCurrency(item.amount, bill.currency)}
                        {mismatch && <span className="ml-1 text-xs text-red-500">(expected {formatCurrency(lineTotal, bill.currency)})</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-white/10">
                  <td colSpan={3} className="py-3 font-bold text-gray-300">Sum of line items</td>
                  <td className="py-3 text-right font-mono font-bold text-white">
                    {formatCurrency(bill.line_items.reduce((s, i) => s + i.amount, 0), bill.currency)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Historical comparison */}
      {comparison && comparison.previous_total > 0 && (
        <div className="bg-white/4 border border-white/8 rounded-2xl p-6 space-y-4">
          <h3 className="font-bold text-sm uppercase tracking-widest text-gray-400">Historical Comparison</h3>
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div className="bg-white/3 rounded-xl p-4">
              <p className="text-gray-500 text-xs mb-1">Previous Total</p>
              <p className="font-mono font-bold text-white text-lg">{formatCurrency(comparison.previous_total, bill.currency)}</p>
            </div>
            <div className="bg-white/3 rounded-xl p-4">
              <p className="text-gray-500 text-xs mb-1">Current Total</p>
              <p className="font-mono font-bold text-white text-lg">{formatCurrency(comparison.current_total, bill.currency)}</p>
            </div>
            <div className={`rounded-xl p-4 ${comparison.absolute_difference > 0 ? "bg-red-500/10" : comparison.absolute_difference < 0 ? "bg-green-500/10" : "bg-white/3"}`}>
              <p className="text-gray-500 text-xs mb-1">Change</p>
              <p className={`font-mono font-bold text-lg ${comparison.absolute_difference > 0 ? "text-red-400" : comparison.absolute_difference < 0 ? "text-green-400" : "text-white"}`}>
                {comparison.absolute_difference > 0 ? "+" : ""}{formatCurrency(comparison.absolute_difference, bill.currency)}
              </p>
              <p className={`text-xs font-semibold ${comparison.absolute_difference > 0 ? "text-red-400" : "text-green-400"}`}>
                {comparison.percentage_difference.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
