"use client";
import { useState } from "react";
import Layout from "@/components/Layout";
import ScoreGauge from "@/components/ScoreGauge";
import { useApi } from "@/hooks/useApi";
import { matchingApi } from "@/services/matching";
import { candidatesApi } from "@/services/candidates";
import { jobsApi } from "@/services/jobs";
import { Play, Loader2 } from "lucide-react";
import Link from "next/link";

export default function MatchingPage() {
  const { data: candidates } = useApi(() => candidatesApi.getCandidates(), []);
  const { data: jobs } = useApi(() => jobsApi.getJobs(), []);
  const { data: results, loading: loadingResults, refetch } = useApi(() => matchingApi.getMatchResults(), []);
  const [candidateId, setCandidateId] = useState("");
  const [criteriaId, setCriteriaId] = useState("");
  const [calculating, setCalculating] = useState(false);

  const calculate = async () => {
    if (!candidateId || !criteriaId) return;
    setCalculating(true);
    try { await matchingApi.calculateMatch(Number(candidateId), Number(criteriaId)); refetch(); }
    catch { alert("Erreur lors du calcul."); }
    finally { setCalculating(false); }
  };

  const sorted = [...(results || [])].sort((a, b) => b.score - a.score);
  const getName = (id: number) => candidates?.find(c => c.id === id)?.full_name || `Candidat #${id}`;
  const getJob = (id: number) => jobs?.find(j => j.id === id)?.title || `Poste #${id}`;

  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Matching</h1><p className="text-sm text-gray-500 mt-1">Calculer et voir les scores — <code className="bg-gray-100 px-1 rounded text-xs">/matching/</code></p></div>

    {/* Calculer un match */}
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h2 className="text-sm font-semibold text-gray-900 mb-3">Calculer un nouveau match</h2>
      <div className="flex items-end gap-3">
        <div className="flex-1"><label className="block text-xs text-gray-500 mb-1">Candidat</label><select value={candidateId} onChange={e=>setCandidateId(e.target.value)} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"><option value="">Sélectionner...</option>{(candidates||[]).map(c=><option key={c.id} value={c.id}>{c.full_name}</option>)}</select></div>
        <div className="flex-1"><label className="block text-xs text-gray-500 mb-1">Critère de poste</label><select value={criteriaId} onChange={e=>setCriteriaId(e.target.value)} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500"><option value="">Sélectionner...</option>{(jobs||[]).map(j=><option key={j.id} value={j.id}>{j.title}</option>)}</select></div>
        <button onClick={calculate} disabled={!candidateId||!criteriaId||calculating} className="flex items-center gap-1 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">{calculating?<Loader2 className="h-4 w-4 animate-spin" />:<Play className="h-4 w-4" />}Calculer</button>
      </div>
    </div>

    {/* Résultats */}
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Résultats ({sorted.length})</h2>
      {loadingResults ? <div className="text-center py-12"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto" /></div>
      : sorted.length === 0 ? <p className="text-center text-gray-400 py-12">Aucun résultat. Lancez un calcul ci-dessus.</p>
      : <div className="space-y-3">{sorted.map((r, i) => (
        <div key={r.id} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
          <span className="text-lg font-bold text-gray-300 w-8 text-right">#{i+1}</span>
          <ScoreGauge score={r.score} size="sm" />
          <div className="flex-1">
            <Link href={`/candidates/${r.candidate_id}`} className="font-semibold text-gray-900 hover:text-indigo-600">{getName(r.candidate_id)}</Link>
            <p className="text-xs text-gray-500">Poste: {getJob(r.criteria_id)}</p>
            {r.explanation && <p className="text-xs text-gray-400 mt-1">{r.explanation}</p>}
          </div>
          <span className="text-sm font-bold text-indigo-600">{Math.round(r.score * 100)}%</span>
        </div>
      ))}</div>}
    </div>
  </div></Layout>;
}
