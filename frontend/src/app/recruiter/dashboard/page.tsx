'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi } from '@/services/candidates';
import { favoritesApi } from '@/services/favorites';
import { criteriaApi } from '@/services/criteria';
import Layout from '@/components/Layout';
import { Upload, Users, GitCompareArrows, Star, Clock, ArrowRight, Target, Sparkles } from 'lucide-react';

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
      href: '/candidates',
      icon: Users,
      grad: 'from-blue-500 to-indigo-500',
      text: 'text-blue-600',
      sub: 'dans la base',
    },
    {
      label: 'Critères de poste',
      value: stats.criteriaCount,
      href: '/matching',
      icon: Target,
      grad: 'from-violet-500 to-fuchsia-500',
      text: 'text-violet-600',
      sub: 'créés',
    },
    {
      label: 'En shortlist',
      value: stats.favoritesCount,
      href: '/recruiter/shortlist',
      icon: Star,
      grad: 'from-emerald-500 to-teal-500',
      text: 'text-emerald-600',
      sub: 'favoris',
    },
  ];

  const quickActions = [
    { label: 'Uploader un CV', href: '/candidate/upload', icon: Upload },
    { label: 'Voir tous les candidats', href: '/candidates', icon: Users },
    { label: 'Lancer un matching', href: '/matching', icon: GitCompareArrows },
  ];

  return (
    <Layout>
      <div className="max-w-6xl mx-auto space-y-7">
        {/* Greeting header */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-violet-600 to-indigo-700 p-8 text-white shadow-xl shadow-indigo-300/30">
          <div className="absolute -right-8 -top-10 h-44 w-44 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute right-24 bottom-[-3rem] h-40 w-40 rounded-full bg-cyan-400/20 blur-2xl" />
          <div className="relative">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" /> Espace Recruteur
            </span>
            <h2 className="font-display mt-3 text-3xl font-extrabold sm:text-4xl">
              Bonjour{userName ? `, ${userName}` : ''} 👋
            </h2>
            <p className="mt-1 text-indigo-100">Bienvenue sur votre tableau de bord recruteur.</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          {statCards.map(({ label, value, href, icon: Icon, grad, text, sub }) => (
            <Link key={href} href={href} className="card-premium card-glow group p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className={`font-display text-4xl font-extrabold ${text}`}>
                    {stats.loading ? <span className="text-lg text-gray-400">...</span> : value}
                  </div>
                  <div className="mt-1 font-semibold text-gray-700">{label}</div>
                  <div className="mt-0.5 text-xs text-gray-400">{sub}</div>
                </div>
                <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${grad} text-white shadow-lg transition-transform group-hover:scale-110`}>
                  <Icon className="h-6 w-6" />
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Raccourcis rapides */}
        <div className="card-premium p-6">
          <h3 className="font-display mb-4 text-xl font-bold text-gray-900">Raccourcis rapides</h3>
          <div className="flex flex-wrap gap-3">
            {quickActions.map(({ label, href, icon: Icon }) => (
              <Link key={href} href={href} className="btn-ghost group">
                <Icon className="h-4 w-4 text-indigo-600" />
                {label}
                <ArrowRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-0.5 group-hover:text-indigo-600" />
              </Link>
            ))}
          </div>
        </div>

        {/* Derniers candidats ajoutes */}
        <div className="card-premium p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display flex items-center gap-2 text-xl font-bold text-gray-900">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600"><Clock className="h-4.5 w-4.5" /></span>
              Derniers candidats ajoutés
            </h3>
            <Link href="/candidates" className="flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-800">
              Voir tous <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {stats.loading ? (
            <div className="py-4 text-center text-sm text-gray-400">Chargement...</div>
          ) : recentCandidates.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              <div className="mb-2 text-4xl">📂</div>
              <p>Aucun candidat pour l&apos;instant. Commencez par uploader un CV.</p>
              <Link href="/candidate/upload" className="mt-3 inline-block font-semibold text-indigo-600 hover:underline">
                Uploader un CV
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {recentCandidates.map((c) => (
                <li key={c.id} className="group flex items-center justify-between rounded-xl px-2 py-3 transition hover:bg-gray-50">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white">
                      {(c.full_name || 'C')[0].toUpperCase()}
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">{c.full_name}</p>
                      <p className="text-xs text-gray-500">{c.email}</p>
                    </div>
                  </div>
                  <Link href={`/candidates/${c.id}`} className="flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-800">
                    Voir <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Shortlist rapide */}
        <div className="card-premium overflow-hidden p-6">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display flex items-center gap-2 text-xl font-bold text-gray-900">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-600"><Star className="h-4.5 w-4.5" /></span>
              Ma shortlist
            </h3>
            <Link href="/recruiter/shortlist" className="flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:text-indigo-800">
              Voir la shortlist <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <p className="text-sm text-gray-600">
            {stats.loading
              ? '...'
              : stats.favoritesCount === 0
              ? 'Aucun candidat en shortlist. Ajoutez vos favoris depuis la liste des candidats.'
              : `Vous avez ${stats.favoritesCount} candidat${stats.favoritesCount > 1 ? 's' : ''} en shortlist.`}
          </p>
        </div>
      </div>
    </Layout>
  );
}
