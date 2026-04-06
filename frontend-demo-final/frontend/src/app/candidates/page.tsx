"use client";
import { useState, useMemo } from "react";
import Layout from "@/components/Layout";
import CandidateCard from "@/components/CandidateCard";
import { Search, SlidersHorizontal, ArrowUpDown, X } from "lucide-react";
const data = [
  { id:"1",fullName:"Ahmed Benali",email:"ahmed@mail.com",skills:[{name:"Python",category:"tech" as const},{name:"React",category:"tech" as const},{name:"Docker",category:"tech" as const}],score:87,date:"2025-03-15" },
  { id:"2",fullName:"Sara El Idrissi",email:"sara@mail.com",skills:[{name:"JavaScript",category:"tech" as const},{name:"Next.js",category:"tech" as const},{name:"Anglais",category:"language" as const}],score:72,date:"2025-03-20" },
  { id:"3",fullName:"Omar Youssef",email:"omar@mail.com",skills:[{name:"Java",category:"tech" as const},{name:"Spring Boot",category:"tech" as const},{name:"PostgreSQL",category:"tech" as const}],score:65,date:"2025-03-10" },
  { id:"4",fullName:"Fatima Zahra",email:"fatima@mail.com",skills:[{name:"Python",category:"tech" as const},{name:"TensorFlow",category:"tech" as const}],score:58,date:"2025-04-01" },
  { id:"5",fullName:"Youssef Amrani",email:"youssef@mail.com",skills:[{name:"Go",category:"tech" as const},{name:"Kubernetes",category:"tech" as const},{name:"AWS",category:"tech" as const}],score:91,date:"2025-03-25" },
  { id:"6",fullName:"Nadia Benchekroun",email:"nadia@mail.com",skills:[{name:"React",category:"tech" as const},{name:"TypeScript",category:"tech" as const}],score:43,date:"2025-02-28" },
];
type SF = "score"|"name"|"date"; type SD = "asc"|"desc";
export default function CandidatesPage() {
  const [search,setSearch] = useState(""); const [minScore,setMinScore] = useState(0); const [sf,setSf] = useState<SF>("score"); const [sd,setSd] = useState<SD>("desc"); const [showF,setShowF] = useState(false);
  const toggle = (f: SF) => { if (sf===f) setSd(d => d==="asc"?"desc":"asc"); else { setSf(f); setSd(f==="name"?"asc":"desc"); } };
  const filtered = useMemo(() => {
    let r = data.filter(c => (c.fullName.toLowerCase().includes(search.toLowerCase())||c.skills.some(s => s.name.toLowerCase().includes(search.toLowerCase()))) && (c.score??0) >= minScore);
    r.sort((a,b) => { let v = 0; if (sf==="score") v=(a.score??0)-(b.score??0); else if (sf==="name") v=a.fullName.localeCompare(b.fullName); else v=new Date(a.date).getTime()-new Date(b.date).getTime(); return sd==="asc"?v:-v; });
    return r;
  }, [search,minScore,sf,sd]);
  const sl = (f: SF) => ({ score:"Score",name:"Nom",date:"Date" }[f] + (sf===f ? (sd==="asc"?" ↑":" ↓") : ""));
  return <Layout><div className="max-w-4xl mx-auto space-y-5">
    <div className="flex items-center justify-between">
      <div><h1 className="text-2xl font-bold text-gray-900">Candidats</h1><p className="text-sm text-gray-500 mt-1">{filtered.length} candidat(s)</p></div>
      <button onClick={() => setShowF(!showF)} className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${showF||minScore>0 ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "border-gray-300 text-gray-600 hover:bg-gray-50"}`}><SlidersHorizontal className="h-4 w-4" />Filtres{minScore>0 && <span className="bg-indigo-600 text-white text-xs px-1.5 py-0.5 rounded-full">1</span>}</button>
    </div>
    <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 py-2.5"><Search className="h-4 w-4 text-gray-400" /><input type="text" placeholder="Rechercher par nom ou compétence..." value={search} onChange={e => setSearch(e.target.value)} className="flex-1 text-sm outline-none" />{search && <button onClick={() => setSearch("")} className="text-gray-400 hover:text-gray-600"><X className="h-4 w-4" /></button>}</div>
    {showF && <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
      <div><label className="block text-sm font-medium text-gray-700 mb-2">Score minimum : <span className="text-indigo-600 font-bold">{minScore}%</span></label><input type="range" min={0} max={100} value={minScore} onChange={e => setMinScore(Number(e.target.value))} className="w-full accent-indigo-600" /></div>
      <div><label className="block text-sm font-medium text-gray-700 mb-2"><ArrowUpDown className="h-3.5 w-3.5 inline mr-1" />Trier par</label><div className="flex gap-2">{(["score","name","date"] as SF[]).map(f => <button key={f} onClick={() => toggle(f)} className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${sf===f ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>{sl(f)}</button>)}</div></div>
    </div>}
    <div className="space-y-3">{filtered.map(c => <CandidateCard key={c.id} {...c} onToggleFavorite={() => {}} />)}{filtered.length===0 && <p className="text-center text-gray-400 py-16">Aucun candidat ne correspond.</p>}</div>
  </div></Layout>;
}
