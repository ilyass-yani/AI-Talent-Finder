"use client";
import { useState } from "react";
import { useTheme } from "@/hooks/useTheme";
import Link from "next/link";
import { BrainCircuit, Mail, ArrowLeft, CheckCircle2, Moon, Sun } from "lucide-react";
export default function ForgotPasswordPage() {
  const { theme, toggleTheme } = useTheme(); const [email, setEmail] = useState(""); const [sent, setSent] = useState(false); const [loading, setLoading] = useState(false);
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setLoading(true); await new Promise(r => setTimeout(r, 1000)); setSent(true); setLoading(false); };
  return <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 relative">
    <button onClick={toggleTheme} className="absolute top-6 right-6 p-2.5 rounded-xl bg-white border border-gray-200 text-gray-500 hover:text-indigo-600 transition-colors">{theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}</button>
    <div className="w-full max-w-md">
      <div className="flex items-center justify-center gap-2 mb-8"><BrainCircuit className="h-9 w-9 text-indigo-600" /><h1 className="text-2xl font-bold text-gray-900">AI Talent Finder</h1></div>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        {!sent ? <><h2 className="text-xl font-semibold text-gray-900 mb-1">Mot de passe oublié</h2><p className="text-sm text-gray-500 mb-6">Entrez votre email pour recevoir un lien de réinitialisation.</p>
          <form onSubmit={submit} className="space-y-4"><div className="relative"><Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" /><input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="vous@exemple.com" className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
            <button type="submit" disabled={loading} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{loading ? "Envoi..." : "Envoyer le lien"}</button></form>
        </> : <div className="text-center py-4"><div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4"><CheckCircle2 className="h-7 w-7 text-green-600" /></div><h2 className="text-xl font-semibold text-gray-900 mb-2">Email envoyé !</h2><p className="text-sm text-gray-500">Si un compte existe avec <span className="font-medium text-gray-700">{email}</span>, vous recevrez un lien.</p></div>}
        <div className="mt-6 text-center"><Link href="/login" className="inline-flex items-center gap-1 text-sm text-indigo-600 font-medium hover:underline"><ArrowLeft className="h-4 w-4" /> Retour</Link></div>
      </div>
    </div>
  </div>;
}
