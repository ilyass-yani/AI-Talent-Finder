'use client';

import Layout from '@/components/Layout';
import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { favoritesApi } from '@/services/favorites';
import { candidatesApi, Candidate, filterDisplayableCandidates } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';

type CandidateDebugRecord = {
  id: number;
  full_name: string;
  email: string;
  raw_text?: string | null;
  extraction_quality_score?: number | null;
};

export default function RecruiterShortlist() {
  const [shortlist, setShortlist] = useState<Array<{ favorite_id: number; candidate: Candidate }>>([]);
  const [showingFallbackCandidates, setShowingFallbackCandidates] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState<number | null>(null);

  // Dev debug state: fetch raw /api/candidates response to inspect visibility issues
  const [debugOpen, setDebugOpen] = useState(false);
  const [debugData, setDebugData] = useState<CandidateDebugRecord[] | null>(null);
  const [debugLoading, setDebugLoading] = useState(false);
  const [debugError, setDebugError] = useState<string | null>(null);

  const fetchDebugCandidates = async () => {
    setDebugLoading(true);
    setDebugError(null);
    try {
      const resp = await candidatesApi.getCandidates();
      setDebugData(resp.data);
    } catch (err) {
      setDebugError(getErrorMessage(err));
      setDebugData(null);
    } finally {
      setDebugLoading(false);
    }
  };

  const formatPercent = (value?: number | null) => {
    const numericValue = Number(value ?? 0);
    return numericValue <= 1 ? Math.round(numericValue * 100) : Math.round(numericValue);
  };

  const parseJsonList = (value?: string | null): string[] => {
    if (!value) {
      return [];
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [];
    } catch {
      return [];
    }
  };

  const fetchFavorites = async () => {
    setLoading(true);
    setError('');
    setShowingFallbackCandidates(false);
    try {
      const response = await favoritesApi.getFavorites(0, 100);

      const itemsWithCandidates: Array<{ favorite_id: number; candidate: Candidate }> = [];
      for (const fav of response.data) {
        try {
          const candResponse = await candidatesApi.getCandidate(fav.candidate_id);
          itemsWithCandidates.push({
            favorite_id: fav.id,
            candidate: candResponse.data,
          });
        } catch (err) {
          console.error(`Erreur lors du chargement du candidat ${fav.candidate_id}:`, err);
        }
      }

      const visibleFavorites = itemsWithCandidates.filter((item) => filterDisplayableCandidates([item.candidate]).length > 0);

      if (visibleFavorites.length > 0) {
        setShortlist(visibleFavorites);
      } else {
        const candidatesResponse = await candidatesApi.getCandidates(0, 100);
        const visibleCandidates = filterDisplayableCandidates(candidatesResponse.data);
        setShortlist(visibleCandidates.map((candidate) => ({ favorite_id: 0, candidate })));
        setShowingFallbackCandidates(true);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchFavorites();
  }, []);

  const handleRemove = async (favoriteId: number, candidateId: number) => {
    setRemoving(favoriteId);
    try {
      await favoritesApi.removeFavorite(candidateId);
      setShortlist((current) => current.filter((item) => item.favorite_id !== favoriteId));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRemoving(null);
    }
  };

  const exportCSV = () => {
    if (shortlist.length === 0) {
      alert('Aucun candidat à exporter');
      return;
    }

    const csv = [
      ['Nom', 'Email', 'Téléphone', 'Titre du Poste', 'Compagnies', 'Score Extraction'],
      ...shortlist.map((item) => [
        item.candidate.full_name,
        item.candidate.email,
        item.candidate.phone || '',
        parseJsonList(item.candidate.extracted_job_titles).join('; '),
        parseJsonList(item.candidate.extracted_companies).join('; '),
        Math.round((item.candidate.extraction_quality_score || 0) * 100) + '%',
      ]),
    ];

    const csvContent = csv.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `shortlist-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-l-4 border-purple-500">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Tes Candidats en Shortlist 📋</h2>
          <p className="text-gray-600 text-lg">
            {loading
              ? '⏳ Chargement...'
              : showingFallbackCandidates
                ? `Aucun favori trouvé. Affichage de ${shortlist.length} candidats disponibles.`
                : `Total: ${shortlist.length} candidats sélectionnés`}
          </p>
          {/* Dev-only debug: show raw /api/candidates response to help troubleshooting */}
          {process.env.NODE_ENV !== 'production' && (
            <div className="mt-4 p-3 border rounded bg-gray-50">
              <button
                onClick={async () => {
                  const next = !debugOpen;
                  setDebugOpen(next);
                  if (next) await fetchDebugCandidates();
                }}
                className="px-3 py-1 bg-indigo-600 text-white rounded mr-3 text-sm"
              >
                {debugOpen ? 'Masquer debug API' : 'Afficher debug API /api/candidates'}
              </button>
              {debugOpen && (
                <div className="mt-3">
                  {debugLoading && <div className="text-sm text-gray-500">Chargement des candidats...</div>}
                  {debugError && <div className="text-sm text-red-600">Erreur: {debugError}</div>}
                  {debugData && (
                    <pre className="max-h-64 overflow-auto text-xs bg-white p-2 border rounded mt-2">{JSON.stringify(debugData, null, 2)}</pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
            className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-800 rounded-lg"
          >
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-5xl mb-4 animate-bounce">⏳</div>
            <p className="text-gray-600 text-lg font-medium">Chargement de vos favoris...</p>
          </div>
        ) : shortlist.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-6xl mb-4">📭</div>
            <p className="text-gray-600 text-lg font-medium">Aucun candidat en shortlist</p>
            <p className="text-gray-500 mt-2 mb-6">
              Visitez le{' '}
              <Link href="/recruiter/dashboard" className="text-purple-600 hover:text-purple-700 font-semibold underline">
                dashboard
              </Link>{' '}
              pour ajouter des candidats
            </p>
            <Link
              href="/recruiter/dashboard"
              className="inline-block px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-700 hover:to-purple-800 transition-all font-semibold"
            >
              Aller au Dashboard
            </Link>
          </div>
        ) : (
          <div>
            <div className="space-y-4 mb-8" role="list" aria-label="Liste de candidats en shortlist">
              {shortlist.map((item, idx) => (
                <div
                  key={item.favorite_id}
                  className="p-6 border border-gray-200 rounded-xl hover:shadow-lg hover:border-purple-300 transition-all duration-300 bg-white"
                  role="listitem"
                  aria-label={`${item.candidate.full_name}, ${item.candidate.email}, score: ${formatPercent(item.candidate.extraction_quality_score)}%`}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <Link href={`/candidates/${item.candidate.id}`}>
                    <div className="flex justify-between items-start cursor-pointer group">
                      <div className="flex-1">
                        <h4 className="font-bold text-gray-900 group-hover:text-purple-600 text-lg transition-colors">
                          {item.candidate.full_name}
                        </h4>
                        <p className="text-gray-600 text-sm">{item.candidate.email}</p>
                        {item.candidate.phone && <p className="text-sm text-gray-500 mt-1">📱 {item.candidate.phone}</p>}
                        {item.candidate.extracted_job_titles && parseJsonList(item.candidate.extracted_job_titles).length > 0 && (
                          <div className="text-sm text-gray-700 mt-3 flex flex-wrap gap-2">
                            <strong className="block w-full">💼 Derniers titres:</strong>
                            {parseJsonList(item.candidate.extracted_job_titles).slice(0, 3).map((title, i) => (
                              <span key={i} className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-xs font-medium">
                                {title}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="text-right ml-6 flex-shrink-0">
                        {item.candidate.extraction_quality_score && (
                          <>
                                        <div className="text-3xl font-bold text-green-600">
                                          {formatPercent(item.candidate.extraction_quality_score)}%
                            </div>
                            <p className="text-xs text-gray-600">Extraction Quality</p>
                          </>
                        )}
                      </div>
                    </div>
                  </Link>
                  {item.favorite_id > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
                      <button
                        onClick={() => void handleRemove(item.favorite_id, item.candidate.id)}
                        disabled={removing === item.favorite_id}
                        aria-label={`Retirer ${item.candidate.full_name} de la shortlist`}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
                      >
                        {removing === item.favorite_id ? '⏳ Suppression...' : '✕ Retirer de la shortlist'}
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {shortlist.length > 0 && (
              <div className="bg-white rounded-xl shadow-md p-6 border-t-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg">Exporter les candidats</h3>
                    <p className="text-gray-600 text-sm">Télécharge la shortlist en format CSV pour traitement ultérieur</p>
                  </div>
                  <button
                    onClick={exportCSV}
                    aria-label={`Exporter les ${shortlist.length} candidats en format CSV`}
                    className="px-8 py-3 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg hover:from-green-700 hover:to-green-800 transition-all font-semibold transform hover:scale-105 active:scale-95"
                  >
                    📊 Exporter CSV
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
