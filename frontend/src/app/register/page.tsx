"use client";
import { useState } from "react";
import { useAuth, UserRole } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import Link from "next/link";
import { BrainCircuit, Eye, EyeOff, Moon, Sun, Briefcase, UserCircle } from "lucide-react";
export default function RegisterPage() {
  const { register } = useAuth(); const { theme, toggleTheme } = useTheme();
  const [role, setRole] = useState<UserRole|null>(null); const [name, setName] = useState(""); const [email, setEmail] = useState("");
  const [pw, setPw] = useState(""); const [cpw, setCpw] = useState(""); const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState(""); const [loading, setLoading] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError("");
    if (!role) { setError("Veuillez sélectionner votre profil."); return; }
    if (pw !== cpw) { setError("Les mots de passe ne correspondent pas."); return; }
    if (pw.length < 8) { setError("Le mot de passe doit contenir au moins 8 caractères."); return; }
    setLoading(true); try { await register(email, pw, name, role); } catch { setError("Erreur lors de l'inscription."); } finally { setLoading(false); }
  };
  return <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 relative">
    <button onClick={toggleTheme} className="absolute top-6 right-6 p-2.5 rounded-xl bg-white border border-gray-200 text-gray-500 hover:text-indigo-600 transition-colors">{theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
    <div className="w-full max-w-md">
      <div className="flex items-center justify-center gap-2 mb-8"><BrainCircuit className="h-9 w-9 text-indigo-600" /><h1 className="text-2xl font-bold text-gray-900">AI Talent Finder</h1></div>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">Inscription</h2>
        <p className="text-sm text-gray-500 mb-6">Créez votre compte</p>
        {error && <div className="bg-red-50 text-red-600 text-sm px-4 py-2.5 rounded-lg mb-4">{error}</div>}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {([["recruiter","Recruteur","Chercher des talents",Briefcase],["candidate","Candidat","Déposer mon CV",UserCircle]] as const).map(([r,l,d,I]) =>
            <button key={r} type="button" onClick={() => setRole(r)} className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${role===r ? "border-indigo-600 bg-indigo-50 text-indigo-700" : "border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50"}`}>
              <I className="h-8 w-8" /><span className="text-sm font-semibold">{l}</span><span className="text-[11px] leading-tight opacity-70">{d}</span>
            </button>)}
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Nom complet</label><input type="text" required value={name} onChange={e => setName(e.target.value)} placeholder="Jean Dupont" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="vous@exemple.com" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe</label><div className="relative"><input type={showPw?"text":"password"} required value={pw} onChange={e => setPw(e.target.value)} placeholder="Min. 8 caractères" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none pr-10" /><button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Confirmer</label><input type="password" required value={cpw} onChange={e => setCpw(e.target.value)} placeholder="••••••••" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
          <button type="submit" disabled={loading||!role} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{loading ? "Inscription..." : "Créer mon compte"}</button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">Déjà un compte ? <Link href="/login" className="text-indigo-600 font-medium hover:underline">Se connecter</Link></p>
      </div>
    </div>
  </div>;
}
