"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck, Search, Activity, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[85vh] text-center px-4 relative overflow-hidden">
      
      {/* Background glow effects */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="space-y-8 max-w-4xl relative z-10"
      >
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 text-sm font-semibold mb-4 backdrop-blur-md">
          <Sparkles className="w-4 h-4" /> 
          Award Winning Financial Intelligence
        </div>

        <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-[1.1]">
          Don't just read your bill.
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400">Verify it.</span>
        </h1>
        
        <p className="text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto font-light leading-relaxed">
          Verify calculations automatically. Understand historical changes instantly. Investigate anomalies with AI.
        </p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="flex gap-4 mt-12 relative z-10"
      >
        <Link 
          href="/upload" 
          className="group relative inline-flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white px-10 py-5 rounded-full font-bold text-lg shadow-[0_0_40px_rgba(59,130,246,0.5)] transition-all hover:scale-105 hover:shadow-[0_0_60px_rgba(59,130,246,0.7)]"
        >
          Upload Your First Bill 
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </Link>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.8 }}
        className="grid md:grid-cols-3 gap-8 text-left max-w-5xl mt-24 relative z-10"
      >
        <div className="glass-card p-8 rounded-3xl space-y-4 hover:-translate-y-2 transition-transform duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-3xl -mr-10 -mt-10 group-hover:bg-green-500/20 transition-colors"></div>
          <ShieldCheck className="w-10 h-10 text-green-400" />
          <h3 className="text-2xl font-bold text-white">VERIFY</h3>
          <p className="text-gray-400 leading-relaxed">Is the bill mathematically consistent? We check every line item, subtotal, and tax mathematically.</p>
        </div>
        <div className="glass-card p-8 rounded-3xl space-y-4 hover:-translate-y-2 transition-transform duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl -mr-10 -mt-10 group-hover:bg-blue-500/20 transition-colors"></div>
          <Activity className="w-10 h-10 text-blue-400" />
          <h3 className="text-2xl font-bold text-white">UNDERSTAND</h3>
          <p className="text-gray-400 leading-relaxed">What changed compared with your history? Spot new recurring charges and unusual usage instantly.</p>
        </div>
        <div className="glass-card p-8 rounded-3xl space-y-4 hover:-translate-y-2 transition-transform duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl -mr-10 -mt-10 group-hover:bg-purple-500/20 transition-colors"></div>
          <Search className="w-10 h-10 text-purple-400" />
          <h3 className="text-2xl font-bold text-white">INVESTIGATE</h3>
          <p className="text-gray-400 leading-relaxed">What deserves your attention? Our AI agent grounds every finding in exact documentary evidence.</p>
        </div>
      </motion.div>
    </div>
  );
}
