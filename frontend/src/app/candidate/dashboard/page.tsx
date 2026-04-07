"use client";
import Layout from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import Link from "next/link";
import { Upload, UserCircle, CheckCircle2, Clock, FileText } from "lucide-react";
export default function CandidateDashboard() {
  const { user } = useAuth();
  const steps = [
    { n:1, label:"Déposer votre CV", desc:"Uploadez votre CV au format PDF pour que l'IA analyse vos compétences.", icon:Upload, done:false, href:"/candidate/upload", action:"Uploader mon CV" },
    { n:2, label:"Analyse IA automatique", desc:"Notre IA extrait automatiquement vos compétences, expériences et formations.", icon:FileText, done:false, href:undefined, action:undefined },
    { n:3, label:"Profil généré", desc:"Consultez votre profil structuré et vérifiez vos compétences.", icon:UserCircle, done:false, href:undefined, action:undefined },
  ];
  return <Layout><div className="max-w-3xl mx-auto space-y-8">
    <div><h1 className="text-2xl font-bold text-gray-900">Bienvenue, {user?.full_name ?? "Candidat"} !</h1><p className="text-sm text-gray-500 mt-1">Suivez les étapes pour créer votre profil.</p></div>
    <div className="space-y-4">{steps.map((s, i) => <div key={s.n} className={`bg-white rounded-xl border p-6 transition-shadow ${s.done ? "border-green-200" : i===0||steps[i-1]?.done ? "border-indigo-200 hover:shadow-md" : "border-gray-200 opacity-60"}`}>
      <div className="flex items-start gap-4">
        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${s.done ? "bg-green-100 text-green-600" : "bg-indigo-100 text-indigo-600"}`}>{s.done ? <CheckCircle2 className="h-5 w-5" /> : <span className="text-sm font-bold">{s.n}</span>}</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1"><h3 className="font-semibold text-gray-900">{s.label}</h3>{!s.done && i>0 && !steps[i-1]?.done && <span className="flex items-center gap-1 text-xs text-gray-400"><Clock className="h-3 w-3" />En attente</span>}</div>
          <p className="text-sm text-gray-500">{s.desc}</p>
          {s.href && s.action && <Link href={s.href} className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"><s.icon className="h-4 w-4" />{s.action}</Link>}
        </div>
      </div>
    </div>)}</div>
  </div></Layout>;
}
