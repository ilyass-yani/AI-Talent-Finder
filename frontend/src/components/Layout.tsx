"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu, X, LogOut, LayoutDashboard, Users, Upload, SlidersHorizontal,
  GitCompareArrows, MessageCircle, Heart, FileDown, BrainCircuit, BarChart3,
  UserCircle, Wrench, ChevronLeft, Moon, Sun, ShieldAlert, Briefcase,
} from "lucide-react";
import { useTheme } from "@/hooks/useTheme";

const recruiterNav = [
  { href: "/recruiter/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/candidates", label: "Candidats", icon: Users },
  { href: "/matching", label: "Critères & Matching", icon: GitCompareArrows },
  { href: "/recruiter/shortlist", label: "Shortlist", icon: Heart },
  { href: "/skills", label: "Compétences", icon: Wrench },
  { href: "/recruiter/chatbot", label: "Chatbot IA", icon: MessageCircle },
  // FeedbackAI retiree de la navigation (E1) - page disponible sur /recruiter/feedback
  { href: "/recruiter/export", label: "Export", icon: FileDown },
];

const candidateNav = [
  { href: "/candidate/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/candidate/upload", label: "Déposer mon CV", icon: Upload },
  { href: "/candidate/profile", label: "Mon profil", icon: UserCircle },
];

const adminNav = [
  { href: "/admin/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/admin/users", label: "Utilisateurs", icon: Users },
  { href: "/admin/jobs", label: "Offres", icon: Briefcase },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const [userName, setUserName] = useState<string>("");
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    setRole(localStorage.getItem("user_role"));
    setUserName(localStorage.getItem("user_name") || "");
  }, []);

  // Close mobile sidebar on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_id");
    localStorage.removeItem("user");
    router.push("/auth/login");
  };

  const isCandidate = role === "candidate";
  const isAdmin = role === "admin";
  const nav = isAdmin ? adminNav : isCandidate ? candidateNav : recruiterNav;

  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      {/* Header */}
      <div className="h-16 flex items-center gap-2.5 px-4 border-b border-gray-200 flex-shrink-0">
        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-300/40">
          <BrainCircuit className="h-5 w-5" />
        </div>
        {(sidebarOpen || mobile) && (
          <span className="font-display text-lg font-bold text-gray-900 truncate">AI Talent Finder</span>
        )}
        {mobile && (
          <button onClick={() => setMobileOpen(false)} className="ml-auto p-1 text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Role Badge */}
      {(sidebarOpen || mobile) && (
        <div className="px-4 pt-3 pb-1">
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
            isAdmin
              ? "bg-red-100 text-red-700"
              : isCandidate
              ? "bg-emerald-100 text-emerald-700"
              : "bg-indigo-100 text-indigo-700"
          }`}>
            {isAdmin && <ShieldAlert className="h-3 w-3" />}
            {isAdmin ? "Espace Admin" : isCandidate ? "Espace Candidat" : "Espace Recruteur"}
          </span>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-1 overflow-y-auto">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href + "/"));
          return (
            <Link
              key={href}
              href={href}
              title={!sidebarOpen && !mobile ? label : undefined}
              className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                active
                  ? "bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-300/40"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon className={`h-5 w-5 flex-shrink-0 transition-transform group-hover:scale-110 ${active ? "" : "text-gray-400 group-hover:text-indigo-600"}`} />
              {(sidebarOpen || mobile) && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 p-3 space-y-1 flex-shrink-0">
        {(sidebarOpen || mobile) && userName && (
          <div className="flex items-center gap-2 px-3 py-2 truncate">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
              {userName.charAt(0).toUpperCase()}
            </span>
            <span className="truncate text-sm font-semibold text-indigo-600">{userName}</span>
          </div>
        )}
        <button
          onClick={toggleTheme}
          title={theme === "dark" ? "Mode clair" : "Mode sombre"}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
        >
          {theme === "dark" ? <Sun className="h-5 w-5 flex-shrink-0" /> : <Moon className="h-5 w-5 flex-shrink-0" />}
          {(sidebarOpen || mobile) && <span className="text-sm font-medium">{theme === "dark" ? "Mode clair" : "Mode sombre"}</span>}
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="h-5 w-5 flex-shrink-0" />
          {(sidebarOpen || mobile) && <span className="text-sm font-medium">Déconnexion</span>}
        </button>
      </div>

      {/* Toggle (desktop only) */}
      {!mobile && (
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="h-10 flex items-center justify-center border-t border-gray-200 hover:bg-gray-50 transition-colors flex-shrink-0"
        >
          <ChevronLeft className={`h-4 w-4 text-gray-500 transition-transform ${!sidebarOpen ? "rotate-180" : ""}`} />
        </button>
      )}
    </>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Desktop Sidebar */}
      <aside className={`hidden lg:flex ${sidebarOpen ? "w-64" : "w-[72px]"} bg-white border-r border-gray-200 transition-all duration-300 flex-col flex-shrink-0`}>
        <SidebarContent />
      </aside>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="fixed left-0 top-0 bottom-0 w-72 bg-white flex flex-col z-50 shadow-xl">
            <SidebarContent mobile />
          </aside>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Mobile Header */}
        <header className="lg:hidden h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-3 flex-shrink-0">
          <button onClick={() => setMobileOpen(true)} className="p-1.5 text-gray-600 hover:text-gray-900">
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 text-white">
            <BrainCircuit className="h-4 w-4" />
          </div>
          <span className="font-display font-bold text-gray-900">AI Talent Finder</span>
        </header>

        {/* scrollbar-gutter:stable reserves the scrollbar lane even when
            no scrollbar is visible — this prevents the page content from
            shifting ~15px left when matching results load and the scrollbar
            suddenly appears (reported: "bouge vers la gauche"). */}
        <main className="flex-1 overflow-y-auto [scrollbar-gutter:stable]">
          <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
