"use client";
import { useState } from "react";
import { Plus, Trash2, Search } from "lucide-react";
interface SC { id: string; name: string; weight: number; }
interface Props { onSubmit: (d: { title: string; description: string; skills: SC[] }) => void; loading?: boolean; }
const SKILLS = ["Python","JavaScript","TypeScript","Java","C++","Go","Rust","React","Next.js","FastAPI","Django","Spring Boot","Express.js","PostgreSQL","MongoDB","Redis","Docker","Kubernetes","AWS","TensorFlow","PyTorch","Pandas","Scikit-learn","Communication","Leadership","Travail d'équipe","Français","Anglais","Arabe","Espagnol"];
export default function CriteriaForm({ onSubmit, loading = false }: Props) {
  const [title, setTitle] = useState(""); const [desc, setDesc] = useState(""); const [skills, setSkills] = useState<SC[]>([]); const [search, setSearch] = useState(""); const [show, setShow] = useState(false);
  const filtered = SKILLS.filter(s => s.toLowerCase().includes(search.toLowerCase()) && !skills.find(x => x.name === s));
  const total = skills.reduce((s, x) => s + x.weight, 0);
  return <div className="space-y-6">
    <div className="space-y-3">
      <input type="text" placeholder="Titre (ex: Développeur Full-Stack Senior)" value={title} onChange={e => setTitle(e.target.value)} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" />
      <textarea placeholder="Description (optionnel)" value={desc} onChange={e => setDesc(e.target.value)} rows={2} className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none" />
    </div>
    <div className="relative">
      <div className="flex items-center gap-2 border border-gray-300 rounded-lg px-3 py-2.5">
        <Search className="h-4 w-4 text-gray-400" />
        <input type="text" placeholder="Rechercher une compétence..." value={search} onChange={e => { setSearch(e.target.value); setShow(true); }} onFocus={() => setShow(true)} className="flex-1 text-sm outline-none" />
        <Plus className="h-4 w-4 text-gray-400" />
      </div>
      {show && search && filtered.length > 0 && <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
        {filtered.map(s => <button key={s} onClick={() => { setSkills(p => [...p, { id: crypto.randomUUID(), name: s, weight: 50 }]); setSearch(""); setShow(false); }} className="w-full text-left px-4 py-2 text-sm hover:bg-indigo-50 hover:text-indigo-700 transition-colors">{s}</button>)}
      </div>}
    </div>
    {skills.length > 0 && <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-gray-500"><span>{skills.length} compétence(s)</span><span className={total > 0 ? "text-indigo-600 font-medium" : ""}>Total : {total}</span></div>
      {skills.map(s => <div key={s.id} className="flex items-center gap-3 bg-gray-50 rounded-lg px-4 py-3">
        <span className="text-sm font-medium text-gray-700 w-32 truncate">{s.name}</span>
        <input type="range" min={0} max={100} value={s.weight} onChange={e => setSkills(p => p.map(x => x.id === s.id ? { ...x, weight: Number(e.target.value) } : x))} className="flex-1 accent-indigo-600" />
        <span className="text-sm font-bold text-indigo-600 w-12 text-right">{s.weight}%</span>
        <button onClick={() => setSkills(p => p.filter(x => x.id !== s.id))} className="text-gray-400 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
      </div>)}
    </div>}
    <button onClick={() => onSubmit({ title, description: desc, skills })} disabled={!title || !skills.length || loading} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
      {loading ? "Création en cours..." : "Créer les critères et lancer le matching"}
    </button>
  </div>;
}
