import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BillShield",
  description: "Evidence-backed financial intelligence layer for everyday bills.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-black text-white min-h-screen flex flex-col`}>
        <Navbar />
        <main className="flex-1 max-w-6xl w-full mx-auto p-6">
          {children}
        </main>
      </body>
    </html>
  );
}
