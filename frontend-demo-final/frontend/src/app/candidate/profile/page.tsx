"use client";
import Layout from "@/components/Layout";
import SkillBadge from "@/components/SkillBadge";
import SkillRadarChart, { skillLevelToValue } from "@/components/SkillRadarChart";
import { useAuth } from "@/hooks/useAuth";
import { CheckCircle2, Code2, Briefcase, GraduationCap, Globe } from "lucide-react";
const p = {
  skills: [{name:"Python",level:"senior" as const,category:"tech" as const},{name:"JavaScript",level:"intermédiaire" as const,category:"tech" as const},{name:"React",level:"intermédiaire" as const,category:"tech" as const},{name:"PostgreSQL",level:"intermédiaire" as const,category:"tech" as const},{name:"Docker",level:"junior" as const,category:"tech" as const},{name:"Git",level:"senior" as const,category:"tech" as const},{name:"Communication",level:"senior" as const,category:"soft" as const},{name:"Travail d'équipe",level:"intermédiaire" as const,category:"soft" as const},{name:"Français",level:"expert" as const,category:"language" as const},{name:"Anglais",level:"intermédiaire" as const,category:"language" as const},{name:"Arabe",level:"expert" as const,category:"language" as const}],
  experiences: [{title:"Développeur Full-Stack",company:"TechCorp Maroc",duration:"1 an 6 mois",description:"Applications web avec React et FastAPI."},{title:"Stagiaire développeur",company:"StartupXYZ",duration:"4 mois",description:"Backend en Python."}],
  education: [{degree:"Master Ingénierie Informatique",institution:"ESISA Fès",field:"Génie Logiciel",year:"2025"},{degree:"Licence SMI",institution:"Université Mohammed V",field:"Informatique",year:"2023"}],
};
export default function CandidateProfile() {
  const { user } = useAuth();
  const tech = p.skills.filter(s => s.category==="tech"), soft = p.skills.filter(s => s.category==="soft"), lang = p.skills.filter(s => s.category==="language");
  return <Layout><div className="max-w-3xl mx-auto space-y-6">
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center gap-4 mb-4"><div className="w-14 h-14 rounded-full bg-indigo-100 flex items-center justify-center"><span className="text-xl font-bold text-indigo-600">{(user?.full_name??"C").charAt(0).toUpperCase()}</span></div><div><h1 className="text-2xl font-bold text-gray-900">{user?.full_name}</h1><p className="text-sm text-gray-500">{user?.email}</p></div></div>
      <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-2 rounded-lg"><CheckCircle2 className="h-4 w-4" />Profil généré par l&apos;IA à partir de votre CV</div>
    </div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-4"><Code2 className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">Compétences techniques</h2></div><div className="flex flex-wrap gap-2">{tech.map(s => <SkillBadge key={s.name} {...s} />)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-4"><Briefcase className="h-5 w-5 text-pink-500" /><h2 className="text-lg font-semibold text-gray-900">Soft Skills</h2></div><div className="flex flex-wrap gap-2">{soft.map(s => <SkillBadge key={s.name} {...s} />)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-4"><Globe className="h-5 w-5 text-amber-500" /><h2 className="text-lg font-semibold text-gray-900">Langues</h2></div><div className="flex flex-wrap gap-2">{lang.map(s => <SkillBadge key={s.name} {...s} />)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><SkillRadarChart title="Compétences techniques" skills={tech.map(s => ({ name: s.name, value: skillLevelToValue(s.level) }))} /></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-4"><Briefcase className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">Expériences</h2></div><div className="space-y-4">{p.experiences.map((x,i) => <div key={i} className="border-l-2 border-indigo-200 pl-4"><p className="font-medium text-gray-900">{x.title}</p><p className="text-sm text-gray-500">{x.company} · {x.duration}</p><p className="text-sm text-gray-600 mt-1">{x.description}</p></div>)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><div className="flex items-center gap-2 mb-4"><GraduationCap className="h-5 w-5 text-indigo-600" /><h2 className="text-lg font-semibold text-gray-900">Formation</h2></div><div className="space-y-3">{p.education.map((x,i) => <div key={i} className="border-l-2 border-indigo-200 pl-4"><p className="font-medium text-gray-900">{x.degree}</p><p className="text-sm text-gray-500">{x.institution} · {x.field} · {x.year}</p></div>)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-5 text-center"><p className="text-sm text-gray-500">Votre profil est stocké en base de données et accessible aux recruteurs.</p></div>
  </div></Layout>;
}
