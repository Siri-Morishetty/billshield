"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, ChevronRight, MessageSquare, ExternalLink, Bot, X } from "lucide-react";
import { investigateBill, getBill, formatCurrency } from "@/lib/api";

const STEPS = [
  { key: "get_bill", label: "Retrieved current bill" },
  { key: "get_history", label: "Retrieved previous bills" },
  { key: "compare", label: "Compared line items" },
  { key: "validate", label: "Validated calculations" },
  { key: "anomalies", label: "Detected anomalies" },
  { key: "evidence", label: "Retrieved evidence" },
  { key: "explanation", label: "Generated explanation" },
];

export default function InvestigatePage() {
  const params = useParams();
  const router = useRouter();
  const billId = params.id as string;

  const [bill, setBill] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);
  const [showClarification, setShowClarification] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!billId || billId === "undefined") {
      router.replace("/dashboard");
      return;
    }

    getBill(billId).then((b) => {
      if (!b) {
        setError("Bill not found.");
        return;
      }
      setBill(b);
    });

    // Animate agent steps
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STEPS.length) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, 700);
    return () => clearInterval(interval);
  }, [billId, router]);

  // After all steps animate, call the real API
  useEffect(() => {
    if (currentStep >= STEPS.length && !result && !error && billId) {
      investigateBill(billId)
        .then(setResult)
        .catch(() => setError("Investigation failed. Please try again."));
    }
  }, [currentStep, result, error, billId]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <p className="text-red-400 text-lg">{error}</p>
        <Link href="/dashboard" className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold">← Back to Dashboard</Link>
      </div>
    );
  }

  if (!bill) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400 font-medium">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        <ChevronRight className="w-4 h-4" />
        <Link href={`/bills/${bill.bill_id}`} className="hover:text-white">Bill Details</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white">Investigate</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-800 pb-6">
        <Bot className="w-10 h-10 text-blue-500" />
        <div>
          <h1 className="text-2xl font-bold">BILL INVESTIGATOR</h1>
          <p className="text-gray-400">Analyzing {bill.provider} {bill.bill_type} bill · {formatCurrency(bill.total)}</p>
        </div>
      </div>

      {/* Agent activity steps */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-3">
        <p className="text-xs text-gray-600 font-mono uppercase tracking-widest mb-4">Agent Execution Log</p>
        {STEPS.map((step, idx) => (
          <div
            key={step.key}
            className={`flex items-center gap-3 transition-all duration-500 ${idx < currentStep ? "opacity-100" : "opacity-0"}`}
          >
            <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
            <span className="font-mono text-sm text-gray-300">
              <span className="text-green-400">{step.key}()</span> → {step.label}
            </span>
          </div>
        ))}
        {currentStep < STEPS.length && (
          <div className="flex items-center gap-3 opacity-60">
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
            <span className="font-mono text-sm text-blue-300">{STEPS[currentStep]?.label}...</span>
          </div>
        )}
      </div>

      {/* Investigation results */}
      {result && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
          {/* Explanation */}
          <div className="bg-blue-900/20 border border-blue-800/50 rounded-xl p-5 text-blue-100 font-medium whitespace-pre-wrap text-sm leading-relaxed">
            {result.explanation}
          </div>

          {/* Findings */}
          {result.findings && result.findings.length > 0 && (
            <div className="space-y-4">
              <h2 className="font-bold text-lg">Findings ({result.findings.length})</h2>
              {result.findings.map((f: any) => {
                const evidence = result.evidence?.find((e: any) => e.evidence_id === f.finding_id);
                return (
                  <div key={f.finding_id} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`px-2 py-1 text-xs font-bold rounded-md ${
                          f.priority === "HIGH" ? "bg-red-500/20 text-red-400" :
                          f.priority === "MEDIUM" ? "bg-orange-500/20 text-orange-400" : "bg-yellow-500/20 text-yellow-400"
                        }`}>
                          {f.priority}
                        </div>
                        <h3 className="font-bold text-lg">{f.title}</h3>
                      </div>
                      {f.amount != null && (
                        <span className="font-mono text-xl">{formatCurrency(f.amount)}</span>
                      )}
                    </div>

                    <p className="text-gray-400">{f.description}</p>

                    <div className="flex flex-wrap gap-3 pt-4 border-t border-gray-800">
                      {evidence && (
                        <button
                          onClick={() => setSelectedEvidence(evidence)}
                          className="flex items-center gap-2 text-sm font-medium bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" /> Show Evidence
                        </button>
                      )}
                      <button
                        onClick={() => setShowClarification(f)}
                        className="flex items-center gap-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" /> What should I ask?
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Questions */}
          {result.questions && result.questions.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-3">
              <h3 className="font-bold">Suggested Questions</h3>
              <ul className="space-y-2">
                {result.questions.map((q: string, i: number) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-300">
                    <span className="text-blue-400 font-bold">Q{i + 1}.</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Evidence modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-lg w-full space-y-4 relative">
            <button onClick={() => setSelectedEvidence(null)} className="absolute top-4 right-4 text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
            <h3 className="font-bold text-lg">EVIDENCE — {selectedEvidence.title}</h3>
            <div className="space-y-3">
              <div className="bg-black rounded-lg p-4 border border-gray-800 text-sm">
                <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Source: {selectedEvidence.source}</p>
                <p className="text-white">{selectedEvidence.current_bill_text}</p>
              </div>
              <div className="bg-black rounded-lg p-4 border border-gray-800 text-sm">
                <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Historical Check</p>
                <p className="text-white">{selectedEvidence.historical_check}</p>
              </div>
              {selectedEvidence.amount != null && (
                <div className="bg-orange-900/20 border border-orange-500/30 rounded-lg p-3 text-sm">
                  <span className="text-orange-400 font-bold">Amount flagged: {formatCurrency(selectedEvidence.amount)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Clarification modal */}
      {showClarification && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 animate-in fade-in">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-lg w-full space-y-4 relative">
            <button onClick={() => setShowClarification(null)} className="absolute top-4 right-4 text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
            <h3 className="font-bold text-lg">Clarification Message</h3>
            <p className="text-gray-400 text-sm">Edit this message and copy it to contact your provider.</p>
            <div
              className="p-4 bg-black border border-gray-700 rounded-lg text-gray-200 text-sm leading-relaxed"
              contentEditable
              suppressContentEditableWarning
            >
              {`Hello,\n\nI noticed a ${formatCurrency(showClarification.amount)} charge for "${showClarification.description?.split("'")[1] ?? showClarification.title}" on my recent ${bill.bill_type} bill that was not present on my previous bill. Could you please clarify when this was added and what it covers?\n\nThank you.`}
            </div>
            <button
              onClick={() => {
                const el = document.querySelector('[contenteditable="true"]');
                if (el) navigator.clipboard.writeText(el.textContent || "");
              }}
              className="bg-white text-black hover:bg-gray-200 px-4 py-2 rounded-lg font-bold text-sm"
            >
              Copy Message
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
