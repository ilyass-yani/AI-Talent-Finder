"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw, CheckCircle2, XCircle, AlertTriangle, Info, Database } from "lucide-react";
import Layout from "@/components/Layout";
import AdminGuard from "@/components/AdminGuard";
import { adminApi, type ActivityLog, type SystemHealth } from "@/services/admin";
import { getErrorMessage } from "@/utils/errorHandler";

const levelStyle: Record<string, { badge: string; icon: React.ElementType }> = {
  INFO: { badge: "bg-blue-100 text-blue-700", icon: Info },
  WARNING: { badge: "bg-amber-100 text-amber-700", icon: AlertTriangle },
  ERROR: { badge: "bg-red-100 text-red-700", icon: XCircle },
};

function capabilityStatus(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && "status" in (value as Record<string, unknown>)) {
    return String((value as Record<string, unknown>).status);
  }
  return JSON.stringify(value);
}

export default function AdminMonitoringPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [levelFilter, setLevelFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      adminApi.getHealth(),
      adminApi.getLogs({ level: levelFilter || undefined, limit: 100 }),
    ])
      .then(([h, l]) => {
        setHealth(h.data);
        setLogs(l.data);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [levelFilter]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AdminGuard>
      <Layout>
        <div className="mb-6 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 text-white shadow-lg"><Database className="h-5 w-5" /></span>
            <div>
              <h1 className="font-display text-2xl font-extrabold text-gray-900 sm:text-3xl">Logs &amp; performances</h1>
              <p className="text-sm text-gray-500">Supervision du système et journal d&apos;activité</p>
            </div>
          </div>
          <button onClick={load} className="btn-ghost !py-2 text-sm">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Actualiser
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        {/* Santé système */}
        {health && (
          <div className="mb-8 grid gap-6 lg:grid-cols-3">
            <div className="card-premium p-6">
              <h2 className="font-display mb-4 text-lg font-bold text-gray-900">État du système</h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Statut global</span>
                  <span className={`inline-flex items-center gap-1.5 font-medium ${health.status === "ok" ? "text-emerald-600" : "text-amber-600"}`}>
                    {health.status === "ok" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                    {health.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Base de données</span>
                  <span className={`inline-flex items-center gap-1.5 font-medium ${health.database_connected ? "text-emerald-600" : "text-red-600"}`}>
                    <Database className="h-4 w-4" />
                    {health.database_connected ? "Connectée" : "Indisponible"}
                  </span>
                </div>
              </div>
            </div>

            <div className="card-premium p-6">
              <h2 className="font-display mb-4 text-lg font-bold text-gray-900">Capacités IA</h2>
              <div className="space-y-2 text-sm">
                {Object.entries(health.capabilities).length === 0 && (
                  <p className="text-gray-400">Aucune information</p>
                )}
                {Object.entries(health.capabilities).map(([name, value]) => {
                  const status = capabilityStatus(value);
                  const ok = /ok|available|true|ready/i.test(status);
                  const degraded = /degraded|partial/i.test(status);
                  return (
                    <div key={name} className="flex items-center justify-between">
                      <span className="text-gray-600">{name}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ok ? "bg-emerald-100 text-emerald-700" : degraded ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"}`}>
                        {status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card-premium p-6">
              <h2 className="font-display mb-4 text-lg font-bold text-gray-900">Volumétrie</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {Object.entries(health.counts).map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-gray-50 px-3 py-2">
                    <p className="text-xs uppercase tracking-wide text-gray-400">{k}</p>
                    <p className="text-xl font-bold text-gray-900">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Journal d'activité */}
        <div className="card-premium overflow-hidden p-0">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
            <h2 className="font-display text-lg font-bold text-gray-900">Journal d&apos;activité</h2>
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
            >
              <option value="">Tous les niveaux</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
          <div className="max-h-[28rem] overflow-y-auto">
            <table className="min-w-full divide-y divide-gray-100 text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th className="px-5 py-2.5">Horodatage</th>
                  <th className="px-5 py-2.5">Niveau</th>
                  <th className="px-5 py-2.5">Action</th>
                  <th className="px-5 py-2.5">Détail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {logs.length === 0 ? (
                  <tr><td colSpan={4} className="px-5 py-8 text-center text-gray-400">Aucune entrée</td></tr>
                ) : (
                  logs.map((log) => {
                    const style = levelStyle[log.level] ?? levelStyle.INFO;
                    const Icon = style.icon;
                    return (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="whitespace-nowrap px-5 py-2.5 text-gray-500">{new Date(log.timestamp).toLocaleString("fr-FR")}</td>
                        <td className="px-5 py-2.5">
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
                            <Icon className="h-3 w-3" /> {log.level}
                          </span>
                        </td>
                        <td className="px-5 py-2.5 font-medium text-gray-800">{log.action}</td>
                        <td className="px-5 py-2.5 text-gray-600">{log.detail ?? "—"}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Layout>
    </AdminGuard>
  );
}
