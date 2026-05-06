"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Menu, X, LogOut, LayoutDashboard, Users, Upload, SlidersHorizontal,
  GitCompareArrows, MessageCircle, Heart, FileDown, BrainCircuit,
  UserCircle, Wrench, ChevronLeft, Moon, Sun,
} from "lucide-react";
import { useTheme } from "@/hooks/useTheme";

const recruiterNav = [
  { href: "/recruiter/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/candidates", label: "Candidats", icon: Users },
  { href: "/skills", label: "Compétences", icon: Wrench },
  { href: "/jobs", label: "Critères de poste", icon: SlidersHorizontal },
  { href: "/matching", label: "Matching", icon: GitCompareArrows },
  { href: "/recruiter/chatbot", label: "Chatbot IA", icon: MessageCircle },
  { href: "/recruiter/shortlist", label: "Shortlist", icon: Heart },
  { href: "/recruiter/export", label: "Export", icon: FileDown },
];

const candidateNav = [
  { href: "/candidate/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/candidate/upload", label: "Déposer mon CV", icon: Upload },
  { href: "/candidate/profile", label: "Mon profil", icon: UserCircle },
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
  const nav = isCandidate ? candidateNav : recruiterNav;

  const SidebarContent = ({ mobile = false }: { mobile?: boolean }) => (
    <>
      {/* Header */}
      <div className="h-16 flex items-center gap-2 px-4 border-b border-gray-200 flex-shrink-0">
        <BrainCircuit className="h-7 w-7 text-indigo-600 flex-shrink-0" />
        {(sidebarOpen || mobile) && (
          <span className="text-lg font-bold text-gray-900 truncate">AI Talent Finder</span>
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
            isCandidate ? "bg-emerald-100 text-emerald-700" : "bg-indigo-100 text-indigo-700"
          }`}>
            {isCandidate ? "Espace Candidat" : "Espace Recruteur"}
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
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {(sidebarOpen || mobile) && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 p-3 space-y-1 flex-shrink-0">
        {(sidebarOpen || mobile) && userName && (
          <div className="px-3 py-2 text-xs text-gray-500 truncate">
            <span className="font-medium text-gray-700">{userName}</span>
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
          <BrainCircuit className="h-5 w-5 text-indigo-600" />
          <span className="font-bold text-gray-900">AI Talent Finder</span>
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
