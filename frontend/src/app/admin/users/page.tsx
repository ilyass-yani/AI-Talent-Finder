'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Trash2, ToggleLeft, ToggleRight, ShieldAlert } from 'lucide-react';
import Layout from '@/components/Layout';
import { adminApi, AdminUser } from '@/services/admin';
import { getErrorMessage } from '@/utils/errorHandler';

const ROLE_OPTIONS = ['', 'candidate', 'recruiter', 'admin'];

const roleBadge: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  recruiter: 'bg-indigo-100 text-indigo-700',
  candidate: 'bg-emerald-100 text-emerald-700',
};

export default function AdminUsersPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roleFilter, setRoleFilter] = useState(searchParams.get('role') ?? '');
  const [page, setPage] = useState(0);
  const limit = 20;

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    adminApi
      .getUsers({ skip: page * limit, limit, role: roleFilter || undefined })
      .then((res) => {
        setUsers(res.data.items);
        setTotal(res.data.total);
      })
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [page, roleFilter]);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const role = localStorage.getItem('user_role');
    if (!token || role !== 'admin') {
      router.push('/auth/login');
      return;
    }
    load();
  }, [router, load]);

  const handleToggleStatus = async (user: AdminUser) => {
    try {
      await adminApi.setUserStatus(user.id, !user.is_active);
      load();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDelete = async (user: AdminUser) => {
    if (!confirm(`Supprimer le compte de ${user.full_name} (${user.email}) ?`)) return;
    try {
      await adminApi.deleteUser(user.id);
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
          <h1 className="text-2xl font-bold text-gray-900">Gestion des utilisateurs</h1>
          <span className="ml-auto text-sm text-gray-500">{total} utilisateur(s)</span>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-5">
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(0); }}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">Tous les rôles</option>
            {ROLE_OPTIONS.filter(Boolean).map((r) => (
              <option key={r} value={r}>{r}</option>
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
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Nom</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Email</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Rôle</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Statut</th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600">Créé le</th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">Chargement...</td>
                </tr>
              )}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">Aucun utilisateur trouvé.</td>
                </tr>
              )}
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-900">{user.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${roleBadge[user.role] ?? 'bg-gray-100 text-gray-700'}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {user.is_active ? 'Actif' : 'Désactivé'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(user.created_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleToggleStatus(user)}
                        title={user.is_active ? 'Désactiver' : 'Activer'}
                        className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors"
                      >
                        {user.is_active
                          ? <ToggleRight className="h-4 w-4 text-green-600" />
                          : <ToggleLeft className="h-4 w-4 text-gray-400" />}
                      </button>
                      <button
                        onClick={() => handleDelete(user)}
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
