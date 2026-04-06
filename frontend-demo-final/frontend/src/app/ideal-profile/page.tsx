"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import SkillBadge from "@/components/SkillBadge";
import SkillRadarChart, { skillLevelToValue } from "@/components/SkillRadarChart";
import { Sparkles, ArrowRight, RotateCcw, GitCompareArrows } from "lucide-react";
import Link from "next/link";
interface GP { title: string; skills: { name: string; level: "junior"|"intermédiaire"|"senior"|"expert"; category: "tech"|"soft"|"language"; weight: number }[]; experience: string; summary: string; }
const demos: Record<string,GP> = {
  default: { title: "Développeur Full-Stack Senior", skills: [{ name:"Python",level:"senior",category:"tech",weight:35 },{ name:"React",level:"senior",category:"tech",weight:25 },{ name:"PostgreSQL",level:"intermédiaire",category:"tech",weight:15 },{ name:"Docker",level:"intermédiaire",category:"tech",weight:10 },{ name:"Communication",level:"senior",category:"soft",weight:10 },{ name:"Anglais",level:"intermédiaire",category:"language",weight:5 }], experience: "3-5 ans minimum", summary: "Profil technique polyvalent, frontend et backend, avec solide maîtrise Python et React." },
  data: { title: "Data Scientist Junior", skills: [{ name:"Python",level:"senior",category:"tech",weight:30 },{ name:"Pandas",level:"intermédiaire",category:"tech",weight:20 },{ name:"Scikit-learn",level:"intermédiaire",category:"tech",weight:15 },{ name:"SQL",level:"intermédiaire",category:"tech",weight:15 },{ name:"TensorFlow",level:"junior",category:"tech",weight:10 },{ name:"Anglais",level:"intermédiaire",category:"language",weight:10 }], experience: "Stage ou 1-2 ans", summary: "Profil orienté data avec bonnes bases Python et analyse statistique." },
};
export default function IdealProfilePage() {
  const [desc, setDesc] = useState(""); const [loading, setLoading] = useState(false); const [profile, setProfile] = useState<GP|null>(null);
  const gen = async () => { if (!desc.trim()) return; setLoading(true); await new Promise(r => setTimeout(r, 2000)); const l = desc.toLowerCase(); setProfile(l.includes("data")||l.includes("ml")||l.includes("machine") ? demos.data : demos.default); setLoading(false); };
  return <Layout><div className="max-w-3xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Générer un profil idéal</h1><p className="text-sm text-gray-500 mt-1">Décrivez le profil recherché en langage naturel. L&apos;IA générera les compétences et pondérations.</p></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={4} placeholder="Ex : Je cherche un stagiaire en data science avec Python et SQL..." className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none" />
      <div className="flex items-center gap-3 mt-4">
        <button onClick={gen} disabled={loading||!desc.trim()} className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"><Sparkles className="h-4 w-4" />{loading ? "Génération..." : "Générer le profil idéal"}</button>
        {profile && <button onClick={() => { setDesc(""); setProfile(null); }} className="flex items-center gap-1 px-4 py-2.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50"><RotateCcw className="h-4 w-4" /> Recommencer</button>}
      </div>
    </div>
    {loading && <div className="bg-white rounded-xl border border-gray-200 p-8 text-center"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" /><p className="text-sm text-gray-500">L&apos;IA analyse votre besoin...</p></div>}
    {profile && !loading && <>
      <div className="bg-white rounded-xl border border-indigo-200 p-6">
        <div className="flex items-center gap-2 mb-1"><Sparkles className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">{profile.title}</h2></div>
        <p className="text-sm text-gray-500 mb-4">{profile.experience}</p>
        <p className="text-sm text-gray-600 mb-5 bg-gray-50 px-4 py-3 rounded-lg">{profile.summary}</p>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Compétences et pondérations</h3>
        <div className="space-y-2 mb-6">{profile.skills.map(s => <div key={s.name} className="flex items-center gap-3"><SkillBadge name={s.name} level={s.level} category={s.category} /><div className="flex-1 bg-gray-100 rounded-full h-2"><div className="bg-indigo-500 h-2 rounded-full" style={{ width: s.weight+"%" }} /></div><span className="text-sm font-bold text-indigo-600 w-12 text-right">{s.weight}%</span></div>)}</div>
        <SkillRadarChart title="Profil idéal" skills={profile.skills.map(s => ({ name: s.name, value: skillLevelToValue(s.level) }))} />
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-5 text-center"><p className="text-sm text-gray-500 mb-3">Lancez le matching pour trouver les candidats les plus proches.</p><Link href="/matching" className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"><GitCompareArrows className="h-4 w-4" />Lancer le matching <ArrowRight className="h-4 w-4" /></Link></div>
    </>}
  </div></Layout>;
}
