'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Users, Briefcase, GitCompareArrows, UserCheck, ShieldAlert } from 'lucide-react';
import Layout from '@/components/Layout';
import { adminApi, AdminStats } from '@/services/admin';
import { getErrorMessage } from '@/utils/errorHandler';

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    if (!token || role !== 'admin') {
      router.push('/auth/login');
      return;
    }
    adminApi.getStats()
      .then((res) => setStats(res.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [router]);

  const cards = stats
    ? [
        {
          label: 'Candidats',
          value: stats.total_candidates,
          icon: Users,
          color: 'bg-emerald-50 text-emerald-700',
          border: 'border-l-4 border-emerald-500',
          href: '/admin/users?role=candidate',
        },
        {
          label: 'Recruteurs',
          value: stats.total_recruiters,
          icon: UserCheck,
          color: 'bg-indigo-50 text-indigo-700',
          border: 'border-l-4 border-indigo-500',
          href: '/admin/users?role=recruiter',
        },
        {
          label: 'Offres approuvées',
          value: stats.total_active_jobs,
          icon: Briefcase,
          color: 'bg-blue-50 text-blue-700',
          border: 'border-l-4 border-blue-500',
          href: '/admin/jobs?moderation_status=approved',
        },
        {
          label: 'Matchings effectués',
          value: stats.total_matchings,
          icon: GitCompareArrows,
          color: 'bg-purple-50 text-purple-700',
          border: 'border-l-4 border-purple-500',
          href: null,
        },
      ]
    : [];

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <ShieldAlert className="h-7 w-7 text-red-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tableau de bord Admin</h1>
            <p className="text-sm text-gray-500">Vue globale de la plateforme</p>
          </div>
        </div>

        {/* Quick nav */}
        <div className="flex gap-3 mb-8">
          <Link
            href="/admin/users"
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Gérer les utilisateurs
          </Link>
          <Link
            href="/admin/jobs"
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Modérer les offres
          </Link>
        </div>

        {/* Stats cards */}
        {loading && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-32 rounded-xl bg-gray-100 animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
            {cards.map(({ label, value, icon: Icon, color, border, href }) => {
              const card = (
                <div
                  className={`rounded-xl bg-white p-6 shadow-sm ${border} ${href ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}`}
                >
                  <div className={`inline-flex rounded-lg p-2 ${color} mb-3`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <p className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</p>
                  <p className="text-sm text-gray-500 mt-1">{label}</p>
                </div>
              );
              return href ? (
                <Link key={label} href={href}>
                  {card}
                </Link>
              ) : (
                <div key={label}>{card}</div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
