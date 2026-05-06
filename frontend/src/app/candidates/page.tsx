'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import Layout from '@/components/Layout';
import { candidatesApi, Candidate, filterDisplayableCandidates } from '@/services/candidates';
import { favoritesApi } from '@/services/favorites';
import { getErrorMessage } from '@/utils/errorHandler';
import { SkeletonList } from '@/components/SkeletonLoader';
import { Search, Upload, Trash2, Heart, Mail, ExternalLink, Code2, X, Users } from 'lucide-react';

export default function CandidatesListPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());

  const fetchData = async () => {
    setLoading(true);
    try {
      const [candRes, favRes] = await Promise.allSettled([
        candidatesApi.getCandidates(),
        favoritesApi.getFavorites(),
      ]);
      if (candRes.status === 'fulfilled') setCandidates(filterDisplayableCandidates(candRes.value.data));
      else setError(getErrorMessage(candRes.reason));
      if (favRes.status === 'fulfilled') {
        setFavoriteIds(new Set(favRes.value.data.map((f) => f.candidate_id)));
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return candidates;
    const q = search.toLowerCase();
    return candidates.filter(
      (c) =>
        c.full_name?.toLowerCase().includes(q) ||
        c.email?.toLowerCase().includes(q) ||
        c.extracted_job_titles?.toLowerCase().includes(q)
    );
  }, [candidates, search]);

  const handleDelete = async (id: number) => {
    if (!confirm('Supprimer ce candidat ?')) return;
    try {
      await candidatesApi.deleteCandidate(id);
      setCandidates((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      alert(getErrorMessage(err));
    }
  };

  const toggleFavorite = async (id: number) => {
    try {
      if (favoriteIds.has(id)) {
        await favoritesApi.removeFavorite(id);
        setFavoriteIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
      } else {
        await favoritesApi.addFavorite(id);
        setFavoriteIds((prev) => new Set(prev).add(id));
      }
    } catch (err) {
      console.error('Favorite error:', err);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Candidats</h1>
            <p className="text-sm text-gray-500 mt-1">
              {filtered.length} candidat{filtered.length !== 1 ? 's' : ''} trouvé{filtered.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Link
            href="/candidate/upload"
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            <Upload className="h-4 w-4" /> Uploader un CV
          </Link>
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-4 py-2.5 shadow-sm">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Rechercher par nom, email ou poste..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 text-sm outline-none bg-transparent"
          />
          {search && (
            <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <SkeletonList />
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">
              {search ? 'Aucun candidat ne correspond à votre recherche.' : 'Aucun candidat enregistré.'}
            </p>
            {!search && (
              <Link href="/candidate/upload" className="text-indigo-600 hover:underline text-sm mt-2 inline-block">
                Uploader un premier CV
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((c) => (
              <div
                key={c.id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/candidates/${c.id}`}
                      className="text-base font-semibold text-gray-900 hover:text-indigo-600 transition-colors"
                    >
                      {c.full_name}
                    </Link>
                    <div className="flex flex-wrap items-center gap-3 mt-1.5 text-sm text-gray-500">
                      {c.email && (
                        <span className="flex items-center gap-1">
                          <Mail className="h-3.5 w-3.5" />{c.email}
                        </span>
                      )}
                      {c.linkedin_url && (
                        <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-blue-600">
                          <ExternalLink className="h-3.5 w-3.5" />LinkedIn
                        </a>
                      )}
                      {c.github_url && (
                        <a href={c.github_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 hover:text-gray-800">
                          <Code2 className="h-3.5 w-3.5" />GitHub
                        </a>
                      )}
                    </div>
                    {c.phone && <p className="text-xs text-gray-400 mt-1">{c.phone}</p>}
                    {c.is_fully_extracted && (
                      <span className="inline-block mt-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                        Profil extrait
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                    <button
                      onClick={() => toggleFavorite(c.id)}
                      className="p-1.5 rounded-full hover:bg-red-50 transition-colors"
                      title={favoriteIds.has(c.id) ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                    >
                      <Heart
                        className={`h-5 w-5 ${
                          favoriteIds.has(c.id) ? 'fill-red-500 text-red-500' : 'text-gray-300 hover:text-red-400'
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="p-1.5 rounded-full text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
