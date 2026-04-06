"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Navbar from "./Navbar";
import { useAuth } from "@/hooks/useAuth";
import { LayoutDashboard, Users, Upload, SlidersHorizontal, GitCompareArrows, MessageCircle, Heart, FileDown, BrainCircuit, UserCircle, Sparkles, Settings } from "lucide-react";

const recruiterNav = [
  { href: "/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/criteria", label: "Définir critères", icon: SlidersHorizontal },
  { href: "/ideal-profile", label: "Profil idéal", icon: Sparkles },
  { href: "/matching", label: "Résultats matching", icon: GitCompareArrows },
  { href: "/candidates", label: "Explorer candidats", icon: Users },
  { href: "/chatbot", label: "Chatbot IA", icon: MessageCircle },
  { href: "/shortlist", label: "Shortlist", icon: Heart },
  { href: "/export", label: "Export", icon: FileDown },
  { href: "/settings", label: "Paramètres", icon: Settings },
];

const candidateNav = [
  { href: "/candidate/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/candidate/upload", label: "Upload CV", icon: Upload },
  { href: "/candidate/profile", label: "Mon profil", icon: UserCircle },
  { href: "/settings", label: "Paramètres", icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isCandidate } = useAuth();
  const nav = isCandidate ? candidateNav : recruiterNav;
  return (
    <div className="flex h-screen" style={{ background: "var(--bg)" }}>
      <aside className="hidden lg:flex w-64 flex-col" style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}>
        <div className="h-16 flex items-center gap-2 px-6" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
          <BrainCircuit className="h-7 w-7 text-indigo-600" />
          <span className="font-bold text-lg" style={{ color: "var(--text-primary)" }}>AI Talent Finder</span>
        </div>
        <div className="px-4 pt-4 pb-2">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${isCandidate ? "bg-emerald-100 text-emerald-700" : "bg-indigo-100 text-indigo-700"}`}>
            {isCandidate ? "Espace Candidat" : "Espace Recruteur"}
          </span>
        </div>
        <nav className="flex-1 py-2 px-3 space-y-1 overflow-y-auto">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link key={href} href={href} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
                style={{ background: active ? "var(--sidebar-active-bg)" : "transparent", color: active ? "var(--sidebar-active-text)" : "var(--sidebar-text)" }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = "var(--sidebar-hover)"; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}>
                <Icon className="h-5 w-5 flex-shrink-0" />{label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
