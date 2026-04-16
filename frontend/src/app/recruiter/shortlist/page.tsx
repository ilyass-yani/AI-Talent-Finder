'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { favoritesApi } from '@/services/favorites';
import { candidatesApi, Candidate } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';

interface ShortlistItem {
  favorite_id: number;
  candidate: Candidate;
}

export default function RecruiterShortlist() {
  const [shortlist, setShortlist] = useState<ShortlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState<number | null>(null);

  // Fetch favorites with candidate details
  const fetchFavorites = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await favoritesApi.getFavorites(0, 100);
      
      // Fetch candidate details for each favorite
      const itemsWithCandidates: ShortlistItem[] = [];
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
      setShortlist(itemsWithCandidates);
    } catch (error) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, []);

  const handleRemove = async (favoriteId: number, candidateId: number) => {
    setRemoving(favoriteId);
    try {
      await favoritesApi.removeFavorite(candidateId);
      setShortlist(shortlist.filter(item => item.favorite_id !== favoriteId));
    } catch (error) {
      setError(getErrorMessage(error));
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
      ...shortlist.map(item => [
        item.candidate.full_name,
        item.candidate.email,
        item.candidate.phone || '',
        item.candidate.extracted_job_titles ? JSON.parse(item.candidate.extracted_job_titles).join('; ') : '',
        item.candidate.extracted_companies ? JSON.parse(item.candidate.extracted_companies).join('; ') : '',
        Math.round((item.candidate.extraction_quality_score || 0) * 100) + '%',
      ]),
    ];

    const csvContent = csv.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `shortlist-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link 
            href="/recruiter/dashboard" 
            className="text-gray-600 hover:text-gray-900 font-medium flex items-center gap-2 hover:bg-gray-100 px-3 py-2 rounded-lg transition-all"
          >
            ← Retour
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-2xl">⭐</span>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-purple-700 bg-clip-text text-transparent">
              Shortlist
            </h1>
          </div>
          <div></div>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header Card */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-l-4 border-purple-500">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Tes Candidats en Shortlist 📋</h2>
          <p className="text-gray-600 text-lg">
            {loading ? '⏳ Chargement...' : `Total: ${shortlist.length} candidats sélectionnés`}
          </p>
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
            {/* Shortlist Items */}
            <div
              className="space-y-4 mb-8"
              role="list"
              aria-label="Liste de candidats en shortlist"
            >
              {shortlist.map((item, idx) => (
                <div
                  key={item.favorite_id}
                  className="p-6 border border-gray-200 rounded-xl hover:shadow-lg hover:border-purple-300 transition-all duration-300 bg-white"
                  role="listitem"
                  aria-label={`${item.candidate.full_name}, ${item.candidate.email}, score: ${Math.round((item.candidate.extraction_quality_score || 0) * 100)}%`}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <Link href={`/candidates/${item.candidate.id}`}>
                    <div className="flex justify-between items-start cursor-pointer group">
                      <div className="flex-1">
                        <h4 className="font-bold text-gray-900 group-hover:text-purple-600 text-lg transition-colors">
                          {item.candidate.full_name}
                        </h4>
                        <p className="text-gray-600 text-sm">{item.candidate.email}</p>
                        {item.candidate.phone && (
                          <p className="text-sm text-gray-500 mt-1">📱 {item.candidate.phone}</p>
                        )}
                        {item.candidate.extracted_job_titles && (
                          <div className="text-sm text-gray-700 mt-3 flex flex-wrap gap-2">
                            <strong className="block w-full">💼 Derniers titres:</strong>
                            {JSON.parse(item.candidate.extracted_job_titles).slice(0, 3).map((title: string, i: number) => (
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
                              {Math.round(item.candidate.extraction_quality_score * 100)}%
                            </div>
                            <p className="text-xs text-gray-600">Extraction Quality</p>
                          </>
                        )}
                      </div>
                    </div>
                  </Link>
                  <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
                    <button
                      onClick={() => handleRemove(item.favorite_id, item.candidate.id)}
                      disabled={removing === item.favorite_id}
                      aria-label={`Retirer ${item.candidate.full_name} de la shortlist`}
                      className="text-red-600 hover:text-red-700 hover:bg-red-50 text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
                    >
                      {removing === item.favorite_id ? '⏳ Suppression...' : '✕ Retirer de la shortlist'}
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Export Button */}
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
    </div>
  );
}
