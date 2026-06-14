'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Trash2, CheckCircle, XCircle, ShieldAlert } from 'lucide-react';
import Layout from '@/components/Layout';
import { adminApi, AdminJob, ModerationStatus } from '@/services/admin';
import { getErrorMessage } from '@/utils/errorHandler';

const STATUS_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Tous les statuts' },
  { value: 'pending', label: 'En attente' },
  { value: 'approved', label: 'Approuvées' },
  { value: 'rejected', label: 'Rejetées' },
];

const statusBadge: Record<ModerationStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

const statusLabel: Record<ModerationStatus, string> = {
  pending: 'En attente',
  approved: 'Approuvée',
  rejected: 'Rejetée',
};

export default function AdminJobsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('moderation_status') ?? '');
  const [page, setPage] = useState(0);
  const limit = 20;

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    adminApi
      .getJobs({ skip: page * limit, limit, moderation_status: statusFilter || undefined })
      .then((res) => {
        setJobs(res.data.items);
        setTotal(res.data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, statusFilter]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    if (!token || role !== 'admin') {
      router.push('/auth/login');
      return;
    }
    load();
  }, [router, load]);

  const handleModerate = async (job: AdminJob, newStatus: ModerationStatus) => {
    try {
      await adminApi.moderateJob(job.id, newStatus);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async (job: AdminJob) => {
    if (!confirm(`Supprimer l'offre "${job.title}" ?`)) return;
    try {
      await adminApi.deleteJob(job.id);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <ShieldAlert className="h-6 w-6 text-red-600" />
          <h1 className="text-2xl font-bold text-gray-900">Modération des offres</h1>
          <span className="ml-auto text-sm text-gray-500">{total} offre(s)</span>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-5">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        {/* Table */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Titre</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Recruteur</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Statut</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Créée le</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">Chargement...</td>
                </tr>
              )}
              {!loading && jobs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">Aucune offre trouvée.</td>
                </tr>
              )}
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{job.title}</td>
                  <td className="px-4 py-3 text-gray-600">{job.recruiter_email ?? `#${job.recruiter_id}`}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadge[job.moderation_status as ModerationStatus]}`}>
                      {statusLabel[job.moderation_status as ModerationStatus]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(job.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {job.moderation_status !== 'approved' && (
                        <button
                          onClick={() => handleModerate(job, 'approved')}
                          title="Approuver"
                          className="p-1.5 rounded-lg text-gray-400 hover:bg-green-50 hover:text-green-600 transition-colors"
                        >
                          <CheckCircle className="h-4 w-4" />
                        </button>
                      )}
                      {job.moderation_status !== 'rejected' && (
                        <button
                          onClick={() => handleModerate(job, 'rejected')}
                          title="Rejeter"
                          className="p-1.5 rounded-lg text-gray-400 hover:bg-yellow-50 hover:text-yellow-600 transition-colors"
                        >
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(job)}
                        title="Supprimer"
                        className="p-1.5 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Précédent
            </button>
            <span>Page {page + 1} / {totalPages}</span>
            <button
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-gray-200 px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Suivant
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
}
