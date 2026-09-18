import Link from 'next/link';
import { Shield } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-white/5 bg-black/50 backdrop-blur-xl">
      <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
        <Link href="/dashboard" className="flex items-center gap-3 text-2xl font-black tracking-tighter">
          <div className="bg-blue-500 p-1.5 rounded-lg">
            <Shield className="w-6 h-6 text-black" fill="currentColor" />
          </div>
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">BillShield</span>
        </Link>
        <div className="flex gap-8 items-center text-sm font-bold text-gray-400 tracking-wide">
          <Link href="/dashboard" className="hover:text-white transition-colors">Dashboard</Link>
          <Link href="/upload" className="hover:text-white transition-colors">Upload</Link>
          <Link href="/history" className="hover:text-white transition-colors">History</Link>
        </div>
      </div>
    </nav>
  );
}
