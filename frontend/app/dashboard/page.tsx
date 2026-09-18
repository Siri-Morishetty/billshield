"use client";

import Link from "next/link";
import { getBills, getFindings, clearAllData } from "@/lib/api";
import { ArrowUpRight, Plus, AlertCircle, FileText, ChevronRight, Trash2 } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

/** Format any number as Indian Rupee currency with exactly 2 decimal places. */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/** Calculate % change between two values. Returns null if previous is 0. */
function calculatePercentageChange(current: number, previous: number): number | null {
  if (previous === 0) return current === 0 ? 0 : null;
  return ((current - previous) / previous) * 100;
}

export default function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const bills = await getBills();

      // Get findings for all uploaded bills (exclude the seeded July historical bill
      // since it has no real findings — it's only for comparison purposes)
      const uploadedBills = bills.filter((b: any) => b.bill_id !== "bill-jul-001");
      let allFindings: any[] = [];
      for (const bill of uploadedBills) {
        const f = await getFindings(bill.bill_id);
        allFindings = [...allFindings, ...f];
      }

      setData({ bills, uploadedBills, allFindings });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading || !data) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Show empty state if no UPLOADED bills (July bill doesn't count)
  if (data.uploadedBills.length === 0) {
    return (
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center h-[60vh] space-y-6">
        <div className="w-24 h-24 bg-gray-900 rounded-full flex items-center justify-center border border-gray-800">
          <FileText className="w-10 h-10 text-gray-600" />
        </div>
        <h2 className="text-3xl font-bold">No bills analyzed yet</h2>
        <p className="text-gray-400 text-lg">Upload your first bill to see the financial intelligence layer in action.</p>
        <Link
          href="/upload"
          className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-full font-bold flex items-center gap-2 shadow-[0_0_20px_rgba(37,99,235,0.3)] transition-all"
        >
          <Plus className="w-5 h-5" /> Upload Bill
        </Link>
      </motion.div>
    );
  }

  const mostRecentBill = data.uploadedBills[0];
  const previousBill = data.uploadedBills[1] || data.bills.find((b: any) => b.bill_id !== mostRecentBill.bill_id);

  const pctChange = previousBill ? calculatePercentageChange(mostRecentBill.total, previousBill.total) : null;

  // Review amount = sum of all finding amounts (no double-counting — each finding is a distinct issue)
  const reviewAmount = data.allFindings.reduce((sum: number, f: any) => sum + (f.amount || 0), 0);

  const handleClear = async () => {
    await clearAllData();
    await load();          // reload from backend — will show July bill only → redirect to empty state
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="space-y-10">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">Welcome Back</h1>
          <p className="text-gray-400 mt-1">Your financial bills, finally understandable.</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleClear}
            className="bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 px-4 py-3 rounded-full font-bold flex items-center gap-2 transition-all"
          >
            <Trash2 className="w-5 h-5" /> Reset
          </button>
          <Link
            href="/upload"
            className="bg-white text-black hover:bg-gray-200 px-6 py-3 rounded-full font-bold flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.15)] transition-all"
          >
            <Plus className="w-5 h-5" /> Upload Bill
          </Link>
        </div>
      </div>

      {/* ─── Top stats ─── */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* This month */}
        <motion.div whileHover={{ y: -5 }} className="p-8 rounded-3xl bg-gradient-to-br from-blue-900/40 to-blue-900/10 border border-blue-500/20 shadow-lg backdrop-blur-md space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
          <p className="text-blue-200 font-semibold text-sm tracking-wider">THIS MONTH</p>
          <p className="text-5xl font-black text-white">{formatCurrency(mostRecentBill.total)}</p>
          {pctChange !== null && pctChange !== 0 && (
            <p className={`${pctChange > 0 ? "text-red-400 bg-red-500/10" : "text-green-400 bg-green-500/10"} text-sm flex items-center gap-1 font-bold w-fit px-2 py-1 rounded-md`}>
              {pctChange > 0 ? "↑" : "↓"} {Math.abs(pctChange).toFixed(2)}% vs last month
            </p>
          )}
        </motion.div>

        {/* Things to review */}
        <motion.div whileHover={{ y: -5 }} className="p-8 rounded-3xl bg-gradient-to-br from-purple-900/40 to-purple-900/10 border border-purple-500/20 shadow-lg backdrop-blur-md space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
          <p className="text-purple-200 font-semibold text-sm tracking-wider">THINGS TO REVIEW</p>
          <p className="text-5xl font-black text-white">{data.allFindings.length}</p>
          <p className="text-gray-400 text-sm font-medium">Across all uploaded bills</p>
        </motion.div>

        {/* Review amount */}
        <motion.div whileHover={{ y: -5 }} className="p-8 rounded-3xl bg-gradient-to-br from-emerald-900/40 to-emerald-900/10 border border-emerald-500/20 shadow-lg backdrop-blur-md space-y-3 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl -mr-10 -mt-10" />
          <p className="text-emerald-200 font-semibold text-sm tracking-wider">REVIEW AMOUNT</p>
          <p className="text-5xl font-black text-white">{formatCurrency(reviewAmount)}</p>
          <p className="text-gray-400 text-sm font-medium">Sum of flagged charge amounts</p>
        </motion.div>
      </div>

      {/* ─── Findings + Bills ─── */}
      <div className="grid md:grid-cols-2 gap-8">
        {/* Recent findings */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2 text-white">
            <AlertCircle className="w-5 h-5 text-orange-500" /> RECENT FINDINGS
          </h2>
          <div className="grid gap-4">
            {data.allFindings.length === 0 && (
              <p className="text-gray-500">No findings yet — upload a bill to see results.</p>
            )}
            {data.allFindings.slice(0, 5).map((finding: any, idx: number) => (
              <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.1 }} key={finding.finding_id}>
                <Link href={`/investigate/${finding.bill_id}`}>
                  <div className="p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-orange-500/50 hover:bg-white/10 transition-all flex justify-between items-center group backdrop-blur-sm">
                    <div className="flex items-center gap-4">
                      <div className={`w-3 h-3 rounded-full shadow-[0_0_10px_currentColor] ${
                        finding.priority === "HIGH" ? "bg-red-500 text-red-500" :
                        finding.priority === "MEDIUM" ? "bg-orange-500 text-orange-500" : "bg-yellow-500 text-yellow-500"
                      }`} />
                      <div>
                        <p className="font-bold text-gray-200 group-hover:text-white">{finding.title}</p>
                        <p className="text-sm text-gray-500 group-hover:text-gray-300 transition-colors line-clamp-1">{finding.description}</p>
                      </div>
                    </div>
                    {finding.amount != null && (
                      <p className="font-mono font-bold text-lg text-white whitespace-nowrap">{formatCurrency(finding.amount)}</p>
                    )}
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Recent bills */}
        <div className="space-y-6">
          <h2 className="text-xl font-bold flex items-center gap-2 text-white justify-between">
            <div className="flex items-center gap-2"><FileText className="w-5 h-5 text-blue-500" /> RECENT BILLS</div>
            <Link href="/history" className="text-sm font-medium text-blue-400 hover:text-blue-300 flex items-center">View all <ChevronRight className="w-4 h-4" /></Link>
          </h2>
          <div className="grid gap-4">
            {data.uploadedBills.slice(0, 3).map((bill: any, idx: number) => (
              <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: idx * 0.1 }} key={bill.bill_id}>
                <Link href={`/bills/${bill.bill_id}`}>
                  <div className="p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-blue-500/50 hover:bg-white/10 flex justify-between items-center transition-all group backdrop-blur-sm">
                    <div>
                      <p className="font-bold text-lg text-gray-200 group-hover:text-white">{bill.provider}</p>
                      <p className="text-gray-500 text-sm capitalize group-hover:text-gray-300 transition-colors">
                        {bill.bill_type}
                        {bill.billing_period ? ` • ${bill.billing_period.start_date} to ${bill.billing_period.end_date}` : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-xl text-white">{formatCurrency(bill.total)}</p>
                      {bill.due_date && <p className="text-sm text-gray-500">Due {bill.due_date}</p>}
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
