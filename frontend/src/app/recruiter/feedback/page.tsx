"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { feedbackApi, type BiasReport, type FeedbackStats, type RetrainingReadiness, type SkillRecommendationItem } from "@/services/feedback";
import { jobsApi, type JobCriteria } from "@/services/jobs";
import { getErrorMessage } from "@/utils/errorHandler";
import { Activity, ArrowUpRight, BadgeCheck, BarChart3, BrainCircuit, DatabaseZap, FileDown, Loader2, MessageSquareMore, ShieldAlert, Sparkles } from "lucide-react";

type Decision = "accepted" | "rejected" | "no_action";

export default function RecruiterFeedbackPage() {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [readiness, setReadiness] = useState<RetrainingReadiness | null>(null);
  const [biasReport, setBiasReport] = useState<BiasReport | null>(null);
  const [criteriaSummary, setCriteriaSummary] = useState<Record<string, unknown> | null>(null);
  const [latestCriteria, setLatestCriteria] = useState<JobCriteria | null>(null);
  const [trendingSkills, setTrendingSkills] = useState<SkillRecommendationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [criteriaId, setCriteriaId] = useState('');
  const [candidateId, setCandidateId] = useState('');
  const [modelScore, setModelScore] = useState('');
  const [modelDecision, setModelDecision] = useState<'accepted' | 'review' | 'rejected'>('review');
  const [recruiterDecision, setRecruiterDecision] = useState<Decision>('accepted');
  const [overrideScore, setOverrideScore] = useState('');
  const [feedbackReason, setFeedbackReason] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [currentSkills, setCurrentSkills] = useState('');
  const [missingSkills, setMissingSkills] = useState('');
  const [gapCandidateSkills, setGapCandidateSkills] = useState('');
  const [gapRequiredSkills, setGapRequiredSkills] = useState('');
  const [jobDomain, setJobDomain] = useState('backend');

  const dashboardCards = useMemo(() => [
    {
      label: 'Feedback total',
      value: stats?.total_feedback ?? '—',
      accent: 'from-indigo-500 to-violet-600',
      icon: Activity,
    },
    {
      label: 'Overrides',
      value: stats ? `${stats.override_rate}` : '—',
      accent: 'from-amber-500 to-orange-500',
      icon: ArrowUpRight,
    },
    {
      label: 'Retraining',
      value: readiness?.ready ? 'Ready' : 'Collecting',
      accent: readiness?.ready ? 'from-emerald-500 to-teal-600' : 'from-slate-500 to-slate-700',
      icon: BrainCircuit,
    },
    {
      label: 'Bias status',
      value: biasReport?.alerts?.length ? 'Review' : 'Stable',
      accent: biasReport?.alerts?.length ? 'from-rose-500 to-pink-600' : 'from-cyan-500 to-blue-600',
      icon: ShieldAlert,
    },
  ], [biasReport?.alerts?.length, readiness?.ready, stats]);

  useEffect(() => {
    void loadOverview();
  }, []);

  useEffect(() => {
    if (!latestCriteria) {
      return;
    }

    setCriteriaId(String(latestCriteria.id));
    setJobTitle(latestCriteria.title);
    void loadCriteriaSummary(latestCriteria.id);
  }, [latestCriteria]);

  const loadOverview = async () => {
    setLoading(true);
    setError(null);

    try {
      const [statsResponse, readinessResponse, biasResponse, jobsResponse] = await Promise.all([
        feedbackApi.getStatistics(),
        feedbackApi.getRetrainingReadiness(),
        feedbackApi.getBiasSummary(),
        jobsApi.getJobs(),
      ]);

      setStats(statsResponse.data);
      setReadiness(readinessResponse.data);
      setBiasReport((biasResponse.data as unknown as BiasReport) ?? null);
      setLatestCriteria(jobsResponse.data?.[0] ?? null);
    } catch (fetchError) {
      setError(getErrorMessage(fetchError));
    } finally {
      setLoading(false);
    }
  };

  const loadCriteriaSummary = async (id: number) => {
    try {
      const response = await feedbackApi.getCriteriaSummary(id);
      setCriteriaSummary(response.data);
    } catch (fetchError) {
      console.warn('Unable to load criteria summary:', fetchError);
      setCriteriaSummary(null);
    }
  };

  const handleManualFeedback = async (event: React.FormEvent) => {
    event.preventDefault();
    setMessage(null);
    setError(null);

    if (!criteriaId || !candidateId || !modelScore) {
      setError('Veuillez compléter au minimum le critère, le candidat et le score modèle.');
      return;
    }

    setWorking(true);
    try {
      await feedbackApi.recordDecision({
        criteria_id: Number(criteriaId),
        candidate_id: Number(candidateId),
        model_predicted_score: Number(modelScore),
        model_predicted_decision: modelDecision,
        recruiter_decision: recruiterDecision,
        recruiter_score_override: overrideScore ? Number(overrideScore) : undefined,
        feedback_reason: feedbackReason || undefined,
      });

      setMessage('Feedback enregistré avec succès.');
      await loadOverview();
      await loadCriteriaSummary(Number(criteriaId));
    } catch (recordError) {
      setError(getErrorMessage(recordError));
    } finally {
      setWorking(false);
    }
  };

  const handleSkillRecommendations = async () => {
    setWorking(true);
    setMessage(null);
    setError(null);

    try {
      const response = await feedbackApi.recommendSkills(jobTitle, currentSkills, missingSkills, 5);
      setTrendingSkills(response.data);
      setMessage('Recommandations de skills actualisées.');
    } catch (recommendationError) {
      setError(getErrorMessage(recommendationError));
    } finally {
      setWorking(false);
    }
  };

  const handleGapAnalysis = async () => {
    setWorking(true);
    setMessage(null);
    setError(null);

    try {
      const response = await feedbackApi.analyzeGap(
        gapCandidateSkills.split(',').map((skill) => skill.trim()).filter(Boolean),
        gapRequiredSkills.split(',').map((skill) => skill.trim()).filter(Boolean),
      );
      setCriteriaSummary(response.data);
      setMessage('Analyse des écarts mise à jour.');
    } catch (gapError) {
      setError(getErrorMessage(gapError));
    } finally {
      setWorking(false);
    }
  };

  const handleBiasAnalysis = async () => {
    setWorking(true);
    setMessage(null);
    setError(null);

    try {
      const response = await feedbackApi.analyzeBias(30);
      setBiasReport(response.data);
      setMessage('Audit biais exécuté.');
    } catch (biasError) {
      setError(getErrorMessage(biasError));
    } finally {
      setWorking(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setMessage(null);
    setError(null);

    try {
      const response = await feedbackApi.exportRetrainingData(undefined, 20);
      setMessage(`Export prêt: ${(response.data as { output_path?: string }).output_path ?? 'généré côté backend'}`);
      await loadOverview();
    } catch (exportError) {
      setError(getErrorMessage(exportError));
    } finally {
      setExporting(false);
    }
  };

  const handleRetraining = async () => {
    setWorking(true);
    setMessage(null);
    setError(null);

    try {
      const response = await feedbackApi.triggerRetraining(120);
      setMessage(`Réentraînement déclenché: ${(response.data as { status?: string }).status ?? 'ok'}`);
      await loadOverview();
    } catch (trainError) {
      setError(getErrorMessage(trainError));
    } finally {
      setWorking(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-8">
        <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-8 text-white shadow-2xl">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(99,102,241,0.18),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(45,212,191,0.12),_transparent_22%)]" />
          <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-100">
                <Sparkles className="h-4 w-4" />
                Phase 3 - Feedback Loop
              </div>
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
                Boucle de feedback, recommandations et conformité
              </h1>
              <p className="mt-4 text-base leading-7 text-slate-300 sm:text-lg">
                Enregistrez les décisions recruteur, préparez le réentraînement, surveillez les biais et exportez un jeu de données propre pour la suite du pipeline.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/recruiter/chatbot" className="inline-flex items-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-900 shadow-lg transition hover:bg-slate-100">
                <span className="inline-flex items-center gap-2"><MessageSquareMore className="h-4 w-4" />Chatbot IA</span>
              </Link>
              <Link href="/recruiter/export" className="inline-flex items-center rounded-full border border-white/20 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
                Export existant
              </Link>
            </div>
          </div>
        </section>

        {(message || error) && (
          <div className={`rounded-2xl border p-4 ${error ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`}>
            {error ?? message}
          </div>
        )}

        <details className="rounded-3xl border border-slate-200 bg-white shadow-sm">
          <summary className="cursor-pointer list-none px-6 py-4 text-sm font-semibold text-slate-700">
            Monitoring avancé
          </summary>
          <div className="grid gap-4 border-t border-slate-100 p-6 md:grid-cols-2 xl:grid-cols-4">
            {dashboardCards.map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.label} className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
                  <div className={`mb-4 inline-flex rounded-2xl bg-gradient-to-br ${card.accent} p-3 text-white`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="text-sm font-medium text-slate-500">{card.label}</div>
                  <div className="mt-1 text-2xl font-black text-slate-900">{card.value}</div>
                </div>
              );
            })}
          </div>
        </details>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Enregistrer un feedback</h2>
                <p className="text-sm text-slate-500">Capturez la vérité terrain pour alimenter l’apprentissage continu.</p>
              </div>
              <BadgeCheck className="h-6 w-6 text-emerald-500" />
            </div>

            <form className="grid gap-4 md:grid-cols-2" onSubmit={handleManualFeedback}>
              <Field label="Criteria ID" value={criteriaId} onChange={setCriteriaId} placeholder="12" />
              <Field label="Candidate ID" value={candidateId} onChange={setCandidateId} placeholder="84" />
              <Field label="Score modèle" value={modelScore} onChange={setModelScore} placeholder="62.5" />
              <Field label="Score override" value={overrideScore} onChange={setOverrideScore} placeholder="85" optional />

              <SelectField label="Décision modèle" value={modelDecision} onChange={setModelDecision} options={["accepted", "review", "rejected"]} />
              <SelectField label="Décision recruteur" value={recruiterDecision} onChange={setRecruiterDecision} options={["accepted", "rejected", "no_action"]} />

              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-semibold text-slate-700">Raison du feedback</label>
                <textarea
                  value={feedbackReason}
                  onChange={(event) => setFeedbackReason(event.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
                  placeholder="Pourquoi la décision recruteur diffère du score modèle ?"
                />
              </div>

              <div className="md:col-span-2 flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={working}
                  className="inline-flex items-center justify-center rounded-full bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {working ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Enregistrer le feedback
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void loadOverview();
                  }}
                  className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Rafraîchir les stats
                </button>
              </div>
            </form>
          </div>

          <details className="rounded-3xl border border-slate-200 bg-white p-0 shadow-sm">
            <summary className="cursor-pointer list-none px-6 py-4 text-sm font-semibold text-slate-700">
              Actions avancées et monitoring
            </summary>
            <div className="space-y-6 border-t border-slate-100 p-6 pt-0">
              <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-sm">
                <div className="mb-4 flex items-center gap-3">
                  <DatabaseZap className="h-5 w-5 text-cyan-300" />
                  <h2 className="text-xl font-bold">Réentraînement et export</h2>
                </div>
                <p className="text-sm leading-6 text-slate-300">
                  Exportez le dataset JSONL ou déclenchez un réentraînement dès que le volume est suffisant.
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      void handleExport();
                    }}
                    disabled={exporting || working}
                    className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
                    Export JSONL
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      void handleRetraining();
                    }}
                    disabled={working}
                    className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {working ? <Loader2 className="h-4 w-4 animate-spin" /> : <BrainCircuit className="h-4 w-4" />}
                    Réentraîner
                  </button>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center gap-3">
                  <BarChart3 className="h-5 w-5 text-indigo-600" />
                  <h2 className="text-xl font-bold text-slate-900">État du système</h2>
                </div>
                {loading ? (
                  <div className="flex items-center gap-3 text-slate-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Chargement des métriques...
                  </div>
                ) : (
                  <div className="space-y-3 text-sm text-slate-600">
                    <MetricLine label="Total feedback" value={stats?.total_feedback ?? '—'} />
                    <MetricLine label="Overrides" value={stats?.override_count ?? '—'} />
                    <MetricLine label="Readiness" value={readiness?.ready ? 'Prêt' : 'Collecte en cours'} />
                    <MetricLine label="Bias alerts" value={biasReport?.alerts?.length ?? 0} />
                  </div>
                )}
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center gap-3">
                  <ShieldAlert className="h-5 w-5 text-rose-500" />
                  <h2 className="text-2xl font-bold text-slate-900">Audit biais</h2>
                </div>
                <p className="text-sm text-slate-500">Surveillez les disparités et déclenchez un audit rapide en un clic.</p>
                <button
                  type="button"
                  onClick={() => {
                    void handleBiasAnalysis();
                  }}
                  disabled={working}
                  className="mt-4 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Lancer l'audit biais
                </button>

                {biasReport?.alerts?.length ? (
                  <div className="mt-4 space-y-3">
                    {biasReport.alerts.map((alert) => (
                      <div key={`${alert.alert_type}-${alert.affected_group}`} className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
                        <div className="flex items-center justify-between gap-2">
                          <strong>{alert.alert_type}</strong>
                          <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold uppercase tracking-wide text-rose-700">{alert.severity}</span>
                        </div>
                        <p className="mt-2">{alert.message}</p>
                        <p className="mt-2 text-xs text-rose-700">{alert.recommendation}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                    Aucun signal biais affiché ou audit non lancé.
                  </div>
                )}
              </div>
            </div>
          </details>
        </section>

        <section className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Recommandations skills</h2>
                <p className="text-sm text-slate-500">Trends, gaps et certifications par rôle.</p>
              </div>
              <Sparkles className="h-5 w-5 text-amber-500" />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Job title" value={jobTitle} onChange={setJobTitle} placeholder="Senior Data Scientist" />
              <Field label="Skills actuelles" value={currentSkills} onChange={setCurrentSkills} placeholder="Python, SQL" />
              <Field label="Skills manquantes" value={missingSkills} onChange={setMissingSkills} placeholder="TensorFlow, MLOps" />
              <Field label="Domaine" value={jobDomain} onChange={setJobDomain} placeholder="backend" />
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => {
                  void handleSkillRecommendations();
                }}
                disabled={working}
                className="rounded-full bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Recommander les skills
              </button>
              <button
                type="button"
                onClick={async () => {
                  setWorking(true);
                  setMessage(null);
                  setError(null);
                  try {
                    const response = await feedbackApi.getComplementarySkills(currentSkills, jobDomain);
                    const items = (response.data as Array<{ primary_skill: string; complementary: string; reason: string }>).map((item) => ({
                      skill_name: item.complementary,
                      frequency: 0,
                      trending_score: 0,
                      category: 'tech',
                      reason: `${item.primary_skill} → ${item.reason}`,
                      average_proficiency: 'intermediate',
                    }));
                    setTrendingSkills(items);
                    setMessage('Compétences complémentaires mises à jour.');
                  } catch (complementaryError) {
                    setError(getErrorMessage(complementaryError));
                  } finally {
                    setWorking(false);
                  }
                }}
                disabled={working}
                className="rounded-full border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Compétences complémentaires
              </button>
            </div>

            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
                <MessageSquareMore className="h-4 w-4 text-indigo-500" />
                Analyse des écarts
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Skills candidat" value={gapCandidateSkills} onChange={setGapCandidateSkills} placeholder="Python, SQL, Docker" />
                <Field label="Skills requis" value={gapRequiredSkills} onChange={setGapRequiredSkills} placeholder="Python, SQL, Docker, Kubernetes" />
              </div>
              <button
                type="button"
                onClick={() => {
                  void handleGapAnalysis();
                }}
                disabled={working}
                className="mt-3 rounded-full border border-indigo-200 bg-white px-4 py-2.5 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Lancer l'analyse des écarts
              </button>
            </div>

            <div className="mt-5 space-y-3">
              {trendingSkills.length > 0 ? trendingSkills.map((item) => (
                <div key={item.skill_name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-slate-900">{item.skill_name}</div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.category}</div>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{item.reason}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                    <span className="rounded-full bg-white px-3 py-1">Fréquence: {item.frequency}</span>
                    <span className="rounded-full bg-white px-3 py-1">Trend: {item.trending_score.toFixed(2)}</span>
                    <span className="rounded-full bg-white px-3 py-1">Niveau: {item.average_proficiency}</span>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                  Lancez une recommandation pour afficher les tendances et les gaps.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <ShieldAlert className="h-5 w-5 text-rose-500" />
                <h2 className="text-2xl font-bold text-slate-900">Audit biais</h2>
              </div>
              <p className="text-sm text-slate-500">Surveillez les disparités et déclenchez un audit rapide en un clic.</p>
              <button
                type="button"
                onClick={() => {
                  void handleBiasAnalysis();
                }}
                disabled={working}
                className="mt-4 rounded-full bg-rose-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Lancer l'audit biais
              </button>

              {biasReport?.alerts?.length ? (
                <div className="mt-4 space-y-3">
                  {biasReport.alerts.map((alert) => (
                    <div key={`${alert.alert_type}-${alert.affected_group}`} className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
                      <div className="flex items-center justify-between gap-2">
                        <strong>{alert.alert_type}</strong>
                        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold uppercase tracking-wide text-rose-700">{alert.severity}</span>
                      </div>
                      <p className="mt-2">{alert.message}</p>
                      <p className="mt-2 text-xs text-rose-700">{alert.recommendation}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                  Aucun signal biais affiché ou audit non lancé.
                </div>
              )}
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <FileDown className="h-5 w-5 text-cyan-600" />
                <h2 className="text-2xl font-bold text-slate-900">Résumé critères</h2>
              </div>
              {criteriaSummary ? (
                <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">{JSON.stringify(criteriaSummary, null, 2)}</pre>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                  Le résumé par critère apparaîtra ici après un feedback, une analyse d'écart ou un export.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </Layout>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  optional = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  optional?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-slate-700">
        {label}{optional ? ' (optionnel)' : ''}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
      />
    </label>
  );
}

function SelectField<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: T[];
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-slate-700">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
      >
        {options.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

function MetricLine({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <span>{label}</span>
      <strong className="text-slate-900">{value}</strong>
    </div>
  );
}