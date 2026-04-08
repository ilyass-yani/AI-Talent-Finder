"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import { useApi } from "@/hooks/useApi";
import { skillsApi } from "@/services/skills";
import SkillBadge from "@/components/SkillBadge";
import { Plus, Trash2, Loader2 } from "lucide-react";

export default function SkillsPage() {
  const { data: skills, loading, refetch } = useApi(() => skillsApi.getSkills(), []);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("tech");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  const addSkill = async (e: React.FormEvent) => {
    e.preventDefault(); if (!name.trim()) return;
    setAdding(true); setError("");
    try { await skillsApi.createSkill({ name: name.trim(), category }); setName(""); refetch(); }
    catch { setError("Cette compétence existe peut-être déjà."); }
    finally { setAdding(false); }
  };

  const deleteSkill = async (id: number) => {
    if (!confirm("Supprimer cette compétence ?")) return;
    try { await skillsApi.deleteSkill(id); refetch(); } catch { alert("Erreur."); }
  };

  const byCategory = (cat: string) => (skills || []).filter(s => s.category === cat);

  return <Layout><div className="max-w-3xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Compétences</h1><p className="text-sm text-gray-500 mt-1">Gérer le dictionnaire — <code className="bg-gray-100 px-1 rounded text-xs">GET/POST/DELETE /skills/</code></p></div>

    {/* Formulaire d'ajout */}
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <form onSubmit={addSkill} className="flex items-end gap-3">
        <div className="flex-1"><label className="block text-sm font-medium text-gray-700 mb-1">Nom</label><input type="text" value={name} onChange={e=>setName(e.target.value)} placeholder="Ex: Python, Docker..." className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Catégorie</label><select value={category} onChange={e=>setCategory(e.target.value)} className="px-4 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"><option value="tech">Tech</option><option value="soft">Soft skill</option><option value="language">Langue</option></select></div>
        <button type="submit" disabled={adding||!name.trim()} className="flex items-center gap-1 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{adding?<Loader2 className="h-4 w-4 animate-spin" />:<Plus className="h-4 w-4" />}Ajouter</button>
      </form>
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </div>

    {loading ? <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto" /></div>
    : <>
      {["tech","soft","language"].map(cat => {
        const items = byCategory(cat);
        if (!items.length) return null;
        const label = {tech:"Compétences techniques",soft:"Soft skills",language:"Langues"}[cat];
        return <div key={cat} className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-900 mb-3">{label} ({items.length})</h2>
          <div className="flex flex-wrap gap-2">{items.map(s => <div key={s.id} className="flex items-center gap-1 group">
            <SkillBadge name={s.name} category={s.category} />
            <button onClick={()=>deleteSkill(s.id)} className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"><Trash2 className="h-3 w-3" /></button>
          </div>)}</div>
        </div>;
      })}
      {(!skills || skills.length === 0) && <p className="text-center text-gray-400 py-8">Aucune compétence. Ajoutez-en ci-dessus.</p>}
    </>}
  </div></Layout>;
}
