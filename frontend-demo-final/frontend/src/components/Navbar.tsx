"use client";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import { LogOut, User, BrainCircuit, Moon, Sun } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <header className="h-16 flex items-center justify-between px-6 sticky top-0 z-30" style={{ background: "var(--bg-card)", borderBottom: "1px solid var(--border)" }}>
      <div className="flex items-center gap-2 lg:hidden">
        <BrainCircuit className="h-6 w-6 text-indigo-600" />
        <span className="font-bold text-lg" style={{ color: "var(--text-primary)" }}>AI Talent Finder</span>
      </div>
      <div className="flex-1" />
      <div className="flex items-center gap-4">
        <button onClick={toggleTheme} className="p-2 rounded-lg text-gray-500 hover:text-indigo-600 transition-colors" style={{ background: "var(--bg-hover)" }}>
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <div className="flex items-center gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          <User className="h-4 w-4" />
          <span>{user?.full_name ?? "Utilisateur"}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${user?.role === "candidate" ? "bg-emerald-100 text-emerald-700" : "bg-indigo-100 text-indigo-700"}`}>
            {user?.role === "candidate" ? "Candidat" : "Recruteur"}
          </span>
        </div>
        <button onClick={logout} className="flex items-center gap-1 text-sm hover:text-red-500 transition-colors" style={{ color: "var(--text-muted)" }}>
          <LogOut className="h-4 w-4" /><span className="hidden sm:inline">Déconnexion</span>
        </button>
      </div>
    </header>
  );
}
