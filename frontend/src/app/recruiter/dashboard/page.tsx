'use client';

import Link from 'next/link';
import Layout from '@/components/Layout';
import { Target, MessageCircle, Heart, FileDown, ArrowRight } from 'lucide-react';

const PIPELINE_STEPS = [
  { step: '1', label: 'CV brut',          desc: 'PDF déposé par le candidat',              color: 'bg-slate-100 text-slate-700' },
  { step: '2', label: 'Extraction NLP',   desc: 'Compétences, expériences, diplômes',       color: 'bg-blue-100 text-blue-700' },
  { step: '3', label: 'Structuration',    desc: 'Données nettoyées et normalisées',          color: 'bg-indigo-100 text-indigo-700' },
  { step: '4', label: 'Feature Eng.',     desc: 'Vectorisation TF-IDF / BERT',              color: 'bg-violet-100 text-violet-700' },
  { step: '5', label: 'Matching',         desc: 'Similarité cosinus pondérée',              color: 'bg-purple-100 text-purple-700' },
  { step: '6', label: 'Scoring',          desc: 'Score 0-100% par compétence',              color: 'bg-emerald-100 text-emerald-700' },
  { step: '7', label: 'Décision',         desc: 'Accepté / À revoir / Rejeté',             color: 'bg-green-100 text-green-700' },
];

const ACTIONS = [
  {
    href: '/matching',
    icon: Target,
    color: 'from-indigo-600 to-indigo-700',
    ring: 'ring-indigo-200',
    title: 'Trouver des candidats',
    desc: 'Définissez vos critères (compétences + poids), lancez le matching et obtenez le classement instantané.',
    cta: 'Lancer une recherche',
  },
  {
    href: '/recruiter/chatbot',
    icon: MessageCircle,
    color: 'from-violet-600 to-violet-700',
    ring: 'ring-violet-200',
    title: 'Chatbot IA',
    desc: "Posez vos questions en langage naturel : 'Qui maîtrise Python et Docker ?', 'Compare Alice et Bob'.",
    cta: 'Ouvrir le chatbot',
  },
  {
    href: '/recruiter/shortlist',
    icon: Heart,
    color: 'from-rose-500 to-rose-600',
    ring: 'ring-rose-200',
    title: 'Ma Shortlist',
    desc: 'Retrouvez les candidats que vous avez sélectionnés depuis les résultats de matching.',
    cta: 'Voir la shortlist',
  },
  {
    href: '/recruiter/export',
    icon: FileDown,
    color: 'from-teal-600 to-teal-700',
    ring: 'ring-teal-200',
    title: 'Exporter',
    desc: 'Téléchargez vos résultats en CSV ou PDF pour partager avec votre équipe.',
    cta: 'Exporter les données',
  },
];

export default function RecruiterDashboard() {
  return (
    <Layout>
      <div className="max-w-5xl mx-auto space-y-10">

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Bonjour 👋</h1>
          <p className="mt-1 text-gray-500 text-lg">
            Bienvenue sur AI Talent Finder — votre assistant de recrutement intelligent.
          </p>
        </div>

        {/* Pipeline visuel */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400 mb-5">
            Comment ça marche — le pipeline IA
          </h2>
          <div className="flex flex-wrap gap-2 items-center">
            {PIPELINE_STEPS.map((s, i) => (
              <div key={s.step} className="flex items-center gap-2">
                <div className={`rounded-xl px-4 py-2 text-center ${s.color}`}>
                  <div className="text-xs font-bold mb-0.5">Étape {s.step}</div>
                  <div className="text-sm font-semibold">{s.label}</div>
                  <div className="text-xs opacity-75 mt-0.5 hidden sm:block">{s.desc}</div>
                </div>
                {i < PIPELINE_STEPS.length - 1 && (
                  <ArrowRight className="h-4 w-4 text-gray-300 flex-shrink-0" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400 mb-5">
            Que voulez-vous faire ?
          </h2>
          <div className="grid sm:grid-cols-2 gap-5">
            {ACTIONS.map(({ href, icon: Icon, color, ring, title, desc, cta }) => (
              <Link
                key={href}
                href={href}
                className={`group block bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:ring-2 ${ring} transition-all p-6`}
              >
                <div className={`inline-flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br ${color} mb-4`}>
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
                <p className="text-sm text-gray-500 mb-4 leading-relaxed">{desc}</p>
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-600 group-hover:gap-2.5 transition-all">
                  {cta} <ArrowRight className="h-4 w-4" />
                </span>
              </Link>
            ))}
          </div>
        </div>

      </div>
    </Layout>
  );
}
