"use client";

import { useEffect, useMemo, useState } from "react";
import Layout from "@/components/Layout";
import ScoreGauge from "@/components/ScoreGauge";
import { useApi } from "@/hooks/useApi";
import { criteriaApi, type Criteria, type CriteriaSkillInput } from "@/services/criteria";
import { matchingApi, type CriteriaMatchResult } from "@/services/matching";
import { skillsApi, type Skill } from "@/services/skills";
import {
  BarChart3,
  Check,
  ChevronDown,
  ChevronUp,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Play,
} from "lucide-react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const palette = ["#2563eb", "#0f766e", "#f59e0b", "#7c3aed", "#ef4444", "#14b8a6", "#ec4899", "#22c55e"];

type FormSkill = CriteriaSkillInput & { key: string };

export default function MatchingPage() {
  const { data: skills } = useApi(() => skillsApi.getSkills(), []);
  const { data: criteriaList, loading: criteriaLoading, refetch: refetchCriteria } = useApi(() => criteriaApi.getCriteria(), []);
  const [selectedCriteriaId, setSelectedCriteriaId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<FormSkill[]>([]);
  const [skillQuery, setSkillQuery] = useState("");
  const [isExpanded, setIsExpanded] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningMatching, setRunningMatching] = useState(false);
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  const [results, setResults] = useState<CriteriaMatchResult[]>([]);
  const [error, setError] = useState("");

  const suggestions = useMemo(() => {
    const query = skillQuery.trim().toLowerCase();
    const used = new Set(selectedSkills.map(skill => skill.name.toLowerCase()));
    return (skills || [])
      .filter((skill: Skill) => !used.has(skill.name.toLowerCase()))
      .filter((skill: Skill) => !query || skill.name.toLowerCase().includes(query))
      .slice(0, 8);
  }, [skills, skillQuery, selectedSkills]);

  const pieData = selectedSkills.map(skill => ({ name: skill.name, value: skill.weight }));
  const totalWeight = selectedSkills.reduce((sum, skill) => sum + skill.weight, 0);

  useEffect(() => {
    if (!selectedCriteriaId || !criteriaList?.length) {
      return;
    }

    const criteria = criteriaList.find(item => item.id === selectedCriteriaId);
    if (!criteria) {
      return;
    }

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

  const addSkill = (skillName: string, weight = 50) => {
    setSelectedSkills(current => {
      if (current.some(skill => skill.name.toLowerCase() === skillName.toLowerCase())) {
        return current;
      }
      return [...current, { key: `${skillName}-${Date.now()}`, name: skillName, weight }];
    });
    setSkillQuery("");
  };

  const updateSkillWeight = (skillKey: string, weight: number) => {
    setSelectedSkills(current => current.map(skill => skill.key === skillKey ? { ...skill, weight } : skill));
  };

  const removeSkill = (skillKey: string) => {
    setSelectedSkills(current => current.filter(skill => skill.key !== skillKey));
  };

  const resetForm = () => {
    setSelectedCriteriaId(null);
    setTitle("");
    setDescription("");
    setSelectedSkills([]);
    setResults([]);
    setError("");
  };

  const saveCriteria = async () => {
    if (!title.trim()) {
      setError("Ajoutez un titre pour vos critères.");
      return;
    }

    if (selectedSkills.length === 0) {
      setError("Ajoutez au moins une compétence.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        required_skills: selectedSkills.map(skill => ({ name: skill.name, weight: skill.weight })),
      };

      const response = selectedCriteriaId
        ? await criteriaApi.updateCriteria(selectedCriteriaId, payload)
        : await criteriaApi.createCriteria(payload);

      setSelectedCriteriaId(response.data.id);
      await refetchCriteria();
    } catch (err) {
      setError("Impossible d'enregistrer ces critères.");
    } finally {
      setSaving(false);
    }
  };

  const launchMatching = async (criteriaId?: number) => {
    const activeCriteriaId = criteriaId ?? selectedCriteriaId;
    if (!activeCriteriaId) {
      setError("Enregistrez d'abord une matrice de critères.");
      return;
    }

    setRunningMatching(true);
    setError("");
    try {
      const response = await matchingApi.runCriteriaMatching(activeCriteriaId);
      setResults(response.data);
      await refetchCriteria();
    } catch (err) {
      setError("Le matching n'a pas pu être lancé.");
    } finally {
      setRunningMatching(false);
    }
  };

  const loadCriteria = async (criteria: Criteria) => {
    setLoadingCriteria(true);
    setError("");
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

      const ranking = await matchingApi.getCriteriaMatchingResults(detail.id);
      setResults(ranking.data);
    } catch (err) {
      setError("Impossible de charger ces critères.");
    } finally {
      setLoadingCriteria(false);
    }
  };

  const deleteCriteria = async (criteriaId: number) => {
    if (!confirm("Supprimer cet ensemble de critères ?")) {
      return;
    }

    try {
      await criteriaApi.deleteCriteria(criteriaId);
      if (selectedCriteriaId === criteriaId) {
        resetForm();
      }
      await refetchCriteria();
    } catch (err) {
      setError("Impossible de supprimer ces critères.");
    }
  };

  const sortedResults = [...results].sort((left, right) => right.score - left.score);

  return (
    <Layout>
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 px-6 py-8 text-white shadow-2xl md:px-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.35),_transparent_34%),radial-gradient(circle_at_bottom_left,_rgba(16,185,129,0.24),_transparent_30%)]" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-100">
                <Sparkles className="h-3.5 w-3.5" />
                Étape 7 · Moteur de matching personnalisable
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">Construisez vos critères, puis lancez le ranking instantané.</h1>
                <p className="mt-3 max-w-2xl text-sm text-slate-200 md:text-base">
                  Sélectionnez des compétences depuis le dictionnaire, attribuez des poids, visualisez la répartition en temps réel et comparez les candidats selon un score cosinus pondéré.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[38rem] lg:grid-cols-2 xl:grid-cols-4">
              <Stat label="Critères" value={criteriaList?.length ?? 0} />
              <Stat label="Compétences" value={selectedSkills.length} />
              <Stat label="Poids total" value={`${totalWeight}%`} />
              <Stat label="Résultats" value={sortedResults.length} />
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Matrice de critères</h2>
                <p className="text-sm text-slate-500">Recherche, ajout, poids et édition des compétences du recruteur.</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsExpanded(value => !value)}
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
                      onChange={event => setTitle(event.target.value)}
                      placeholder="Ex: Data Engineer / France"
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-sky-400 focus:bg-white focus:ring-4 focus:ring-sky-100"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Description</label>
                    <input
                      value={description}
                      onChange={event => setDescription(event.target.value)}
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
                      onChange={event => setSkillQuery(event.target.value)}
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
                            <div className="text-xs text-slate-500">Poids: {skill.weight}%</div>
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
                            onChange={event => updateSkillWeight(skill.key, Number(event.target.value))}
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
                    {saving ? "Enregistrement..." : selectedCriteriaId ? "Mettre à jour les critères" : "Créer les critères"}
                  </button>
                  <button
                    type="button"
                    onClick={() => launchMatching()}
                    disabled={runningMatching || !selectedCriteriaId}
                    className="inline-flex items-center gap-2 rounded-2xl bg-sky-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Play className="h-4 w-4" />
                    {runningMatching ? "Matching en cours..." : "Lancer le matching"}
                  </button>
                </div>
              </div>
            )}
          </section>

          <section className="space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Répartition des poids</h2>
                <p className="text-sm text-slate-500">Camembert en temps réel sur les compétences sélectionnées.</p>
              </div>
              <div className="rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-600">Total: {totalWeight}%</div>
            </div>

            <div className="h-80 rounded-3xl border border-slate-200 bg-slate-50 p-4">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={110} paddingAngle={3}>
                      {pieData.map((entry, index) => (
                        <Cell key={entry.name} fill={palette[index % palette.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-slate-500">Ajoutez des compétences pour voir la distribution.</div>
              )}
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-400">Critères enregistrés</h3>
              <div className="space-y-3">
                {(criteriaList || []).length === 0 && !criteriaLoading && (
                  <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">Aucun ensemble de critères enregistré.</div>
                )}
                {criteriaLoading && <div className="rounded-2xl border border-slate-200 px-4 py-6 text-sm text-slate-500">Chargement des critères...</div>}
                {(criteriaList || []).map(criteria => (
                  <button
                    key={criteria.id}
                    type="button"
                    onClick={() => loadCriteria(criteria)}
                    className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                      selectedCriteriaId === criteria.id
                        ? "border-sky-300 bg-sky-50 shadow-sm"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{criteria.title}</div>
                        <div className="mt-1 text-xs text-slate-500">{criteria.required_skills.length} compétences</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={event => {
                            event.stopPropagation();
                            void launchMatching(criteria.id);
                          }}
                          className="rounded-xl bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
                        >
                          Matcher
                        </button>
                        <button
                          type="button"
                          onClick={event => {
                            event.stopPropagation();
                            void deleteCriteria(criteria.id);
                          }}
                          className="rounded-xl border border-slate-200 p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    {criteria.description && <div className="mt-2 text-sm text-slate-500">{criteria.description}</div>}
                  </button>
                ))}
              </div>
            </div>
          </section>
        </div>

        <section className="space-y-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">Classement des candidats</h2>
              <p className="text-sm text-slate-500">Résultats triés par score décroissant, avec détail des compétences couvertes.</p>
            </div>
            <button
              type="button"
              onClick={() => selectedCriteriaId && launchMatching(selectedCriteriaId)}
              disabled={!selectedCriteriaId || runningMatching}
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <BarChart3 className="h-4 w-4" />
              Rafraîchir le classement
            </button>
          </div>

          {loadingCriteria ? (
            <div className="rounded-2xl border border-slate-200 px-4 py-10 text-center text-sm text-slate-500">Chargement en cours...</div>
          ) : sortedResults.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500">
              Créez une matrice puis lancez le matching pour afficher le classement.
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {sortedResults.map((result, index) => (
                <article key={result.match_result_id || `${result.candidate_id}-${index}`} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-2xl bg-white px-3 py-2 text-sm font-bold text-slate-500">#{index + 1}</div>
                        <div>
                          <h3 className="text-lg font-semibold text-slate-900">{result.candidate_name}</h3>
                          <p className="text-sm text-slate-500">{result.candidate_email}</p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                        {result.matched_skills.slice(0, 4).map(skill => (
                          <span key={skill} className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">{skill}</span>
                        ))}
                        {result.missing_skills.slice(0, 2).map(skill => (
                          <span key={skill} className="rounded-full bg-amber-100 px-3 py-1 text-amber-800">Manque: {skill}</span>
                        ))}
                      </div>

                      <p className="text-sm leading-relaxed text-slate-600">{result.summary}</p>
                    </div>

                    <div className="flex flex-col items-center gap-3 rounded-2xl bg-white p-3 shadow-sm">
                      <ScoreGauge score={result.score} size="lg" />
                      <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Score cosinus</div>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2">
                    {result.skill_breakdown.map(item => (
                      <div key={item.skill} className="flex items-center justify-between gap-3 rounded-2xl bg-white px-3 py-2 text-sm">
                        <span className="font-medium text-slate-700">{item.skill}</span>
                        <span className={item.present ? "font-semibold text-emerald-700" : "font-semibold text-slate-400"}>
                          {item.present ? `${item.weight}%` : "0%"}
                        </span>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
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
