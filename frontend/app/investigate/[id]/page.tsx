"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import {
  CheckCircle2, ChevronRight, MessageSquare, ExternalLink,
  Bot, X, Sparkles, Database, AlertTriangle, ShieldCheck
} from "lucide-react";
import { investigateBill, getBill, formatCurrency } from "@/lib/api";
import { Bill, InvestigationResult, EvidenceItem, Finding } from "@/lib/types";

const STEPS = [
  { key: "get_bill",     label: "Retrieved bill",           detail: "Loading bill data" },
  { key: "get_history",  label: "Retrieved history",        detail: "Finding previous bills for this provider" },
  { key: "compare",      label: "Compared charges",         detail: "Checking for price and quantity changes" },
  { key: "validate",     label: "Validated calculations",   detail: "Verifying arithmetic, subtotals, totals" },
  { key: "anomalies",    label: "Detected anomalies",       detail: "Identifying new and unusual charges" },
  { key: "evidence",     label: "Assembled evidence",       detail: "Building documentary evidence for each finding" },
  { key: "explanation",  label: "Generated explanation",    detail: "Composing investigation report" },
];

function SeverityChip({ priority }: { priority: string }) {
  const cfg = {
    HIGH:   "bg-red-500/20 text-red-400 border-red-500/30",
    MEDIUM: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    LOW:    "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  }[priority] ?? "bg-gray-500/20 text-gray-400 border-gray-500/30";
  return (
    <span className={`inline-flex text-xs font-bold px-2.5 py-1 rounded-full border ${cfg}`}>
      {priority}
    </span>
  );
}

function EvidenceModal({ evidence, onClose }: { evidence: EvidenceItem; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-950 border border-gray-800 rounded-2xl p-6 max-w-lg w-full space-y-4 relative shadow-2xl">
        <button
          onClick={onClose}
          aria-label="Close evidence"
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
        <h3 className="font-bold text-lg pr-8">Evidence: {evidence.title}</h3>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Source: {evidence.source}</p>

        <div className="space-y-3">
          <div className="bg-black rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Current Bill</p>
            <p className="text-gray-200 text-sm">{evidence.current_bill_text}</p>
          </div>
          <div className="bg-black rounded-xl p-4 border border-gray-800">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Historical Check</p>
            <p className="text-gray-200 text-sm">{evidence.historical_check}</p>
          </div>
          {evidence.amount != null && (
            <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-3">
              <span className="text-orange-400 font-bold text-sm">
                Amount flagged: {formatCurrency(evidence.amount)}
              </span>
              {evidence.percentage_change != null && (
                <span className="text-orange-400 text-sm ml-3">
                  ({evidence.percentage_change > 0 ? "+" : ""}{evidence.percentage_change.toFixed(1)}%)
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ClarificationModal({ finding, bill, onClose }: { finding: Finding; bill: Bill; onClose: () => void }) {
  const amountStr = finding.amount != null ? formatCurrency(finding.amount) : "";
  const ev = finding.evidence as Record<string, unknown> | null;
  const itemName = (ev?.description as string) ?? finding.title;
  const defaultMsg = finding.type === "NEW_CHARGE"
    ? `Hello,\n\nI noticed a ${amountStr} charge for "${itemName}" on my recent ${bill.bill_type} bill that was not present on my previous bill.\n\nCould you please clarify:\n1. When was this charge added?\n2. What does it cover?\n3. Is it mandatory?\n\nThank you.`
    : finding.type === "PRICE_INCREASE"
    ? `Hello,\n\nI noticed the price for "${itemName}" increased to ${formatCurrency((ev?.current_price as number) ?? 0)} from ${formatCurrency((ev?.previous_price as number) ?? 0)} on my recent bill.\n\nCould you please explain this price change and whether a notice was sent?\n\nThank you.`
    : `Hello,\n\nI have a query about my recent ${bill.bill_type} bill regarding: ${finding.title}.\n\n${finding.description}\n\nCould you please clarify this?\n\nThank you.`;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-gray-950 border border-gray-800 rounded-2xl p-6 max-w-lg w-full space-y-4 relative shadow-2xl">
        <button onClick={onClose} aria-label="Close" className="absolute top-4 right-4 text-gray-400 hover:text-white">
          <X className="w-5 h-5" />
        </button>
        <h3 className="font-bold text-lg pr-8">Clarification Message</h3>
        <p className="text-gray-500 text-sm">Edit and copy this message to contact your provider.</p>
        <div
          className="p-4 bg-black border border-gray-700 rounded-xl text-gray-200 text-sm leading-relaxed whitespace-pre-wrap min-h-[120px]"
          contentEditable
          suppressContentEditableWarning
          id="clarification-text"
        >
          {defaultMsg}
        </div>
        <button
          onClick={() => {
            const el = document.getElementById("clarification-text");
            if (el) navigator.clipboard.writeText(el.textContent || "");
          }}
          className="bg-white text-black hover:bg-gray-100 px-4 py-2 rounded-xl font-bold text-sm transition-colors"
        >
          Copy Message
        </button>
      </div>
    </div>
  );
}

export default function InvestigatePage() {
  const params = useParams();
  const router = useRouter();
  const billId = params.id as string;

  const [bill, setBill] = useState<Bill | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<InvestigationResult | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);
  const [clarificationFinding, setClarificationFinding] = useState<Finding | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!billId || billId === "undefined") {
      router.replace("/dashboard");
      return;
    }
    getBill(billId).then((b) => {
      if (!b) { setError("Bill not found."); return; }
      setBill(b);
    });

    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= STEPS.length) { clearInterval(interval); return prev; }
        return prev + 1;
      });
    }, 600);
    return () => clearInterval(interval);
  }, [billId, router]);

  useEffect(() => {
    if (currentStep >= STEPS.length && !result && !error && billId) {
      investigateBill(billId)
        .then(setResult)
        .catch((e) => setError(e.message ?? "Investigation failed."));
    }
  }, [currentStep, result, error, billId]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <AlertTriangle className="w-12 h-12 text-red-400" />
        <p className="text-red-400 text-lg font-semibold">{error}</p>
        <Link href="/dashboard" className="bg-blue-600 text-white px-6 py-3 rounded-xl font-bold">
          ← Back to Dashboard
        </Link>
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
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Link href="/dashboard" className="hover:text-white">Dashboard</Link>
        <ChevronRight className="w-4 h-4" />
        <Link href={`/bills/${bill.bill_id}`} className="hover:text-white">{bill.provider}</Link>
        <ChevronRight className="w-4 h-4" />
        <span className="text-white">Investigate</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-4 border-b border-gray-800 pb-6">
        <div className="bg-blue-500/10 p-3 rounded-2xl">
          <Bot className="w-8 h-8 text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold">Bill Investigator</h1>
          <p className="text-gray-400 text-sm">{bill.provider} · {bill.bill_type} · {formatCurrency(bill.total)}</p>
        </div>
      </div>

      {/* Agent execution log */}
      <div className="bg-gray-950 border border-gray-800 rounded-2xl p-6 space-y-3">
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
          <div className="flex items-center gap-3 opacity-70">
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
            <span className="font-mono text-sm text-blue-300">{STEPS[currentStep]?.label}...</span>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Explanation source badge */}
          <div className="flex items-center gap-3">
            {result.explanation_source === "amazon_bedrock" ? (
              <div className="flex items-center gap-2 text-sm bg-green-500/10 border border-green-500/20 px-4 py-2 rounded-full text-green-400 font-semibold">
                <Sparkles className="w-4 h-4" />
                Explanation by Amazon Bedrock (Claude 3)
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm bg-blue-500/10 border border-blue-500/20 px-4 py-2 rounded-full text-blue-400 font-semibold">
                <Database className="w-4 h-4" />
                Deterministic explanation (no AI inference used)
              </div>
            )}
          </div>

          {/* Summary */}
          <div className={`rounded-xl p-5 border text-sm leading-relaxed ${
            result.findings.length === 0
              ? "bg-green-500/5 border-green-500/20 text-green-200"
              : "bg-blue-900/10 border-blue-800/30 text-blue-100"
          }`}>
            {result.findings.length === 0 ? (
              <div className="flex items-center gap-3">
                <ShieldCheck className="w-6 h-6 text-green-400 flex-shrink-0" />
                <p className="font-semibold">{result.summary}</p>
              </div>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown>{result.explanation}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* Findings with evidence */}
          {result.findings.length > 0 && (
            <div className="space-y-4">
              <h2 className="font-bold text-xl text-white">
                Findings ({result.findings.length})
              </h2>
              {result.findings.map((f: Finding) => {
                const evidence = result.evidence.find((e: EvidenceItem) => e.evidence_id === f.finding_id);
                return (
                  <div
                    key={f.finding_id}
                    className={`bg-gray-950 border rounded-2xl p-6 space-y-4 ${
                      f.priority === "HIGH"   ? "border-red-500/20"
                      : f.priority === "MEDIUM" ? "border-orange-500/20"
                      : "border-gray-800"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <SeverityChip priority={f.priority} />
                        <div>
                          <h3 className="font-bold text-white">{f.title}</h3>
                          <p className="text-gray-400 text-sm mt-1">{f.description}</p>
                        </div>
                      </div>
                      {f.amount != null && (
                        <span className="font-mono font-bold text-xl text-white flex-shrink-0">
                          {formatCurrency(f.amount)}
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-3 pt-3 border-t border-gray-800">
                      {evidence && (
                        <button
                          id={`btn-evidence-${f.finding_id}`}
                          onClick={() => setSelectedEvidence(evidence)}
                          className="flex items-center gap-2 text-sm font-semibold bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-xl transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" /> View Evidence
                        </button>
                      )}
                      <button
                        id={`btn-clarify-${f.finding_id}`}
                        onClick={() => setClarificationFinding(f)}
                        className="flex items-center gap-2 text-sm font-semibold bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 px-4 py-2 rounded-xl border border-blue-600/30 transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" /> Draft Message
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Suggested questions */}
          {result.questions.length > 0 && (
            <div className="bg-gray-950 border border-gray-800 rounded-2xl p-6 space-y-4">
              <h3 className="font-bold text-white">Questions to Ask Your Provider</h3>
              <ul className="space-y-2">
                {result.questions.map((q: string, i: number) => (
                  <li key={i} className="flex gap-3 text-sm text-gray-300">
                    <span className="text-blue-400 font-bold flex-shrink-0">Q{i + 1}.</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Historical comparison summary */}
          {result.comparison.previous_total > 0 && (
            <div className="bg-gray-950 border border-gray-800 rounded-2xl p-6 space-y-3">
              <h3 className="font-bold text-white">Historical Comparison</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500 text-xs mb-1">Previous</p>
                  <p className="font-mono font-bold text-white">{formatCurrency(result.comparison.previous_total)}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Current</p>
                  <p className="font-mono font-bold text-white">{formatCurrency(result.comparison.current_total)}</p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs mb-1">Change</p>
                  <p className={`font-mono font-bold ${result.comparison.absolute_difference > 0 ? "text-red-400" : "text-green-400"}`}>
                    {result.comparison.absolute_difference > 0 ? "+" : ""}
                    {formatCurrency(result.comparison.absolute_difference)}
                    {" "}({result.comparison.percentage_difference.toFixed(1)}%)
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {selectedEvidence && (
        <EvidenceModal evidence={selectedEvidence} onClose={() => setSelectedEvidence(null)} />
      )}
      {clarificationFinding && bill && (
        <ClarificationModal
          finding={clarificationFinding}
          bill={bill}
          onClose={() => setClarificationFinding(null)}
        />
      )}
    </div>
  );
}
