"use client";
import { useState } from "react";
import { useAuth, UserRole } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import Link from "next/link";
import { BrainCircuit, Eye, EyeOff, Moon, Sun, Briefcase, UserCircle } from "lucide-react";
export default function LoginPage() {
  const { login } = useAuth(); const { theme, toggleTheme } = useTheme();
  const [role, setRole] = useState<UserRole|null>(null); const [email, setEmail] = useState(""); const [pw, setPw] = useState("");
  const [showPw, setShowPw] = useState(false); const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const submit = async (e: React.FormEvent) => { e.preventDefault(); if (!role) { setError("Veuillez sélectionner votre profil."); return; } setError(""); setLoading(true); try { await login(email, pw, role); } catch { setError("Email ou mot de passe incorrect."); } finally { setLoading(false); } };
  return <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 relative">
    <button onClick={toggleTheme} className="absolute top-6 right-6 p-2.5 rounded-xl bg-white border border-gray-200 text-gray-500 hover:text-indigo-600 transition-colors">{theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
    <div className="w-full max-w-md">
      <div className="flex items-center justify-center gap-2 mb-8"><BrainCircuit className="h-9 w-9 text-indigo-600" /><h1 className="text-2xl font-bold text-gray-900">AI Talent Finder</h1></div>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Connexion</h2>
        <p className="text-sm text-gray-500 mb-6">Sélectionnez votre profil pour continuer</p>
        {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2.5 rounded-lg mb-4">{error}</div>}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {([["recruiter","Recruteur","Chercher des talents",Briefcase],["candidate","Candidat","Déposer mon CV",UserCircle]] as const).map(([r,l,d,I]) =>
            <button key={r} type="button" onClick={() => setRole(r)} className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${role===r ? "border-indigo-600 bg-indigo-50 text-indigo-700" : "border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50"}`}>
              <I className="h-8 w-8" /><span className="text-sm font-semibold">{l}</span><span className="text-[11px] leading-tight opacity-70">{d}</span>
            </button>)}
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="vous@exemple.com" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe</label><div className="relative"><input type={showPw?"text":"password"} required value={pw} onChange={e => setPw(e.target.value)} placeholder="••••••••" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none pr-10" /><button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>
          <button type="submit" disabled={loading||!role} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{loading ? "Connexion..." : `Se connecter en tant que ${role==="candidate"?"candidat":role==="recruiter"?"recruteur":"..."}`}</button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">Pas encore de compte ? <Link href="/register" className="text-indigo-600 font-medium hover:underline">S&apos;inscrire</Link></p>
        <p className="text-center text-sm mt-2"><Link href="/forgot-password" className="text-gray-400 hover:text-indigo-600 hover:underline">Mot de passe oublié ?</Link></p>
      </div>
    </div>
  </div>;
}
