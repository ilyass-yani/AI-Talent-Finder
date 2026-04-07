"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import SkillBadge from "@/components/SkillBadge";
import ScoreGauge from "@/components/ScoreGauge";
import SkillRadarChart, { skillLevelToValue } from "@/components/SkillRadarChart";
import { ArrowLeft, Mail, ExternalLink, Code2, Download, GitCompareArrows } from "lucide-react";
import Link from "next/link";
interface CD { id:string; fullName:string; email:string; phone:string; linkedinUrl:string; githubUrl:string; skills:{name:string;level:"junior"|"intermédiaire"|"senior"|"expert";category:"tech"|"soft"|"language"}[]; experiences:{title:string;company:string;duration:string;description:string}[]; education:{degree:string;institution:string;field:string;year:string}[]; score:number; }
const cands: Record<string,CD> = {
  "1": { id:"1",fullName:"Ahmed Benali",email:"ahmed@mail.com",phone:"+212 6 12 34 56 78",linkedinUrl:"https://linkedin.com/in/ahmed",githubUrl:"https://github.com/ahmed",skills:[{name:"Python",level:"senior",category:"tech"},{name:"React",level:"intermédiaire",category:"tech"},{name:"Docker",level:"intermédiaire",category:"tech"},{name:"PostgreSQL",level:"senior",category:"tech"},{name:"Communication",level:"senior",category:"soft"},{name:"Français",level:"expert",category:"language"},{name:"Anglais",level:"intermédiaire",category:"language"}],experiences:[{title:"Développeur Backend",company:"TechCorp",duration:"2 ans",description:"APIs REST avec FastAPI."},{title:"Stagiaire Data",company:"DataLab",duration:"6 mois",description:"Analyse avec Pandas."}],education:[{degree:"Master Informatique",institution:"ESISA",field:"Génie Logiciel",year:"2023"}],score:87 },
  "2": { id:"2",fullName:"Sara El Idrissi",email:"sara@mail.com",phone:"+212 6 98 76 54",linkedinUrl:"https://linkedin.com/in/sara",githubUrl:"https://github.com/sara",skills:[{name:"Python",level:"intermédiaire",category:"tech"},{name:"React",level:"senior",category:"tech"},{name:"Docker",level:"junior",category:"tech"},{name:"PostgreSQL",level:"intermédiaire",category:"tech"},{name:"Communication",level:"intermédiaire",category:"soft"},{name:"Français",level:"expert",category:"language"},{name:"Anglais",level:"senior",category:"language"}],experiences:[{title:"Développeuse Frontend",company:"WebAgency",duration:"1 an",description:"React et Next.js."}],education:[{degree:"Master Informatique",institution:"EMI",field:"Dev Web",year:"2024"}],score:72 },
};
const c = cands["1"]; const opts = Object.values(cands).filter(x => x.id!=="1");
export default function CandidateDetailPage() {
  const [cw, setCw] = useState<string|null>(null); const cc = cw ? cands[cw] : null;
  const rs = c.skills.filter(s => s.category==="tech").map(s => ({ name:s.name, value:skillLevelToValue(s.level) }));
  const cd = cc ? [{ name:cc.fullName, color:"#f59e0b", skills:cc.skills.filter(s => s.category==="tech").map(s => ({ name:s.name, value:skillLevelToValue(s.level) })) }] : undefined;
  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <Link href="/candidates" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" /> Retour</Link>
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-start justify-between">
      <div><h1 className="text-2xl font-bold text-gray-900">{c.fullName}</h1><div className="flex items-center gap-4 mt-2 text-sm text-gray-500"><a href={`mailto:${c.email}`} className="flex items-center gap-1 hover:text-indigo-600"><Mail className="h-4 w-4" />{c.email}</a>{c.linkedinUrl && <a href={c.linkedinUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-blue-600"><ExternalLink className="h-4 w-4" />LinkedIn</a>}{c.githubUrl && <a href={c.githubUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-gray-800"><Code2 className="h-4 w-4" />GitHub</a>}</div></div>
      <div className="flex items-center gap-4"><ScoreGauge score={c.score} size="lg" /><button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"><Download className="h-4 w-4" /> CV</button></div>
    </div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><h2 className="text-lg font-semibold text-gray-900 mb-4">Compétences</h2><div className="flex flex-wrap gap-2">{c.skills.map(s => <SkillBadge key={s.name} {...s} />)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4"><h2 className="text-lg font-semibold text-gray-900">Visualisation</h2><div className="flex items-center gap-2"><GitCompareArrows className="h-4 w-4 text-gray-400" /><select value={cw??""} onChange={e => setCw(e.target.value||null)} className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 outline-none focus:ring-2 focus:ring-indigo-500"><option value="">Comparer avec...</option>{opts.map(o => <option key={o.id} value={o.id}>{o.fullName} ({o.score}%)</option>)}</select></div></div>
      <SkillRadarChart title={c.fullName} skills={rs} compareData={cd} />
    </div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><h2 className="text-lg font-semibold text-gray-900 mb-4">Expériences</h2><div className="space-y-4">{c.experiences.map((x,i) => <div key={i} className="border-l-2 border-indigo-200 pl-4"><p className="font-medium text-gray-900">{x.title}</p><p className="text-sm text-gray-500">{x.company} · {x.duration}</p><p className="text-sm text-gray-600 mt-1">{x.description}</p></div>)}</div></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><h2 className="text-lg font-semibold text-gray-900 mb-4">Formation</h2>{c.education.map((x,i) => <div key={i}><p className="font-medium text-gray-900">{x.degree}</p><p className="text-sm text-gray-500">{x.institution} · {x.field} · {x.year}</p></div>)}</div>
  </div></Layout>;
}
