"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import { useApi } from "@/hooks/useApi";
import { jobsApi } from "@/services/jobs";
import { Plus, Trash2, Loader2 } from "lucide-react";

export default function JobsPage() {
  const { data: jobs, loading, refetch } = useApi(() => jobsApi.getJobs(), []);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [adding, setAdding] = useState(false);

  const addJob = async (e: React.FormEvent) => {
    e.preventDefault(); if (!title.trim()) return;
    setAdding(true);
    try { await jobsApi.createJob({ title: title.trim(), description: desc.trim() }); setTitle(""); setDesc(""); refetch(); }
    catch { alert("Erreur lors de la création."); }
    finally { setAdding(false); }
  };

  const deleteJob = async (id: number) => {
    if (!confirm("Supprimer ce critère ?")) return;
    try { await jobsApi.deleteJob(id); refetch(); } catch { alert("Erreur."); }
  };

  return <Layout><div className="max-w-3xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Critères de poste</h1><p className="text-sm text-gray-500 mt-1">Gérer les offres — <code className="bg-gray-100 px-1 rounded text-xs">GET/POST/DELETE /jobs/</code></p></div>

    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <form onSubmit={addJob} className="space-y-3">
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Titre du poste</label><input type="text" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Ex: Développeur Full-Stack Senior" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Description</label><textarea value={desc} onChange={e=>setDesc(e.target.value)} rows={3} placeholder="Décrivez les responsabilités et compétences recherchées..." className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none resize-none" /></div>
        <button type="submit" disabled={adding||!title.trim()} className="flex items-center gap-1 px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{adding?<Loader2 className="h-4 w-4 animate-spin" />:<Plus className="h-4 w-4" />}Créer le critère</button>
      </form>
    </div>

    {loading ? <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto" /></div>
    : (jobs && jobs.length > 0) ? <div className="space-y-3">{jobs.map(j => (
      <div key={j.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between">
          <div><h3 className="font-semibold text-gray-900">{j.title}</h3><p className="text-sm text-gray-500 mt-1">{j.description || "Pas de description"}</p><p className="text-xs text-gray-400 mt-2">Créé le {new Date(j.created_at).toLocaleDateString("fr-FR")}</p></div>
          <button onClick={()=>deleteJob(j.id)} className="text-gray-400 hover:text-red-500 p-1"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
    ))}</div>
    : <p className="text-center text-gray-400 py-12">Aucun critère de poste. Créez-en un ci-dessus.</p>}
  </div></Layout>;
}
