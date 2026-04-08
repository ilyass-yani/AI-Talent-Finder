"use client";
import Link from "next/link";
import { useTheme } from "@/hooks/useTheme";
import { BrainCircuit, Moon, Sun } from "lucide-react";
export default function Navbar() {
  const { theme, toggleTheme } = useTheme();
  return <header className="h-16 flex items-center justify-between px-6 sticky top-0 z-30" style={{ background:"var(--bg-card)", borderBottom:"1px solid var(--border)" }}>
    <Link href="/" className="flex items-center gap-2 lg:hidden"><BrainCircuit className="h-6 w-6 text-indigo-600" /><span className="font-bold text-lg" style={{color:"var(--text-primary)"}}>AI Talent Finder</span></Link>
    <div className="flex-1" />
    <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-500 hover:text-indigo-600 transition-colors" style={{background:"var(--bg-hover)"}}>
      {theme==="dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  </header>;
}
