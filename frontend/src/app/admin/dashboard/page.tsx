"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Users, FileText, GitCompareArrows, MessageSquare, Wrench, TrendingUp,
  ShieldCheck, Activity, SlidersVertical,
} from "lucide-react";
import Layout from "@/components/Layout";
import AdminGuard from "@/components/AdminGuard";
import { adminApi, type GlobalStats } from "@/services/admin";
import { getErrorMessage } from "@/utils/errorHandler";

const roleLabels: Record<string, string> = {
  admin: "Administrateurs",
  recruiter: "Recruteurs",
  candidate: "Candidats",
};

function StatCard({ icon: Icon, label, value, accent }: {
  icon: React.ElementType; label: string; value: string | number; accent: string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent}`}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <p className="mt-3 text-3xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .getStats()
      .then((res) => setStats(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminGuard>
      <Layout>
        <div className="mb-8 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-100 text-rose-600">
            <ShieldCheck className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tableau de bord administrateur</h1>
            <p className="text-gray-600">Statistiques globales de la plateforme</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse rounded-xl bg-gray-100" />
            ))}
          </div>
        ) : stats ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard icon={Users} label="Utilisateurs" value={stats.total_users} accent="bg-indigo-100 text-indigo-600" />
              <StatCard icon={FileText} label="Candidats" value={stats.total_candidates} accent="bg-emerald-100 text-emerald-600" />
              <StatCard icon={GitCompareArrows} label="Offres / Critères" value={stats.total_jobs} accent="bg-blue-100 text-blue-600" />
              <StatCard icon={Activity} label="Résultats de matching" value={stats.total_match_results} accent="bg-amber-100 text-amber-600" />
              <StatCard icon={MessageSquare} label="Feedbacks recruteurs" value={stats.total_feedback} accent="bg-fuchsia-100 text-fuchsia-600" />
              <StatCard icon={Wrench} label="Compétences" value={stats.total_skills} accent="bg-cyan-100 text-cyan-600" />
              <StatCard
                icon={TrendingUp}
                label="Score moyen de matching"
                value={stats.average_match_score != null ? `${Math.round(stats.average_match_score * 100)}%` : "—"}
                accent="bg-rose-100 text-rose-600"
              />
              <StatCard icon={Users} label="Inscriptions (7 j)" value={stats.recent_signups} accent="bg-lime-100 text-lime-600" />
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              {/* Répartition par rôle */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold text-gray-900">Répartition par rôle</h2>
                <div className="space-y-3">
                  {Object.entries(stats.users_by_role).map(([role, count]) => {
                    const pct = stats.total_users ? Math.round((count / stats.total_users) * 100) : 0;
                    return (
                      <div key={role}>
                        <div className="mb-1 flex justify-between text-sm">
                          <span className="font-medium text-gray-700">{roleLabels[role] ?? role}</span>
                          <span className="text-gray-500">{count} ({pct}%)</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-gray-100">
                          <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Accès rapides */}
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="mb-4 text-lg font-semibold text-gray-900">Accès rapides</h2>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Link href="/admin/users" className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 hover:bg-gray-50">
                    <Users className="h-5 w-5 text-indigo-600" />
                    <span className="text-sm font-medium text-gray-800">Gérer les utilisateurs</span>
                  </Link>
                  <Link href="/admin/monitoring" className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 hover:bg-gray-50">
                    <Activity className="h-5 w-5 text-amber-600" />
                    <span className="text-sm font-medium text-gray-800">Logs & performances</span>
                  </Link>
                  <Link href="/admin/pipeline" className="flex items-center gap-3 rounded-lg border border-gray-200 p-4 hover:bg-gray-50">
                    <SlidersVertical className="h-5 w-5 text-rose-600" />
                    <span className="text-sm font-medium text-gray-800">Configurer le pipeline IA</span>
                  </Link>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </Layout>
    </AdminGuard>
  );
}
