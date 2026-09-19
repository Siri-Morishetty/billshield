"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getBills, getFindings, getDemoBills, clearUploadedBills, formatCurrency, calculatePercentageChange } from "@/lib/api";
import { Bill, Finding, DemoBill } from "@/lib/types";
import {
  ArrowUpRight, Plus, AlertCircle, FileText, ChevronRight,
  Trash2, Sparkles, ShieldCheck, TrendingUp, AlertTriangle,
  Activity, Play
} from "lucide-react";

function SeverityBadge({ priority }: { priority: string }) {
  const cfg = {
    HIGH:   { cls: "bg-red-500/20 text-red-400 border-red-500/30",    dot: "bg-red-500",    label: "High" },
    MEDIUM: { cls: "bg-orange-500/20 text-orange-400 border-orange-500/30", dot: "bg-orange-500", label: "Review" },
    LOW:    { cls: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", dot: "bg-yellow-500", label: "Low" },
  }[priority] ?? { cls: "bg-gray-500/20 text-gray-400 border-gray-500/30", dot: "bg-gray-500", label: priority };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border ${cfg.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

export default function Dashboard() {
  const router = useRouter();
  const [uploadedBills, setUploadedBills] = useState<Bill[]>([]);
  const [allFindings, setAllFindings] = useState<Finding[]>([]);
  const [demoBills, setDemoBills] = useState<DemoBill[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [allBills, demos] = await Promise.all([getBills(), getDemoBills()]);
      const uploaded = allBills.filter((b) => !b.is_demo);
      setDemoBills(demos);
      setUploadedBills(uploaded);

      const findings: Finding[] = [];
      for (const b of uploaded) {
        const f = await getFindings(b.bill_id);
        findings.push(...f);
      }
      setAllFindings(findings);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleClear = async () => {
    await clearUploadedBills();
    await load();
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const mostRecentBill = uploadedBills[0] ?? null;
  const previousBill   = uploadedBills[1] ?? null;
  const pctChange = mostRecentBill && previousBill
    ? calculatePercentageChange(mostRecentBill.total, previousBill.total)
    : null;
  const reviewAmount = allFindings.reduce((s, f) => s + (f.amount ?? 0), 0);

  return (
    <div className="space-y-12">
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            Dashboard
          </h1>
          <p className="text-gray-400 mt-1">Verify calculations. Spot new charges. Understand your bills.</p>
        </div>
        <div className="flex gap-3">
          {uploadedBills.length > 0 && (
            <button
              id="btn-reset-bills"
              onClick={handleClear}
              className="bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 px-4 py-2.5 rounded-xl font-semibold flex items-center gap-2 transition-all text-sm"
            >
              <Trash2 className="w-4 h-4" /> Clear Uploads
            </button>
          )}
          <Link
            href="/upload"
            id="btn-upload-bill"
            className="bg-white text-black hover:bg-gray-100 px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.1)] transition-all text-sm"
          >
            <Plus className="w-4 h-4" /> Upload Bill
          </Link>
        </div>
      </div>

      {/* ── Try Demo Bills ── */}
      <section aria-label="Demo bills">
        <div className="flex items-center gap-3 mb-5">
          <div className="bg-purple-500/10 p-2 rounded-lg">
            <Sparkles className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Try a Demo Bill</h2>
            <p className="text-gray-500 text-sm">Explore BillShield with synthetic sample bills — no upload needed.</p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {demoBills.map((demo) => (
            <Link
              key={demo.bill_id}
              href={`/bills/${demo.bill_id}`}
              id={`demo-bill-${demo.bill_id}`}
              className="group p-4 rounded-2xl bg-white/4 border border-white/8 hover:border-purple-500/40 hover:bg-purple-500/5 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">Demo</span>
                {demo.high_findings > 0
                  ? <AlertTriangle className="w-4 h-4 text-red-400" />
                  : demo.findings_count > 0
                  ? <Activity className="w-4 h-4 text-orange-400" />
                  : <ShieldCheck className="w-4 h-4 text-green-400" />
                }
              </div>
              <div>
                <p className="font-bold text-white text-sm group-hover:text-purple-200 transition-colors">{demo.demo_label}</p>
                <p className="text-gray-500 text-xs mt-1 leading-relaxed">{demo.demo_description}</p>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-white/5">
                <span className="font-mono text-white text-sm font-semibold">{formatCurrency(demo.total)}</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  demo.findings_count === 0
                    ? "bg-green-500/10 text-green-400"
                    : demo.high_findings > 0
                    ? "bg-red-500/10 text-red-400"
                    : "bg-orange-500/10 text-orange-400"
                }`}>
                  {demo.findings_count === 0 ? "Clean" : `${demo.findings_count} findings`}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Uploaded Bills Stats (only if user has uploaded bills) ── */}
      {uploadedBills.length > 0 && (
        <>
          <section aria-label="Your bill stats">
            <h2 className="text-xl font-bold text-white mb-5 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-400" /> Your Bills
            </h2>
            <div className="grid md:grid-cols-3 gap-5">
              <div className="p-6 rounded-2xl bg-gradient-to-br from-blue-900/30 to-blue-900/10 border border-blue-500/20 space-y-2 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl -mr-8 -mt-8" />
                <p className="text-blue-200 font-semibold text-xs tracking-widest uppercase">Latest Bill</p>
                <p className="text-4xl font-black text-white">{formatCurrency(mostRecentBill!.total, mostRecentBill!.currency)}</p>
                {pctChange !== null && pctChange !== 0 && (
                  <div className={`flex items-center gap-1 w-fit px-2 py-1 rounded-lg text-xs font-bold ${
                    pctChange > 0 ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400"
                  }`}>
                    <ArrowUpRight className={`w-3 h-3 ${pctChange < 0 ? "rotate-180" : ""}`} />
                    {Math.abs(pctChange).toFixed(1)}% vs last
                  </div>
                )}
                <p className="text-gray-500 text-sm">{mostRecentBill!.provider}</p>
              </div>

              <div className="p-6 rounded-2xl bg-gradient-to-br from-orange-900/30 to-orange-900/10 border border-orange-500/20 space-y-2 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-orange-500/10 rounded-full blur-2xl -mr-8 -mt-8" />
                <p className="text-orange-200 font-semibold text-xs tracking-widest uppercase">Findings</p>
                <p className="text-4xl font-black text-white">{allFindings.length}</p>
                <p className="text-gray-500 text-sm">
                  {allFindings.filter((f) => f.priority === "HIGH").length} high · {allFindings.filter((f) => f.priority === "MEDIUM").length} review
                </p>
              </div>

              <div className="p-6 rounded-2xl bg-gradient-to-br from-emerald-900/30 to-emerald-900/10 border border-emerald-500/20 space-y-2 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl -mr-8 -mt-8" />
                <p className="text-emerald-200 font-semibold text-xs tracking-widest uppercase">Review Amount</p>
                <p className="text-4xl font-black text-white">{formatCurrency(reviewAmount, mostRecentBill?.currency)}</p>
                <p className="text-gray-500 text-sm">Sum of flagged charges</p>
              </div>
            </div>
          </section>

          {/* ── Findings + Bills ── */}
          <div className="grid md:grid-cols-2 gap-8">
            {/* Recent findings */}
            <div className="space-y-4">
              <h3 className="font-bold text-lg flex items-center gap-2 text-white">
                <AlertCircle className="w-5 h-5 text-orange-500" /> Recent Findings
              </h3>
              {allFindings.length === 0 ? (
                <div className="p-6 rounded-2xl bg-green-500/5 border border-green-500/20 flex items-center gap-4">
                  <ShieldCheck className="w-8 h-8 text-green-400" />
                  <div>
                    <p className="font-bold text-green-300">All clear</p>
                    <p className="text-green-400/70 text-sm">No issues detected on your uploaded bills.</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {allFindings.slice(0, 5).map((finding) => {
                    const bill = uploadedBills.find((b) => b.bill_id === finding.bill_id);
                    return (
                      <Link href={`/investigate/${finding.bill_id}`} key={finding.finding_id}>
                        <div className="p-4 rounded-xl bg-white/4 border border-white/8 hover:border-orange-500/40 hover:bg-white/8 transition-all flex justify-between items-start group">
                          <div className="flex gap-3 items-start">
                            <SeverityBadge priority={finding.priority} />
                            <div>
                              <p className="font-semibold text-gray-200 group-hover:text-white text-sm">{finding.title}</p>
                              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{finding.description}</p>
                            </div>
                          </div>
                          {finding.amount != null && (
                            <p className="font-mono font-bold text-white whitespace-nowrap ml-4 text-sm">{formatCurrency(finding.amount, bill?.currency)}</p>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Uploaded bills */}
            <div className="space-y-4">
              <h3 className="font-bold text-lg flex items-center gap-2 text-white justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-500" /> Uploaded Bills
                </div>
                <Link href="/history" className="text-sm font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1">
                  View all <ChevronRight className="w-4 h-4" />
                </Link>
              </h3>
              <div className="space-y-3">
                {uploadedBills.slice(0, 4).map((bill) => (
                  <Link href={`/bills/${bill.bill_id}`} key={bill.bill_id}>
                    <div className="p-4 rounded-xl bg-white/4 border border-white/8 hover:border-blue-500/40 hover:bg-white/8 flex justify-between items-center transition-all group">
                      <div>
                        <p className="font-bold text-gray-200 group-hover:text-white text-sm">{bill.provider}</p>
                        <p className="text-gray-500 text-xs capitalize">
                          {bill.bill_type}
                          {bill.billing_period ? ` · ${bill.billing_period.start_date}` : ""}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-white text-sm">{formatCurrency(bill.total, bill.currency)}</p>
                        {bill.due_date && <p className="text-xs text-gray-500">Due {bill.due_date}</p>}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* ── Empty state for uploads ── */}
      {uploadedBills.length === 0 && (
        <section className="rounded-2xl border border-dashed border-white/10 p-10 text-center space-y-5">
          <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto">
            <FileText className="w-8 h-8 text-gray-600" />
          </div>
          <div>
            <p className="text-xl font-bold text-white">No bills uploaded yet</p>
            <p className="text-gray-500 mt-1">Upload your first bill, or try a demo bill above to see BillShield in action.</p>
          </div>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-bold transition-all"
          >
            <Plus className="w-5 h-5" /> Upload Your First Bill
          </Link>
        </section>
      )}
    </div>
  );
}
