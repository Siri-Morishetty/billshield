"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, Shield, Sparkles, AlertTriangle, Download } from "lucide-react";
import { useRouter } from "next/navigation";
import { processUploadedBill } from "@/lib/api";

type UploadStatus = "IDLE" | "READING" | "PARSING" | "ANALYZING" | "DONE" | "ERROR";

const STEPS = [
  { key: "READING",   label: "Reading document",             detail: "Validating file format and size" },
  { key: "PARSING",   label: "Extracting bill information",  detail: "Parsing line items, totals, and dates" },
  { key: "ANALYZING", label: "Running deterministic checks", detail: "Checking arithmetic, totals, and history" },
  { key: "DONE",      label: "Analysis complete",            detail: "Redirecting to results..." },
];

function stepIndex(status: UploadStatus): number {
  return STEPS.findIndex((s) => s.key === status);
}

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [status, setStatus] = useState<UploadStatus>("IDLE");
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [extractionMode, setExtractionMode] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  const checkBackend = useCallback(() => {
    fetch("http://localhost:8000/api/health")
      .then((res) => setIsBackendOnline(res.ok))
      .catch(() => setIsBackendOnline(false));
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  const handleFile = useCallback(async (file: File) => {
    setErrorMsg(null);

    // Client-side validation
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "json", "png", "jpg", "jpeg"].includes(ext || "")) {
      setErrorMsg(`Unsupported format: .${ext}. Please upload PDF, JSON, PNG, or JPG.`);
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg("File too large. Maximum size is 10 MB.");
      return;
    }

    setFileName(file.name);
    setFileSize((file.size / 1024).toFixed(1) + " KB");

    try {
      setStatus("READING");
      await delay(500);

      setStatus("PARSING");
      const result = await processUploadedBill(file);

      setExtractionMode(result.extraction_mode);
      setStatus("ANALYZING");
      await delay(600);

      setStatus("DONE");
      await delay(600);

      // Navigate to the specific bill's results
      router.push(`/bills/${result.bill_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setErrorMsg(msg);
      setStatus("ERROR");
      checkBackend();
    }
  }, [router, checkBackend]);

  const handleLoadSamplePdf = async () => {
    try {
      setErrorMsg(null);
      const res = await fetch("/BillShield_Sample_August_Bill.pdf");
      if (!res.ok) throw new Error("Could not load sample PDF asset");
      const blob = await res.blob();
      const file = new File([blob], "BillShield_Sample_August_Bill.pdf", { type: "application/pdf" });
      handleFile(file);
    } catch (err: unknown) {
      setErrorMsg("Failed to load sample PDF: " + (err instanceof Error ? err.message : String(err)));
      setStatus("ERROR");
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);

  const currentStepIdx = stepIndex(status);
  const isProcessing = ["READING", "PARSING", "ANALYZING"].includes(status);

  return (
    <div className="max-w-2xl mx-auto space-y-8 pt-6">
      <div className="text-center space-y-2">
        <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
          Upload Your Bill
        </h1>
        <p className="text-gray-400 text-lg">
          PDF & JSON supported in local mode. PNG/JPG require AWS Textract.
        </p>
      </div>

      {/* Backend connection warning if offline */}
      {isBackendOnline === false && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold text-amber-300">Backend Server Offline (port 8000)</p>
              <p className="text-xs text-amber-400/80">
                Please ensure the backend is running: <code className="bg-black/30 px-1.5 py-0.5 rounded text-amber-200">.\venv\Scripts\python.exe -m uvicorn src.main:app --port 8000</code>
              </p>
            </div>
          </div>
          <button
            onClick={checkBackend}
            className="text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 px-3 py-2 rounded-xl font-semibold transition-colors flex-shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* 1-Click Sample PDF Test Bar */}
      <div className="bg-gradient-to-r from-blue-900/30 to-indigo-900/30 border border-blue-500/30 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-500/20 text-blue-400 flex-shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-bold text-white">Need a test bill file?</p>
            <p className="text-xs text-blue-300/80">Test live PDF parsing & extraction with our sample August bill.</p>
          </div>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <a
            href="/BillShield_Sample_August_Bill.pdf"
            download="BillShield_Sample_August_Bill.pdf"
            className="text-xs text-gray-300 hover:text-white px-3 py-2 rounded-xl border border-gray-700 hover:border-gray-500 transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Download PDF
          </a>
          <button
            type="button"
            onClick={handleLoadSamplePdf}
            disabled={status !== "IDLE"}
            className="text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 px-4 py-2 rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center gap-1.5"
          >
            ⚡ Test With Sample PDF
          </button>
        </div>
      </div>

      <input
        type="file"
        className="hidden"
        ref={fileInputRef}
        onChange={handleInputChange}
        accept=".pdf,.json,.png,.jpg,.jpeg"
        aria-label="Bill file upload"
      />

      {/* Drop zone */}
      <div
        id="upload-dropzone"
        role="button"
        tabIndex={0}
        aria-label="Drag and drop your bill here or click to select"
        onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && status === "IDLE") fileInputRef.current?.click(); }}
        onClick={() => status === "IDLE" && fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative border-2 border-dashed rounded-3xl p-14 text-center transition-all duration-300
          ${status === "IDLE"
            ? isDragging
              ? "border-blue-400 bg-blue-500/10 scale-105 cursor-copy"
              : "border-blue-500/50 hover:border-blue-400 hover:bg-blue-500/5 cursor-pointer bg-white/5"
            : "border-gray-800 bg-black/30 cursor-default"
          }
        `}
      >
        <UploadCloud className={`w-16 h-16 mx-auto mb-5 transition-colors ${isDragging ? "text-blue-400" : status === "IDLE" ? "text-blue-500/70" : "text-gray-700"}`} />
        {status === "IDLE" ? (
          <>
            <p className="font-bold text-xl text-white mb-2">Drag & Drop or Click to Select</p>
            <p className="text-gray-400 text-sm">PDF · JSON · PNG · JPG · Max 10 MB</p>
          </>
        ) : (
          <p className="font-semibold text-gray-400">{fileName}</p>
        )}
        {isDragging && (
          <div className="absolute inset-0 rounded-3xl border-2 border-blue-400 bg-blue-400/5 flex items-center justify-center pointer-events-none">
            <p className="text-blue-300 font-bold text-xl">Drop to upload</p>
          </div>
        )}
      </div>

      {/* Processing progress */}
      {status !== "IDLE" && status !== "ERROR" && (
        <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 space-y-5">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500/10 p-2 rounded-lg">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="font-semibold text-white">{fileName}</p>
              {fileSize && <p className="text-xs text-gray-500">{fileSize}</p>}
            </div>
          </div>

          <div className="space-y-3">
            {STEPS.map((step, idx) => {
              const done = currentStepIdx > idx || status === "DONE";
              const active = currentStepIdx === idx && isProcessing;
              return (
                <div key={step.key} className={`flex items-center gap-4 transition-all duration-500 ${idx <= currentStepIdx || status === "DONE" ? "opacity-100" : "opacity-30"}`}>
                  {done ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                  ) : active ? (
                    <Loader2 className="w-5 h-5 text-blue-400 animate-spin flex-shrink-0" />
                  ) : (
                    <div className="w-5 h-5 rounded-full border-2 border-gray-700 flex-shrink-0" />
                  )}
                  <div>
                    <p className={`font-medium text-sm ${done ? "text-white" : active ? "text-blue-300" : "text-gray-600"}`}>
                      {step.label}
                    </p>
                    {active && <p className="text-xs text-gray-500">{step.detail}</p>}
                  </div>
                </div>
              );
            })}
          </div>

          {extractionMode && (
            <div className="pt-2 border-t border-white/10">
              <span className={`text-xs px-2 py-1 rounded font-mono ${
                extractionMode === "textract"
                  ? "bg-green-500/10 text-green-400"
                  : extractionMode === "local_fallback"
                  ? "bg-yellow-500/10 text-yellow-400"
                  : "bg-blue-500/10 text-blue-400"
              }`}>
                {extractionMode === "textract"
                  ? "✓ Extracted via AWS Textract"
                  : extractionMode === "local_fallback"
                  ? "⚠ Local fallback (Textract unavailable)"
                  : "✓ Extracted locally (demo mode)"}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error state */}
      {status === "ERROR" && errorMsg && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 flex gap-4 items-start">
          <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-red-300">Upload Failed</p>
            <p className="text-red-400/80 text-sm mt-1">{errorMsg}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                onClick={() => { setStatus("IDLE"); setErrorMsg(null); setFileName(null); }}
                className="text-sm font-bold text-red-300 hover:text-white underline"
              >
                Try again
              </button>
              <button
                type="button"
                onClick={handleLoadSamplePdf}
                className="text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg shadow transition-colors flex items-center gap-1"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Test with Sample PDF instead
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info note */}
      {status === "IDLE" && (
        <div className="flex gap-3 text-sm text-gray-500 bg-white/3 rounded-xl p-4 border border-white/5">
          <Shield className="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" />
          <p>
            In <strong className="text-gray-400">local/demo mode</strong>, bills are parsed using pdfplumber.
            Configure AWS credentials and set <code className="text-blue-400">USE_MOCK_AWS=false</code> to enable
            Amazon Textract for real OCR on scanned PDFs and images.
          </p>
        </div>
      )}
    </div>
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((res) => setTimeout(res, ms));
}
