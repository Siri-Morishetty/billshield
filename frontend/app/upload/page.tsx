"use client";

import { useState, useRef } from "react";
import { UploadCloud, File, CheckCircle } from "lucide-react";
import { useRouter } from "next/navigation";

import { processUploadedBill } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<"IDLE" | "UPLOADING" | "ANALYZING" | "DONE">("IDLE");
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setFileName(file.name);
      startMockUpload(file);
    }
  };

  const startMockUpload = async (file: File) => {
    setStatus("UPLOADING");
    setTimeout(() => setStatus("ANALYZING"), 1500);
    
    // Call the real Python backend API
    await processUploadedBill(file);
    
    setStatus("DONE");
    setTimeout(() => {
      router.push("/dashboard");
    }, 1500);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-12 pt-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">Upload your bill</h1>
        <p className="text-gray-400 text-lg">PDF, PNG, or JPG formats supported.</p>
      </div>

      <input 
        type="file" 
        className="hidden" 
        ref={fileInputRef} 
        onChange={handleFileChange} 
        accept=".pdf,.png,.jpg,.jpeg" 
      />

      <div 
        onClick={() => status === "IDLE" && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 backdrop-blur-md ${
          status === "IDLE" ? "border-blue-500/50 hover:border-blue-400 hover:bg-blue-500/5 cursor-pointer bg-white/5 shadow-[0_0_50px_-12px_rgba(59,130,246,0.3)]" : "border-gray-800 bg-black/50 opacity-75 cursor-default"
        }`}
      >
        <UploadCloud className={`w-20 h-20 mx-auto mb-6 transition-colors ${status === 'IDLE' ? 'text-blue-500' : 'text-gray-600'}`} />
        <p className="font-semibold text-xl text-white">Drag & Drop or Choose File</p>
        {fileName && <p className="mt-4 text-sm text-blue-400 font-mono bg-blue-900/30 py-1 px-3 rounded-full inline-block">{fileName}</p>}
      </div>

      {status !== "IDLE" && (
        <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 space-y-5 border border-white/10 shadow-2xl">
          <h3 className="font-bold flex items-center gap-2 text-lg">
            <File className="w-6 h-6 text-blue-400" /> Processing {fileName || "Document"}
          </h3>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <CheckCircle className={`w-6 h-6 transition-colors ${status !== 'IDLE' ? 'text-emerald-500 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'text-gray-700'}`} />
              <span className={`text-lg font-medium transition-colors ${status !== 'IDLE' ? 'text-white' : 'text-gray-500'}`}>Uploaded successfully</span>
            </div>
            <div className="flex items-center gap-4">
              <CheckCircle className={`w-6 h-6 transition-colors ${status === 'ANALYZING' || status === 'DONE' ? 'text-emerald-500 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'text-gray-700'}`} />
              <span className={`text-lg font-medium transition-colors ${status === 'ANALYZING' || status === 'DONE' ? 'text-white' : 'text-gray-500'}`}>Extracting data with AWS Textract...</span>
            </div>
            <div className="flex items-center gap-4">
              <CheckCircle className={`w-6 h-6 transition-colors ${status === 'DONE' ? 'text-emerald-500 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'text-gray-700'}`} />
              <span className={`text-lg font-medium transition-colors ${status === 'DONE' ? 'text-white' : 'text-gray-500'}`}>Validating & generating findings...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
