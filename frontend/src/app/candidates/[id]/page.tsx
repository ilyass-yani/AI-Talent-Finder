"use client";
import { use } from "react";
import Layout from "@/components/Layout";
import { useApi } from "@/hooks/useApi";
import { candidatesApi } from "@/services/candidates";
import { ArrowLeft, Mail, ExternalLink, Code2, FileText } from "lucide-react";
import Link from "next/link";

export default function CandidateDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: candidate, loading } = useApi(() => candidatesApi.getCandidate(Number(id)), [id]);

  if (loading) return <Layout><div className="flex justify-center py-20"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div></Layout>;
  if (!candidate) return <Layout><div className="text-center py-20 text-gray-500">Candidat non trouvé.</div></Layout>;

  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <Link href="/candidates" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-indigo-600"><ArrowLeft className="h-4 w-4" /> Retour</Link>
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h1 className="text-2xl font-bold text-gray-900">{candidate.full_name}</h1>
      <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-gray-500">
        {candidate.email && <a href={`mailto:${candidate.email}`} className="flex items-center gap-1 hover:text-indigo-600"><Mail className="h-4 w-4" />{candidate.email}</a>}
        {candidate.phone && <span>{candidate.phone}</span>}
        {candidate.linkedin_url && <a href={candidate.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-blue-600"><ExternalLink className="h-4 w-4" />LinkedIn</a>}
        {candidate.github_url && <a href={candidate.github_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-gray-800"><Code2 className="h-4 w-4" />GitHub</a>}
      </div>
      {candidate.cv_path && <div className="flex items-center gap-2 mt-3 text-xs text-gray-400"><FileText className="h-4 w-4" />CV: {candidate.cv_path}</div>}
      <p className="text-xs text-gray-400 mt-2">Créé le {new Date(candidate.created_at).toLocaleDateString("fr-FR")}</p>
    </div>
    {candidate.raw_text && <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Texte extrait du CV</h2>
      <pre className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">{candidate.raw_text}</pre>
    </div>}
    <p className="text-xs text-gray-400 text-center">Données de <code className="bg-gray-100 px-1 rounded">GET /candidates/{id}</code></p>
  </div></Layout>;
}
