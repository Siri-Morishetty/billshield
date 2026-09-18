import Link from "next/link";
import { ChevronRight, History } from "lucide-react";
import { getBills, formatCurrency } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const bills = await getBills();

  // Filter out the seeded historical bill from the display list
  // (users only see bills they uploaded)
  const uploadedBills = bills.filter((b) => b.bill_id !== "bill-jul-001");

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in zoom-in duration-500">
      <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white">Financial History</span>
      </div>

      <div className="flex items-center gap-3 border-b border-white/10 pb-6">
        <History className="w-10 h-10 text-purple-500" />
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">Bill History</h1>
          <p className="text-gray-400">Review your past financial documents</p>
        </div>
      </div>

      {uploadedBills.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p className="text-lg">No bills uploaded yet.</p>
          <Link href="/upload" className="text-blue-400 hover:text-blue-300 mt-2 inline-block">Upload your first bill →</Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {uploadedBills.map((bill) => (
            <Link href={`/bills/${bill.bill_id}`} key={bill.bill_id}>
              <div className="p-5 rounded-xl bg-white/5 backdrop-blur-md border border-white/10 hover:border-purple-500/50 hover:bg-white/10 flex justify-between items-center transition-all group">
                <div>
                  <p className="font-bold text-lg text-white group-hover:text-purple-300 transition-colors">{bill.provider}</p>
                  <p className="text-gray-400 text-sm capitalize">
                    {bill.bill_type}
                    {bill.billing_period ? ` • ${bill.billing_period.start_date} to ${bill.billing_period.end_date}` : ""}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-xl text-white">{formatCurrency(bill.total)}</p>
                  {bill.issue_date && <p className="text-sm text-gray-400">Issued {bill.issue_date}</p>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
