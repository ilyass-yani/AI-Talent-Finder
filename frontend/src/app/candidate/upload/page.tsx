"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import FileUpload from "@/components/FileUpload";
import { CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";
export default function CandidateUpload() {
  const [done, setDone] = useState(false);
  const upload = async (files: File[]) => { await new Promise(r => setTimeout(r, 2000)); console.log("DEMO — CV:", files.map(f => f.name)); setDone(true); };
  return <Layout><div className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Déposer mon CV</h1><p className="text-sm text-gray-500 mt-1">Uploadez votre CV au format PDF. Notre IA extraira vos compétences.</p></div>
    {!done ? <div className="bg-white rounded-xl border border-gray-200 p-6"><FileUpload onUpload={upload} /></div>
      : <div className="bg-white rounded-xl border border-green-200 p-8 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto"><CheckCircle2 className="h-8 w-8 text-green-600" /></div>
        <div><h2 className="text-lg font-semibold text-gray-900">CV envoyé !</h2><p className="text-sm text-gray-500 mt-1">L&apos;analyse IA est en cours.</p></div>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link href="/candidate/profile" className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">Voir mon profil <ArrowRight className="h-4 w-4" /></Link>
          <button onClick={() => setDone(false)} className="px-5 py-2.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">Autre CV</button>
        </div>
      </div>}
  </div></Layout>;
}
