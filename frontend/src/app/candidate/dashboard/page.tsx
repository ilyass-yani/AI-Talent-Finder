'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/services/api';
import { candidatesApi, Candidate } from '@/services/candidates';
import { SkeletonProfile, SkeletonCard } from '@/components/SkeletonLoader';

export default function CandidateDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          router.push('/auth/login');
          return;
        }
        
        const userResponse = await apiClient.get('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(userResponse.data);

        try {
          const candidateResponse = await candidatesApi.getMyProfile();
          setCandidate(candidateResponse.data);
        } catch (err) {
          console.log('Candidate profile not found yet');
          setCandidate(null);
        }
      } catch (error) {
        router.push('/auth/login');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <div className="h-8 bg-gray-200 rounded w-40 animate-pulse"></div>
          </div>
        </nav>
        <div className="max-w-6xl mx-auto px-4 py-8">
          <SkeletonProfile />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <span className="text-3xl">👤</span>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-blue-700 bg-clip-text text-transparent">
              Candidat Dashboard
            </h1>
          </div>
          <button 
            onClick={() => {
              localStorage.removeItem('access_token');
              setTimeout(() => router.push('/'), 100);
            }}
            className="px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors font-medium"
          >
            Déconnexion
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Welcome Card */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-l-4 border-blue-500">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                Bienvenue, {user?.full_name}! 👋
              </h2>
              <p className="text-gray-600 text-lg">
                Mets en avant ton profil et tes compétences pour attirer les meilleurs recruteurs
              </p>
            </div>
            {candidate && candidate.extraction_quality_score && (
              <div className="text-right">
                <div className="text-3xl font-bold text-green-600">
                  {Math.round(candidate.extraction_quality_score * 100)}%
                </div>
                <div className="text-sm text-gray-600">Profil complet</div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions - Onboarding Steps */}
        <div className="mb-12">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Étapes de configuration</h3>
          <div className="grid md:grid-cols-3 gap-6">
            {/* Step 1: Upload CV */}
            <Link href="/candidate/upload">
              <div className="bg-white rounded-xl shadow-md p-6 hover:shadow-xl transition-all duration-300 cursor-pointer group h-full">
                <div className="flex items-start justify-between mb-4">
                  <div className="text-4xl group-hover:scale-110 transition-transform">📄</div>
                  <div className={`text-sm font-semibold px-3 py-1 rounded-full ${
                    candidate ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
                  }`}>
                    {candidate ? '✓ Fait' : 'Étape 1'}
                  </div>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Télécharger CV</h3>
                <p className="text-gray-600 mb-4">
                  Télécharge ou mets à jour ton CV. Notre IA extraira automatiquement tes données.
                </p>
                <div className="text-blue-600 font-semibold group-hover:translate-x-2 transition-transform">
                  Commencer →
                </div>
              </div>
            </Link>

            {/* Step 2: View Profile */}
            <Link href="/candidate/profile">
              <div className="bg-white rounded-xl shadow-md p-6 hover:shadow-xl transition-all duration-300 cursor-pointer group h-full">
                <div className="flex items-start justify-between mb-4">
                  <div className="text-4xl group-hover:scale-110 transition-transform">🧑</div>
                  <div className={`text-sm font-semibold px-3 py-1 rounded-full ${
                    candidate ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {candidate ? '✓ Visible' : 'Étape 2'}
                  </div>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Mon Profil</h3>
                <p className="text-gray-600 mb-4">
                  Vois comment les recruteurs te découvrent. Édite tes informations personnelles.
                </p>
                <div className="text-blue-600 font-semibold group-hover:translate-x-2 transition-transform">
                  Voir profil →
                </div>
              </div>
            </Link>

            {/* Step 3: Wait for Opportunities */}
            <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-md p-6 cursor-default h-full border-2 border-dashed border-purple-200">
              <div className="flex items-start justify-between mb-4">
                <div className="text-4xl opacity-60">💼</div>
                <div className="text-sm font-semibold px-3 py-1 rounded-full bg-purple-100 text-purple-700">
                  Bientôt
                </div>
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Opportunités</h3>
              <p className="text-gray-600 mb-4 opacity-75">
                Les recruteurs te découvriront basé sur tes compétences! Reste à l'affût.
              </p>
              <div className="text-purple-600 font-semibold opacity-75">
                En construction...
              </div>
            </div>
          </div>
        </div>

        {/* Profile Stats */}
        <div className="mb-12">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Ton Profil</h3>
          <div className="grid md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-blue-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-blue-600">
                    {candidate ? '✓' : '○'}
                  </div>
                  <div className="text-gray-600 font-medium">CV Uploadé</div>
                </div>
                <div className="text-3xl">📄</div>
              </div>
              {candidate && (
                <div className="text-xs text-gray-500 mt-3 pt-3 border-t">
                  Qualité: {Math.round(candidate.extraction_quality_score || 0)}%
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-green-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-green-600">
                    {(() => {
                      if (!candidate) return '0';
                      try {
                        const titles = JSON.parse(candidate.extracted_job_titles || '[]');
                        return titles.length || '0';
                      } catch {
                        return '0';
                      }
                    })()}
                  </div>
                  <div className="text-gray-600 font-medium">Titres Détectés</div>
                </div>
                <div className="text-3xl">💼</div>
              </div>
              {candidate && (
                <div className="text-xs text-gray-500 mt-3 pt-3 border-t">
                  {(() => {
                    try {
                      const companies = JSON.parse(candidate.extracted_companies || '[]');
                      return `${companies.length} entreprises`;
                    } catch {
                      return 'N/A';
                    }
                  })()}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-purple-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-purple-600">
                    {(() => {
                      if (!candidate) return '0';
                      try {
                        const emails = JSON.parse(candidate.extracted_emails || '[]');
                        return emails.length || '0';
                      } catch {
                        return '0';
                      }
                    })()}
                  </div>
                  <div className="text-gray-600 font-medium">Emails Trouvés</div>
                </div>
                <div className="text-3xl">📧</div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-orange-500 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-orange-600">0</div>
                  <div className="text-gray-600 font-medium">Propositions</div>
                </div>
                <div className="text-3xl">🎯</div>
              </div>
              <div className="text-xs text-gray-500 mt-3 pt-3 border-t">
                À venir bientôt
              </div>
            </div>
          </div>
        </div>

        {/* Tips Section */}
        {!candidate && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl border-2 border-blue-200 p-8">
            <div className="flex items-start gap-4">
              <div className="text-3xl">💡</div>
              <div>
                <h4 className="text-lg font-bold text-gray-900 mb-2">Débute maintenant</h4>
                <p className="text-gray-700 mb-4">
                  Upload ton CV pour que les recruteurs te découvrent! Notre IA extraira automatiquement tes compétences et expériences.
                </p>
                <Link
                  href="/candidate/upload"
                  className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
                >
                  Upload mon CV →
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
