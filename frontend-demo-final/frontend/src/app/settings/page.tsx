"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { User, Lock, CheckCircle2, Eye, EyeOff } from "lucide-react";
export default function SettingsPage() {
  const { user } = useAuth(); const [name, setName] = useState(user?.full_name ?? ""); const [saved, setSaved] = useState(false);
  const [cpw, setCpw] = useState(""); const [npw, setNpw] = useState(""); const [cnpw, setCnpw] = useState(""); const [showPw, setShowPw] = useState(false); const [pwSaved, setPwSaved] = useState(false); const [err, setErr] = useState("");
  const saveProfile = async (e: React.FormEvent) => { e.preventDefault(); await new Promise(r => setTimeout(r, 500)); setSaved(true); setTimeout(() => setSaved(false), 3000); };
  const changePw = async (e: React.FormEvent) => { e.preventDefault(); setErr(""); if (npw.length<8) { setErr("Min. 8 caractères."); return; } if (npw!==cnpw) { setErr("Les mots de passe ne correspondent pas."); return; } await new Promise(r => setTimeout(r, 500)); setCpw(""); setNpw(""); setCnpw(""); setPwSaved(true); setTimeout(() => setPwSaved(false), 3000); };
  return <Layout><div className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Paramètres</h1><p className="text-sm text-gray-500 mt-1">Gérez votre compte</p></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-5"><User className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">Informations</h2></div>
      <form onSubmit={saveProfile} className="space-y-4"><div><label className="block text-sm font-medium text-gray-700 mb-1">Nom complet</label><input type="text" required value={name} onChange={e => setName(e.target.value)} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
        <div className="text-sm text-gray-500">Email : {user?.email} · Rôle : <span className={`font-medium ${user?.role==="candidate"?"text-emerald-600":"text-indigo-600"}`}>{user?.role==="candidate"?"Candidat":"Recruteur"}</span></div>
        <div className="flex items-center gap-3"><button type="submit" className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">Enregistrer</button>{saved && <span className="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 className="h-4 w-4" />Sauvegardé</span>}</div>
      </form></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-5"><Lock className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">Mot de passe</h2></div>
      {err && <div className="bg-red-50 text-red-600 text-sm px-4 py-2.5 rounded-lg mb-4">{err}</div>}
      <form onSubmit={changePw} className="space-y-4">
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Mot de passe actuel</label><input type={showPw?"text":"password"} required value={cpw} onChange={e => setCpw(e.target.value)} placeholder="••••••••" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm outline-none" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Nouveau</label><div className="relative"><input type={showPw?"text":"password"} required value={npw} onChange={e => setNpw(e.target.value)} placeholder="Min. 8 caractères" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm outline-none pr-10" /><button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">{showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Confirmer</label><input type="password" required value={cnpw} onChange={e => setCnpw(e.target.value)} placeholder="••••••••" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm outline-none" /></div>
        <div className="flex items-center gap-3"><button type="submit" className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">Modifier</button>{pwSaved && <span className="flex items-center gap-1 text-sm text-green-600"><CheckCircle2 className="h-4 w-4" />Modifié</span>}</div>
      </form></div>
  </div></Layout>;
}
