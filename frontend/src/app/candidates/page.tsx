"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import { useApi } from "@/hooks/useApi";
import { candidatesApi } from "@/services/candidates";
import { Search, Trash2, ExternalLink, Code2, Mail } from "lucide-react";
import Link from "next/link";

export default function CandidatesPage() {
  const { data: candidates, loading, refetch } = useApi(() => candidatesApi.getCandidates(), []);
  const [search, setSearch] = useState("");

  const filtered = (candidates || []).filter(c =>
    c.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    c.email?.toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = async (id: number) => {
    if (!confirm("Supprimer ce candidat ?")) return;
    try { await candidatesApi.deleteCandidate(id); refetch(); } catch { alert("Erreur lors de la suppression."); }
  };

  return <Layout><div className="max-w-4xl mx-auto space-y-5">
    <div><h1 className="text-2xl font-bold text-gray-900">Candidats</h1><p className="text-sm text-gray-500 mt-1">{filtered.length} candidat(s) — données du backend <code className="bg-gray-100 px-1 rounded text-xs">GET /candidates/</code></p></div>

    <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 py-2.5">
      <Search className="h-4 w-4 text-gray-400" />
      <input type="text" placeholder="Rechercher par nom ou email..." value={search} onChange={e => setSearch(e.target.value)} className="flex-1 text-sm outline-none" />
    </div>

    {loading ? <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto" /></div>
    : filtered.length === 0 ? <p className="text-center text-gray-400 py-12">Aucun candidat trouvé. <Link href="/candidates/upload" className="text-indigo-600 hover:underline">Uploader un CV</Link></p>
    : <div className="space-y-3">{filtered.map(c => (
      <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between">
          <div>
            <Link href={`/candidates/${c.id}`} className="text-base font-semibold text-gray-900 hover:text-indigo-600 transition-colors">{c.full_name}</Link>
            <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
              {c.email && <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{c.email}</span>}
              {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-blue-600"><ExternalLink className="h-3.5 w-3.5" />LinkedIn</a>}
              {c.github_url && <a href={c.github_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-gray-800"><Code2 className="h-3.5 w-3.5" />GitHub</a>}
            </div>
            {c.phone && <p className="text-xs text-gray-400 mt-1">{c.phone}</p>}
          </div>
          <button onClick={() => handleDelete(c.id)} className="text-gray-400 hover:text-red-500 p-1"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
    ))}</div>}
  </div></Layout>;
}
