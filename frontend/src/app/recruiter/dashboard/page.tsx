'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi } from '@/services/candidates';
import { favoritesApi } from '@/services/favorites';
import { criteriaApi } from '@/services/criteria';
import Layout from '@/components/Layout';
import { Upload, Users, GitCompareArrows, Star, Clock, ArrowRight } from 'lucide-react';

/*
 * C1 - Bloc "mode recherche" supprime du dashboard.
 *      La fonctionnalite SearchMode est disponible sur /matching (criteres & matching).
 * C2 - Bloc "generation de profil IA" supprime du dashboard.
 *      La fonctionnalite GenerateMode pourrait etre deplacee dans une page dediee
 *      /recruiter/ai-generate si besoin (composant GenerateMode existant dans git).
 * C3 - Remplacement par des widgets utiles (derniers candidats, stats, raccourcis).
 */

interface Candidate {
  id: number;
  full_name: string;
  email: string;
  created_at?: string;
}

interface DashboardStats {
  candidateCount: number;
  criteriaCount: number;
  favoritesCount: number;
  loading: boolean;
}

export default function RecruiterDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats>({
    candidateCount: 0,
    criteriaCount: 0,
    favoritesCount: 0,
    loading: true,
  });
  const [recentCandidates, setRecentCandidates] = useState<Candidate[]>([]);
  const [userName, setUserName] = useState('');

  useEffect(() => {
    setUserName(localStorage.getItem('user_name') || 'Recruteur');
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      const [candRes, critRes, favRes] = await Promise.allSettled([
        candidatesApi.getCandidates(0, 1000),
        criteriaApi.getCriteria(),
        favoritesApi.getFavorites(),
      ]);

      const candidates: Candidate[] =
        candRes.status === 'fulfilled' ? (candRes.value.data ?? []) : [];

      const sorted = [...candidates].sort((a, b) => {
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateB - dateA;
      });

      setRecentCandidates(sorted.slice(0, 5));
      setStats({
        candidateCount: candidates.length,
        criteriaCount:
          critRes.status === 'fulfilled' ? (critRes.value.data?.length ?? 0) : 0,
        favoritesCount:
          favRes.status === 'fulfilled' ? (favRes.value.data?.length ?? 0) : 0,
        loading: false,
      });
    };
    fetchData();
  }, []);

  const statCards = [
    {
      label: 'Candidats',
      value: stats.candidateCount,
      color: 'blue',
      href: '/candidates',
      emoji: '👥',
      sub: 'dans la base',
    },
    {
      label: 'Criteres de poste',
      value: stats.criteriaCount,
      color: 'purple',
      href: '/matching',
      emoji: '🎯',
      sub: 'crees',
    },
    {
      label: 'En shortlist',
      value: stats.favoritesCount,
      color: 'green',
      href: '/recruiter/shortlist',
      emoji: '⭐',
      sub: 'favoris',
    },
  ];

  const colorMap: Record<string, string> = {
    blue: 'border-blue-500 text-blue-600',
    purple: 'border-purple-500 text-purple-600',
    green: 'border-green-500 text-green-600',
  };

  const quickActions = [
    {
      label: 'Uploader un CV',
      href: '/candidate/upload',
      icon: Upload,
      color: 'bg-indigo-600 hover:bg-indigo-700',
    },
    {
      label: 'Voir tous les candidats',
      href: '/candidates',
      icon: Users,
      color: 'bg-blue-600 hover:bg-blue-700',
    },
    {
      label: 'Lancer un matching',
      href: '/matching',
      icon: GitCompareArrows,
      color: 'bg-purple-600 hover:bg-purple-700',
    },
  ];

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-md p-8 border-l-4 border-purple-500">
          <h2 className="text-3xl font-bold text-gray-900 mb-1">
            Bonjour{userName ? `, ${userName}` : ''} !
          </h2>
          <p className="text-gray-600 text-lg">
            Bienvenue sur votre tableau de bord recruteur.
          </p>
        </div>

        {/* Stats */}
        <div className="grid md:grid-cols-3 gap-4">
          {statCards.map(({ label, value, color, href, emoji, sub }) => (
            <Link
              key={href}
              href={href}
              className={`bg-white rounded-xl shadow-md p-6 border-l-4 ${colorMap[color].split(' ')[0]} hover:shadow-lg transition-shadow`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className={`text-3xl font-bold ${colorMap[color].split(' ')[1]}`}>
                    {stats.loading ? (
                      <span className="text-lg text-gray-400">...</span>
                    ) : (
                      value
                    )}
                  </div>
                  <div className="text-gray-600 font-medium">{label}</div>
                  <div className="text-xs text-gray-400 mt-1">{sub}</div>
                </div>
                <div className="text-3xl">{emoji}</div>
              </div>
            </Link>
          ))}
        </div>

        {/* Raccourcis rapides */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Raccourcis rapides</h3>
          <div className="flex flex-wrap gap-3">
            {quickActions.map(({ label, href, icon: Icon, color }) => (
              <Link
                key={href}
                href={href}
                className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors ${color}`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </div>
        </div>

        {/* Derniers candidats ajoutes */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Clock className="h-5 w-5 text-indigo-500" />
              Derniers candidats ajoutes
            </h3>
            <Link
              href="/candidates"
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
            >
              Voir tous <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {stats.loading ? (
            <div className="text-gray-400 text-sm py-4 text-center">Chargement...</div>
          ) : recentCandidates.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-4xl mb-2">📂</div>
              <p>Aucun candidat pour l&apos;instant. Commencez par uploader un CV.</p>
              <Link
                href="/candidate/upload"
                className="mt-3 inline-block text-indigo-600 hover:underline font-medium"
              >
                Uploader un CV
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {recentCandidates.map((c) => (
                <li key={c.id} className="py-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-sm flex-shrink-0">
                      {(c.full_name || 'C')[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{c.full_name}</p>
                      <p className="text-xs text-gray-500">{c.email}</p>
                    </div>
                  </div>
                  <Link
                    href={`/candidates/${c.id}`}
                    className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                  >
                    Voir <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Shortlist rapide */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Star className="h-5 w-5 text-yellow-500" />
              Ma shortlist
            </h3>
            <Link
              href="/recruiter/shortlist"
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
            >
              Voir la shortlist <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <p className="text-gray-600 text-sm">
            {stats.loading ? (
              '...'
            ) : stats.favoritesCount === 0 ? (
              'Aucun candidat en shortlist. Ajoutez vos favoris depuis la liste des candidats.'
            ) : (
              `Vous avez ${stats.favoritesCount} candidat${stats.favoritesCount > 1 ? 's' : ''} en shortlist.`
            )}
          </p>
        </div>
      </div>
    </Layout>
  );
}
