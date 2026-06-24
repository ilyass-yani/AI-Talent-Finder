"use client";

import { useEffect, useState } from "react";
import { Save, RotateCcw, SlidersVertical, AlertTriangle } from "lucide-react";
import Layout from "@/components/Layout";
import AdminGuard from "@/components/AdminGuard";
import { adminApi, type PipelineConfig } from "@/services/admin";
import { getErrorMessage } from "@/utils/errorHandler";

type EditableKey =
  | "skill_weight" | "semantic_weight" | "experience_weight"
  | "education_weight" | "perfect_match_bonus" | "accept_threshold" | "review_threshold";

const WEIGHT_FIELDS: { key: EditableKey; label: string; help: string }[] = [
  { key: "skill_weight", label: "Compétences", help: "Poids du recouvrement des compétences" },
  { key: "semantic_weight", label: "Similarité sémantique", help: "Poids du matching sémantique (embeddings)" },
  { key: "experience_weight", label: "Expérience", help: "Poids de l'adéquation d'expérience" },
  { key: "education_weight", label: "Formation", help: "Poids de l'adéquation de formation" },
  { key: "perfect_match_bonus", label: "Bonus match parfait", help: "Bonus appliqué pour un match parfait" },
];

const THRESHOLD_FIELDS: { key: EditableKey; label: string; help: string }[] = [
  { key: "accept_threshold", label: "Seuil d'acceptation", help: "Score ≥ ce seuil → Accepté" },
  { key: "review_threshold", label: "Seuil de revue", help: "Score ≥ ce seuil → À revoir, sinon Rejeté" },
];

export default function AdminPipelinePage() {
  const [config, setConfig] = useState<PipelineConfig | null>(null);
  const [values, setValues] = useState<Record<EditableKey, number>>({} as Record<EditableKey, number>);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const apply = (cfg: PipelineConfig) => {
    setConfig(cfg);
    setValues({
      skill_weight: cfg.skill_weight,
      semantic_weight: cfg.semantic_weight,
      experience_weight: cfg.experience_weight,
      education_weight: cfg.education_weight,
      perfect_match_bonus: cfg.perfect_match_bonus,
      accept_threshold: cfg.accept_threshold,
      review_threshold: cfg.review_threshold,
    });
  };

  useEffect(() => {
    adminApi.getPipelineConfig()
      .then((res) => apply(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const weightSum = WEIGHT_FIELDS.reduce((acc, f) => acc + (values[f.key] || 0), 0);
  const thresholdInvalid = (values.accept_threshold || 0) < (values.review_threshold || 0);

  const set = (key: EditableKey, raw: string) => {
    const v = Math.min(1, Math.max(0, parseFloat(raw) || 0));
    setValues((prev) => ({ ...prev, [key]: v }));
    setSuccess("");
  };

  const save = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const res = await adminApi.updatePipelineConfig(values);
      apply(res.data);
      setSuccess("Paramètres enregistrés. Ils s'appliquent aux prochains calculs de matching.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    if (!confirm("Réinitialiser tous les paramètres aux valeurs par défaut ?")) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const res = await adminApi.resetPipelineConfig();
      apply(res.data);
      setSuccess("Paramètres réinitialisés aux valeurs par défaut.");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ field }: { field: { key: EditableKey; label: string; help: string } }) => (
    <div className="rounded-lg border border-gray-200 p-4">
      <div className="mb-2 flex items-center justify-between">
        <label className="text-sm font-semibold text-gray-800">{field.label}</label>
        <span className="text-sm font-mono text-indigo-600">{(values[field.key] ?? 0).toFixed(2)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={values[field.key] ?? 0}
        onChange={(e) => set(field.key, e.target.value)}
        className="w-full accent-indigo-600"
      />
      <div className="mt-1 flex items-center justify-between">
        <p className="text-xs text-gray-500">{field.help}</p>
        {config && (
          <span className="text-xs text-gray-400">défaut: {config.defaults[field.key]?.toFixed(2)}</span>
        )}
      </div>
    </div>
  );

  return (
    <AdminGuard>
      <Layout>
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-red-600 text-white shadow-lg shadow-rose-200/50">
            <SlidersVertical className="h-6 w-6" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-extrabold text-gray-900 sm:text-3xl">Paramètres du pipeline IA</h1>
            <p className="text-sm text-gray-500">Poids du scoring et seuils de décision du matching</p>
          </div>
        </div>

        {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
        {success && <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>}

        {loading ? (
          <div className="h-64 animate-pulse rounded-xl bg-gray-100" />
        ) : (
          <div className="space-y-6">
            <section className="card-premium p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-display text-lg font-bold text-gray-900">Poids du scoring</h2>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${Math.abs(weightSum - 1) < 0.001 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                  Somme des poids : {weightSum.toFixed(2)}
                </span>
              </div>
              {Math.abs(weightSum - 1) >= 0.001 && (
                <p className="mb-4 flex items-center gap-2 text-xs text-amber-600">
                  <AlertTriangle className="h-4 w-4" />
                  La somme des poids (hors bonus) est idéalement proche de 1,00.
                </p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                {WEIGHT_FIELDS.map((f) => <Field key={f.key} field={f} />)}
              </div>
            </section>

            <section className="card-premium p-6">
              <h2 className="font-display mb-4 text-lg font-bold text-gray-900">Seuils de décision</h2>
              {thresholdInvalid && (
                <p className="mb-4 flex items-center gap-2 text-xs text-red-600">
                  <AlertTriangle className="h-4 w-4" />
                  Le seuil d&apos;acceptation doit être supérieur ou égal au seuil de revue.
                </p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                {THRESHOLD_FIELDS.map((f) => <Field key={f.key} field={f} />)}
              </div>
            </section>

            <div className="flex justify-end gap-3">
              <button onClick={reset} disabled={saving} className="btn-ghost !py-2 text-sm disabled:opacity-60">
                <RotateCcw className="h-4 w-4" /> Réinitialiser
              </button>
              <button onClick={save} disabled={saving || thresholdInvalid} className="btn-primary !py-2 text-sm disabled:opacity-60">
                <Save className="h-4 w-4" /> {saving ? "Enregistrement…" : "Enregistrer"}
              </button>
            </div>
          </div>
        )}
      </Layout>
    </AdminGuard>
  );
}
