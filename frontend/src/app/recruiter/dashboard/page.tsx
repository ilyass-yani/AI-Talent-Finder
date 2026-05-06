'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { jobsApi } from '@/services/jobs';
import { matchingApi } from '@/services/matching';
import { filterDisplayableIdentities } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';
import Layout from '@/components/Layout';

export default function RecruiterDashboard() {
  const router = useRouter();
  const [selectedMode, setSelectedMode] = useState<'search' | 'generate' | null>(null);

  return (
    <Layout>
{/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-l-4 border-purple-500">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Trouvez les meilleurs candidats 🎯</h2>
          <p className="text-gray-600 text-lg">
            Utilisez le matching intelligent pour trouver vos futurs talents
          </p>
        </div>

        {/* Mode Selection */}
        <div className="grid md:grid-cols-2 gap-8 mb-12" role="group" aria-label="Sélectionner le mode de recherche">
          {/* Mode 1: Search */}
          <div 
            onClick={() => setSelectedMode(selectedMode === 'search' ? null : 'search')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSelectedMode(selectedMode === 'search' ? null : 'search');
              }
            }}
            aria-pressed={selectedMode === 'search'}
            aria-label="Mode Recherche: Rechercher dans la base de candidats existants"
            className={`relative p-8 rounded-xl border-2 transition-all duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 transform hover:scale-105 ${
              selectedMode === 'search'
                ? 'border-blue-500 bg-gradient-to-br from-blue-50 to-blue-100 shadow-lg'
                : 'border-gray-200 bg-white hover:border-blue-300 shadow-md hover:shadow-lg'
            }`}
          >
            <div className="absolute top-4 right-4 text-2xl" aria-hidden="true">
              {selectedMode === 'search' ? '✓' : ''}
            </div>
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform" aria-hidden="true">🔍</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">Mode Recherche</h3>
            <p className="text-gray-600 mb-6">
              Déposez vos critères et trouvez les candidats correspondants dans notre base
            </p>
            <div className="space-y-2 text-sm text-gray-700">
              <p className="flex items-center gap-2"><span className="text-blue-600 font-bold">✓</span> Décrire le poste et les compétences requises</p>
              <p className="flex items-center gap-2"><span className="text-blue-600 font-bold">✓</span> Matching automatique sur les candidats</p>
              <p className="flex items-center gap-2"><span className="text-blue-600 font-bold">✓</span> Résultats classés par score</p>
              <p className="flex items-center gap-2"><span className="text-blue-600 font-bold">✓</span> Idéal pour: Recherche traditionnelle rapide</p>
            </div>
          </div>

          {/* Mode 2: Generate */}
          <div 
            onClick={() => setSelectedMode(selectedMode === 'generate' ? null : 'generate')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSelectedMode(selectedMode === 'generate' ? null : 'generate');
              }
            }}
            aria-pressed={selectedMode === 'generate'}
            aria-label="Mode Génération: L'IA génère le profil idéal et trouve les candidats correspondants"
            className={`relative p-8 rounded-xl border-2 transition-all duration-300 cursor-pointer focus:outline-none focus:ring-2 focus:ring-purple-500 transform hover:scale-105 ${
              selectedMode === 'generate'
                ? 'border-purple-500 bg-gradient-to-br from-purple-50 to-purple-100 shadow-lg'
                : 'border-gray-200 bg-white hover:border-purple-300 shadow-md hover:shadow-lg'
            }`}
          >
            <div className="absolute top-4 right-4 text-2xl" aria-hidden="true">
              {selectedMode === 'generate' ? '✓' : ''}
            </div>
            <div className="text-5xl mb-4" aria-hidden="true">⚡</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-3">Mode Génération IA</h3>
            <p className="text-gray-600 mb-6">
              Décrivez votre besoin et notre IA génère le profil idéal
            </p>
            <div className="space-y-2 text-sm text-gray-700">
              <p className="flex items-center gap-2"><span className="text-purple-600 font-bold">✓</span> Description texte du besoin</p>
              <p className="flex items-center gap-2"><span className="text-purple-600 font-bold">✓</span> L'IA génère le profil idéal</p>
              <p className="flex items-center gap-2"><span className="text-purple-600 font-bold">✓</span> Matching sur le profil généré</p>
              <p className="flex items-center gap-2"><span className="text-purple-600 font-bold">✓</span> Idéal pour: Postes innovants/complexes</p>
            </div>
          </div>
        </div>

        {/* Mode Selected: Search */}
        {selectedMode === 'search' && (
          <SearchMode />
        )}

        {/* Mode Selected: Generate */}
        {selectedMode === 'generate' && (
          <GenerateMode />
        )}

        {/* Quick Stats */}
        {!selectedMode && (
          <div className="grid md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-blue-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-blue-600">0</div>
                  <div className="text-gray-600 font-medium">Recherches</div>
                </div>
                <div className="text-3xl">🔍</div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-purple-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-purple-600">0</div>
                  <div className="text-gray-600 font-medium">Candidats vus</div>
                </div>
                <div className="text-3xl">👥</div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-green-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-green-600">0</div>
                  <div className="text-gray-600 font-medium">En shortlist</div>
                </div>
                <div className="text-3xl">⭐</div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-orange-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-orange-600">0</div>
                  <div className="text-gray-600 font-medium">Exported</div>
                </div>
                <div className="text-3xl">📊</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

function SearchMode() {
  const [jobTitle, setJobTitle] = useState('');
  const [description, setDescription] = useState('');
  const [skills, setSkills] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!jobTitle || !description) {
      setError('Veuillez remplir tous les champs');
      return;
    }

    setLoading(true);
    setError('');
    try {
      // Step 1: Create job criteria
      const criteria = await jobsApi.createJob({
        title: jobTitle,
        description: description,
      });

      // Step 2: Search candidates
      const matchedCandidates = await matchingApi.searchCandidates(criteria.data.id);
      const visibleCandidates = filterDisplayableIdentities(matchedCandidates.data);
      setResults(visibleCandidates);

      if (visibleCandidates.length === 0) {
        setError('Aucun candidat trouvé correspondant à vos critères.');
      }
    } catch (error) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-t-4 border-blue-500">
      <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">🔍 Mode Recherche</h3>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div>
          <label htmlFor="search-job-title" className="block text-sm font-semibold text-gray-900 mb-2">
            Titre du Poste <span className="text-red-600">*</span>
          </label>
          <input
            id="search-job-title"
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="Ex: Senior Python Developer"
            aria-required="true"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
          />
        </div>
        <div>
          <label htmlFor="search-skills" className="block text-sm font-semibold text-gray-900 mb-2">
            Compétences Requises
          </label>
          <input
            id="search-skills"
            type="text"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Ex: Python, FastAPI, SQL"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
          />
        </div>
      </div>

      <div className="mb-6">
        <label htmlFor="search-description" className="block text-sm font-semibold text-gray-900 mb-2">
          Description du Poste <span className="text-red-600">*</span>
        </label>
        <textarea
          id="search-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Décrivez le rôle, les responsabilités et les qualités recherchées..."
          rows={5}
          aria-required="true"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all resize-none"
        />
      </div>

      <button
        onClick={handleSearch}
        disabled={loading}
        className={`px-8 py-3 rounded-lg font-semibold text-white transition-all transform disabled:opacity-50 disabled:cursor-not-allowed ${
          loading
            ? 'bg-blue-500'
            : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 active:scale-95'
        }`}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="inline-block animate-spin">⏳</span> Recherche...
          </span>
        ) : (
          '🔍 Lancer la Recherche'
        )}
      </button>

      {error && (
        <div
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
          className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-800 rounded-lg"
        >
          ⚠️ {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="mt-8 animate-fadeIn">
          <h4 className="text-xl font-bold text-gray-900 mb-4">
            🎯 Résultats ({results.length})
          </h4>
          <div className="space-y-3">
            {results.map((result, idx) => (
              <Link key={result.candidate_id} href={`/candidates/${result.candidate_id}`}>
                <div
                  className="p-5 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-all cursor-pointer transform hover:scale-102"
                  role="article"
                  aria-label={`Candidat: ${result.full_name}, score: ${Math.round(result.match_score * 100)}%`}
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h5 className="font-bold text-gray-900 hover:text-blue-600 text-lg">
                        {result.full_name}
                      </h5>
                      <p className="text-gray-600 text-sm">{result.email}</p>
                      {result.explanation && (
                        <p className="text-xs text-gray-500 mt-2 leading-relaxed">{result.explanation}</p>
                      )}
                    </div>
                    <div className="text-right ml-6 flex-shrink-0">
                      <div className={`text-3xl font-bold ${
                        result.match_score >= 0.7 ? 'text-green-600' :
                        result.match_score >= 0.5 ? 'text-yellow-600' :
                        'text-orange-600'
                      }`}>
                        {Math.round(result.match_score * 100)}%
                      </div>
                      <p className="text-xs text-gray-600">Match Score</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

function GenerateMode() {
  const [jobTitle, setJobTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [idealProfile, setIdealProfile] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!jobTitle || !description) {
      setError('Veuillez remplir tous les champs');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await matchingApi.generateAndMatch(jobTitle, description);
      setIdealProfile(response.data.ideal_profile);
      const visibleMatches = filterDisplayableIdentities(response.data.matches);
      setResults(visibleMatches);

      if (visibleMatches.length === 0) {
        setError('Aucun candidat ne correspond au profil généré.');
      }
    } catch (error) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-t-4 border-purple-500">
      <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">⚡ Mode Génération IA</h3>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div>
          <label htmlFor="generate-job-title" className="block text-sm font-semibold text-gray-900 mb-2">
            Titre du Poste <span className="text-red-600">*</span>
          </label>
          <input
            id="generate-job-title"
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="Ex: Startup CTO"
            aria-required="true"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all"
          />
        </div>
      </div>

      <div className="mb-6">
        <label htmlFor="generate-description" className="block text-sm font-semibold text-gray-900 mb-2">
          Décrivez vos besoins <span className="text-red-600">*</span>
        </label>
        <textarea
          id="generate-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Décrivez en détail le poste, la vision, les défis et l'impact souhaité..."
          rows={6}
          aria-required="true"
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all resize-none"
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        aria-label="Générer le profil idéal et trouver les candidats correspondants"
        className={`px-8 py-3 rounded-lg font-semibold text-white transition-all transform disabled:opacity-50 disabled:cursor-not-allowed ${
          loading
            ? 'bg-purple-500'
            : 'bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 active:scale-95'
        }`}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="inline-block animate-spin">⚙️</span> L'IA génère...
          </span>
        ) : (
          '✨ Générer le Profil Idéal'
        )}
      </button>

      {error && (
        <div
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
          className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-800 rounded-lg"
        >
          ⚠️ {error}
        </div>
      )}

      {idealProfile && (
        <div className="mt-8 animate-fadeIn">
          <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2" id="ideal-profile-section">
            💡 Profil Idéal Généré
          </h4>
          <div
            className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-xl mb-6 border-2 border-purple-200"
            role="region"
            aria-labelledby="ideal-profile-section"
          >
            <h5 className="font-bold text-gray-900 mb-4 text-lg">Compétences Idéales:</h5>
            <div className="space-y-3">
              {idealProfile.ideal_skills?.map((skill: { name: string; weight?: number; level?: string }, idx: number) => (
                <div key={skill.name} className="flex justify-between items-center p-3 bg-white rounded-lg hover:shadow-md transition-shadow">
                  <span className="text-gray-800 font-medium">{skill.name}</span>
                  <span className="text-sm text-purple-600 font-bold bg-purple-100 px-3 py-1 rounded-full">{skill.level}</span>
                </div>
              ))}
            </div>
          </div>

          <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2" id="matched-candidates-section">
            👥 Candidats Matchés ({results.length})
          </h4>
          {results.length > 0 ? (
            <div
              className="space-y-3"
              role="region"
              aria-labelledby="matched-candidates-section"
            >
              {results.map((result, idx) => (
                <Link key={result.candidate_id} href={`/candidates/${result.candidate_id}`}>
                  <div
                    className="p-5 border border-gray-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-all cursor-pointer transform hover:scale-102"
                    role="article"
                    aria-label={`Candidat: ${result.full_name}, score: ${Math.round(result.match_score * 100)}%`}
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h5 className="font-bold text-gray-900 hover:text-purple-600 text-lg">
                          {result.full_name}
                        </h5>
                        <p className="text-gray-600 text-sm">{result.email}</p>
                        {result.explanation && (
                          <p className="text-xs text-gray-500 mt-2 leading-relaxed">{result.explanation}</p>
                        )}
                      </div>
                      <div className="text-right ml-6 flex-shrink-0">
                        <div className={`text-3xl font-bold ${
                          result.match_score >= 0.7 ? 'text-green-600' :
                          result.match_score >= 0.5 ? 'text-yellow-600' :
                          'text-orange-600'
                        }`}>
                          {Math.round(result.match_score * 100)}%
                        </div>
                        <p className="text-xs text-gray-600">Match Score</p>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <div className="text-5xl mb-3">🔍</div>
              <p>Aucun candidat ne correspond à ce profil.</p>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
