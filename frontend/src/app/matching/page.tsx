"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Layout from "@/components/Layout";
import { useApi } from "@/hooks/useApi";
import { criteriaApi, type Criteria, type CriteriaSkillInput } from "@/services/criteria";
import { matchingApi, type RankAllResult } from "@/services/matching";
import { skillsApi, type Skill } from "@/services/skills";
import {
  BarChart3,
  Check,
  ChevronDown,
  ChevronUp,
  Play,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Cell, Legend, Pie, PieChart, Tooltip } from "recharts";

const palette = [
  "#2563eb", "#0f766e", "#f59e0b", "#7c3aed",
  "#ef4444", "#14b8a6", "#ec4899", "#22c55e",
];

type FormSkill = CriteriaSkillInput & { key: string };

export default function MatchingPage() {
  const { data: skills } = useApi(() => skillsApi.getSkills(), []);
  const { data: criteriaList, loading: criteriaLoading, refetch: refetchCriteria } = useApi(
    () => criteriaApi.getCriteria(),
    [],
  );

  const [selectedCriteriaId, setSelectedCriteriaId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<FormSkill[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const [isExpanded, setIsExpanded] = useState(true);
  const [saving, setSaving] = useState(false);
  const [rankAllLoading, setRankAllLoading] = useState(false);
  const [rankAllResults, setRankAllResults] = useState<RankAllResult[]>([]);
  const [error, setError] = useState("");
  const [isChartMounted, setIsChartMounted] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    setIsChartMounted(true);
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    const node = chartRef.current;
    const updateSize = () => {
      const rect = node.getBoundingClientRect();
      setChartSize({ width: Math.floor(rect.width), height: Math.floor(rect.height) });
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!selectedCriteriaId || !criteriaList?.length) return;
    const criteria = criteriaList.find(item => item.id === selectedCriteriaId);
    if (!criteria) return;
    setTitle(criteria.title);
    setDescription(criteria.description || "");
    setSelectedSkills(
      criteria.required_skills.map(skill => ({
        key: `${skill.name}-${skill.weight}`,
        name: skill.name,
        weight: skill.weight,
      })),
    );
  }, [criteriaList, selectedCriteriaId]);

  const suggestions = useMemo(() => {
    const query = skillQuery.trim().toLowerCase();
    const used = new Set(selectedSkills.map(s => s.name.toLowerCase()));
    return (skills || [])
      .filter((s: Skill) => !used.has(s.name.toLowerCase()))
      .filter((s: Skill) => !query || s.name.toLowerCase().includes(query))
      .slice(0, 8);
  }, [skills, skillQuery, selectedSkills]);

  const pieData = selectedSkills.map(s => ({ name: s.name, value: s.weight }));
  const totalWeight = selectedSkills.reduce((sum, s) => sum + s.weight, 0);

  const addSkill = (skillName: string, weight = 50) => {
    setSelectedSkills(cur => {
      if (cur.some(s => s.name.toLowerCase() === skillName.toLowerCase())) return cur;
      return [...cur, { key: `${skillName}-${Date.now()}`, name: skillName, weight }];
    });
    setSkillQuery("");
  };

  const updateSkillWeight = (skillKey: string, weight: number) =>
    setSelectedSkills(cur => cur.map(s => (s.key === skillKey ? { ...s, weight } : s)));

  const removeSkill = (skillKey: string) =>
    setSelectedSkills(cur => cur.filter(s => s.key !== skillKey));

  const resetForm = () => {
    setSelectedCriteriaId(null);
    setTitle("");
    setDescription("");
    setSelectedSkills([]);
    setRankAllResults([]);
    setError("");
  };

  const saveCriteria = async () => {
    if (!title.trim()) { setError("Ajoutez un titre pour vos critères."); return; }
    if (selectedSkills.length === 0) { setError("Ajoutez au moins une compétence."); return; }
    setSaving(true);
    setError("");
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        required_skills: selectedSkills.map(s => ({ name: s.name, weight: s.weight })),
      };
      const response = selectedCriteriaId
        ? await criteriaApi.updateCriteria(selectedCriteriaId, payload)
        : await criteriaApi.createCriteria(payload);
      setSelectedCriteriaId(response.data.id);
      await refetchCriteria();
    } catch {
      setError("Impossible d'enregistrer ces critères.");
    } finally {
      setSaving(false);
    }
  };

  const launchRankAll = async (criteriaId?: number) => {
    const id = criteriaId ?? selectedCriteriaId;
    if (!id) { setError("Sélectionnez ou créez une matrice de critères."); return; }
    setRankAllLoading(true);
    setError("");
    try {
      const response = await matchingApi.rankAll(id);
      setRankAllResults(response.data);
    } catch {
      setError("Impossible de lancer le classement.");
    } finally {
      setRankAllLoading(false);
    }
  };

  const loadCriteria = async (criteria: Criteria) => {
    setError("");
    setRankAllResults([]);
    try {
      const response = await criteriaApi.getCriteriaById(criteria.id);
      const detail = response.data;
      setSelectedCriteriaId(detail.id);
      setTitle(detail.title);
      setDescription(detail.description || "");
      setSelectedSkills(
        detail.required_skills.map(skill => ({
          key: `${skill.name}-${skill.weight}`,
          name: skill.name,
          weight: skill.weight,
        })),
      );
    } catch {
      setError("Impossible de charger ces critères.");
    }
  };

  const loadAndRank = async (criteria: Criteria) => {
    await loadCriteria(criteria);
    await launchRankAll(criteria.id);
  };

  const deleteCriteria = async (criteriaId: number) => {
    if (!confirm("Supprimer cet ensemble de critères ?")) return;
    try {
      await criteriaApi.deleteCriteria(criteriaId);
      if (selectedCriteriaId === criteriaId) resetForm();
      await refetchCriteria();
    } catch {
      setError("Impossible de supprimer ces critères.");
    }
  };

  return (
    <Layout>
      <div className="mx-auto max-w-7xl space-y-8">

        {/* ── Hero ────────────────────────────────────────────────────────── */}
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 px-6 py-8 text-white shadow-2xl md:px-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.35),_transparent_34%),radial-gradient(circle_at_bottom_left,_rgba(16,185,129,0.24),_transparent_30%)]" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-100">
                <Sparkles className="h-3.5 w-3.5" />
                Matching personnalisable
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">
                  Construisez vos critères, puis lancez le classement instantané.
                </h1>
                <p className="mt-3 max-w-2xl text-sm text-slate-200 md:text-base">
                  Sélectionnez des compétences, attribuez des poids, visualisez la répartition et classez vos
                  candidats selon un score cosinus pondéré.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[38rem] lg:grid-cols-2 xl:grid-cols-4">
              <Stat label="Critères" value={criteriaList?.length ?? 0} />
              <Stat label="Compétences" value={selectedSkills.length} />
              <Stat label="Poids total" value={`${totalWeight}%`} />
              <Stat label="Classés" value={rankAllResults.length} />
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}

        {/* ── Form + Pie ──────────────────────────────────────────────────── */}
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">

          {/* Criteria form */}
          <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Matrice de critères</h2>
                <p className="text-sm text-slate-500">Compétences et poids du recruteur.</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsExpanded(v => !v)}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {isExpanded ? "Réduire" : "Développer"}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  Nouveau
                </button>
              </div>
            </div>

            {isExpanded && (
              <div className="space-y-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Nom de la matrice</label>
                    <input
                      value={title}
                      onChange={e => setTitle(e.target.value)}
                      placeholder="Ex: Data Engineer / France"
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Description</label>
                    <input
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                      placeholder="Contexte du poste, équipe, contraintes"
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                    />
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <label className="mb-2 block text-sm font-medium text-slate-700">Rechercher une compétence</label>
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
                    <input
                      value={skillQuery}
                      onChange={e => setSkillQuery(e.target.value)}
                      placeholder="Python, React, Docker, Anglais..."
                      className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-4 text-sm outline-none transition focus:border-sky-400 focus:ring-4 focus:ring-sky-100"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {suggestions.map(skill => (
                      <button
                        key={skill.id}
                        type="button"
                        onClick={() => addSkill(skill.name, 50)}
                        className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-800"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        {skill.name}
                      </button>
                    ))}
                    {!suggestions.length && skillQuery.trim() && (
                      <span className="text-sm text-slate-500">Aucune compétence trouvée.</span>
                    )}
                  </div>
                </div>

                <div className="space-y-3">
                  {selectedSkills.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
                      Commencez par ajouter des compétences depuis le dictionnaire.
                    </div>
                  ) : (
                    selectedSkills.map(skill => (
                      <div key={skill.key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-slate-900">{skill.name}</div>
                            <div className="text-xs text-slate-500">Poids : {skill.weight}%</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeSkill(skill.key)}
                            className="rounded-xl p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        <div className="mt-3 flex items-center gap-3">
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={skill.weight}
                            onChange={e => updateSkillWeight(skill.key, Number(e.target.value))}
                            className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-sky-600"
                          />
                          <div className="w-12 text-right text-sm font-semibold text-slate-700">{skill.weight}%</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={saveCriteria}
                    disabled={saving}
                    className="inline-flex items-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Check className="h-4 w-4" />
                    {saving ? "Enregistrement..." : selectedCriteriaId ? "Mettre à jour" : "Créer les critères"}
                  </button>
                  <button
                    type="button"
                    onClick={() => launchRankAll()}
                    disabled={rankAllLoading || !selectedCriteriaId}
                    className="inline-flex items-center gap-2 rounded-2xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Play className="h-4 w-4" />
                    {rankAllLoading ? "Classement en cours..." : "Lancer le classement"}
                  </button>
                </div>
              </div>
            )}
          </section>

          {/* Pie chart + saved criteria list */}
          <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Répartition des poids</h2>
                <p className="text-sm text-slate-500">Distribution en temps réel.</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-600">
                Total : {totalWeight}%
              </div>
            </div>

            <div ref={chartRef} className="h-80 min-w-0 rounded-3xl border border-slate-200 bg-slate-50 p-4">
              {isChartMounted && pieData.length > 0 && chartSize.width > 0 && chartSize.height > 0 ? (
                <div className="flex h-full items-center justify-center">
                  <PieChart
                    width={Math.max(280, chartSize.width - 32)}
                    height={Math.max(240, chartSize.height - 24)}
                  >
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={60}
                      outerRadius={110}
                      paddingAngle={3}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={entry.name} fill={palette[index % palette.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">
                  Ajoutez des compétences pour voir la distribution.
                </div>
              )}
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">
                Critères enregistrés
              </h3>
              <div className="space-y-3">
                {(criteriaList || []).length === 0 && !criteriaLoading && (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                    Aucun ensemble de critères enregistré.
                  </div>
                )}
                {criteriaLoading && (
                  <div className="rounded-2xl border border-slate-200 px-4 py-6 text-sm text-slate-500">
                    Chargement des critères...
                  </div>
                )}
                {(criteriaList || []).map(criteria => (
                  <div
                    key={criteria.id}
                    onClick={() => void loadCriteria(criteria)}
                    onKeyDown={e => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        void loadCriteria(criteria);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    className={`w-full cursor-pointer rounded-2xl border px-4 py-4 text-left transition ${
                      selectedCriteriaId === criteria.id
                        ? "border-sky-300 bg-sky-50 shadow-sm"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{criteria.title}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {criteria.required_skills.length} compétence(s)
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            void loadAndRank(criteria);
                          }}
                          className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                        >
                          Classer
                        </button>
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            void deleteCriteria(criteria.id);
                          }}
                          className="rounded-xl border border-slate-200 p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    {criteria.description && (
                      <div className="mt-2 text-sm text-slate-500">{criteria.description}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* ── ONE ranking table ────────────────────────────────────────────── */}
        <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Classement de mes candidats</h2>
              <p className="text-sm text-slate-500">
                Tous vos candidats classés du meilleur score au plus faible, basé sur les compétences
                extraites de leur CV.
              </p>
            </div>
            <button
              type="button"
              onClick={() => launchRankAll()}
              disabled={!selectedCriteriaId || rankAllLoading}
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <BarChart3 className="h-4 w-4" />
              Rafraîchir
            </button>
          </div>

          {rankAllLoading ? (
            <div className="rounded-2xl border border-slate-200 px-4 py-10 text-center text-sm text-slate-500">
              Calcul des scores en cours...
            </div>
          ) : rankAllResults.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500">
              Sélectionnez ou créez une matrice de critères puis cliquez sur{" "}
              <span className="font-semibold">Lancer le classement</span>.
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <th className="px-4 py-3">Rang</th>
                    <th className="px-4 py-3">Nom</th>
                    <th className="hidden px-4 py-3 sm:table-cell">Email</th>
                    <th className="px-4 py-3">Score</th>
                    <th className="hidden px-4 py-3 md:table-cell">Compétences trouvées</th>
                    <th className="hidden px-4 py-3 lg:table-cell">Manquantes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rankAllResults.map(r => (
                    <tr key={r.candidate_id} className="transition-colors hover:bg-slate-50">
                      <td className="px-4 py-3 font-bold text-slate-400">#{r.rank}</td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{r.full_name}</td>
                      <td className="hidden px-4 py-3 text-slate-500 sm:table-cell">{r.email}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-20 overflow-hidden rounded-full bg-slate-100">
                            <div
                              className="h-full rounded-full bg-sky-500"
                              style={{ width: `${Math.min(r.score, 100)}%` }}
                            />
                          </div>
                          <span
                            className={`font-semibold ${
                              r.score >= 70
                                ? "text-emerald-700"
                                : r.score >= 40
                                  ? "text-amber-700"
                                  : "text-slate-400"
                            }`}
                          >
                            {Math.round(r.score)}%
                          </span>
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 md:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {r.matched_skills.slice(0, 3).map(skill => (
                            <span
                              key={skill}
                              className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"
                            >
                              {skill}
                            </span>
                          ))}
                          {r.matched_skills.length > 3 && (
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                              +{r.matched_skills.length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="hidden px-4 py-3 lg:table-cell">
                        <div className="flex flex-wrap gap-1">
                          {r.missing_skills.slice(0, 2).map(skill => (
                            <span
                              key={skill}
                              className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </Layout>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
      <div className="text-xs uppercase tracking-[0.24em] text-slate-300">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}
