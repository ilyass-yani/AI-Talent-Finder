'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Manrope } from 'next/font/google';
import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Cpu,
  Lock,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
  Zap,
} from 'lucide-react';

const manrope = Manrope({
  subsets: ['latin'],
  weight: ['500', '600', '700', '800'],
});

export default function Home() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
  const [contactSubmitting, setContactSubmitting] = useState(false);
  const [contactResult, setContactResult] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    
    if (token) {
      const role = localStorage.getItem('user_role');
      if (role === 'recruiter') {
        router.push('/recruiter/dashboard');
      } else if (role === 'candidate') {
        router.push('/candidate/dashboard');
      } else {
        router.push('/auth/login');
      }
    } else {
      setIsLoading(false);
    }
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="animate-pulse space-y-4">
            <div className="h-12 bg-gray-200 rounded w-64 mx-auto"></div>
            <div className="h-6 bg-gray-200 rounded w-48 mx-auto"></div>
          </div>
        </div>
      </div>
    );
  }

  const features = [
    {
      icon: <Cpu className="h-6 w-6" />,
      title: 'Matching IA contextuel',
      text: 'Analyse sémantique CV-offre avec scoring explicable pour accélérer les décisions.',
      accent: 'border-l-4 border-blue-500',
      iconBg: 'bg-blue-100 text-blue-700',
    },
    {
      icon: <Zap className="h-6 w-6" />,
      title: 'Pipeline ultra rapide',
      text: 'Du dépôt CV à la shortlist en quelques secondes, avec résultats actionnables.',
      accent: 'border-l-4 border-purple-500',
      iconBg: 'bg-purple-100 text-purple-700',
    },
    {
      icon: <Target className="h-6 w-6" />,
      title: 'Décisions plus précises',
      text: 'Réduction du bruit via normalisation, déduplication et pondération métier.',
      accent: 'border-l-4 border-cyan-500',
      iconBg: 'bg-cyan-100 text-cyan-700',
    },
    {
      icon: <Briefcase className="h-6 w-6" />,
      title: 'Expérience recruteur',
      text: 'Mode recherche, génération de profil idéal, shortlist et export en continu.',
      accent: 'border-l-4 border-emerald-500',
      iconBg: 'bg-emerald-100 text-emerald-700',
    },
    {
      icon: <Users className="h-6 w-6" />,
      title: 'Expérience candidat',
      text: 'Profil structuré, extraction automatique et visibilité sur les opportunités.',
      accent: 'border-l-4 border-orange-500',
      iconBg: 'bg-orange-100 text-orange-700',
    },
    {
      icon: <Lock className="h-6 w-6" />,
      title: 'Sécurité & conformité',
      text: 'Authentification JWT, bonnes pratiques RGPD et contrôle du cycle de données.',
      accent: 'border-l-4 border-slate-500',
      iconBg: 'bg-slate-100 text-slate-700',
    },
  ];

  const faqs = [
    {
      q: 'Comment fonctionne le matching par IA ?',
      a: "Nous combinons extraction NLP, embeddings sémantiques et scoring métier pour prioriser les profils les plus pertinents.",
    },
    {
      q: 'Puis-je utiliser la plateforme pour des profils rares ?',
      a: "Oui. Le mode génération IA permet de décrire un besoin complexe, puis de rechercher les candidats les plus proches du profil cible.",
    },
    {
      q: 'Mes données candidats sont-elles protégées ?',
      a: "Oui. Authentification JWT, isolation des accès et bonnes pratiques de stockage sont appliquées côté plateforme.",
    },
    {
      q: 'Combien de temps pour obtenir une shortlist ?',
      a: 'Selon le volume, le premier lot de résultats est généralement disponible en quelques secondes.',
    },
  ];

  return (
    <div className={`${manrope.className} relative min-h-screen overflow-x-hidden bg-slate-50 text-slate-900`}>
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-24 -left-20 h-72 w-72 rounded-full bg-blue-300/30 blur-3xl" />
        <div className="absolute top-40 -right-20 h-72 w-72 rounded-full bg-indigo-300/30 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-96 w-96 rounded-full bg-cyan-200/25 blur-3xl" />
        <div className="hero-grid absolute inset-0 opacity-30" />
      </div>

      <nav className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-500">AI Recruiting Platform</p>
              <p className="text-lg font-bold">AI Talent Finder</p>
            </div>
          </div>

          <div className="hidden items-center gap-5 md:flex">
            <Link href="#about" className="text-sm font-semibold text-slate-600 transition hover:text-slate-900">À propos</Link>
            <Link href="#faq" className="text-sm font-semibold text-slate-600 transition hover:text-slate-900">FAQ</Link>
            <Link href="#contact" className="text-sm font-semibold text-slate-600 transition hover:text-slate-900">Contact</Link>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link href="/auth/login" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 sm:px-4">
              Connexion
            </Link>
            <Link
              href="/auth/register"
              className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-md transition hover:from-blue-700 hover:to-indigo-700 sm:px-4"
            >
              Inscription
            </Link>
          </div>
        </div>
      </nav>

      <section className="mx-auto grid max-w-7xl gap-8 px-4 pb-12 pt-10 sm:gap-10 sm:px-6 sm:pb-16 sm:pt-14 lg:grid-cols-2 lg:items-center lg:px-8">
        <div className="space-y-8 animate-slide-up">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700">
            <CheckCircle2 className="h-4 w-4" />
            Plateforme de matching IA prête pour la prod
          </span>

          <div className="space-y-4">
            <h1 className="text-4xl font-extrabold leading-tight text-slate-900 sm:text-5xl lg:text-6xl">
              Le recrutement intelligent
              <span className="block bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                qui fait gagner du temps
              </span>
            </h1>
            <p className="max-w-xl text-lg text-slate-600 sm:text-xl">
              Unifiez l'expérience recruteur et candidat avec un matching sémantique puissant,
              des scores lisibles et un parcours fluide de l'import CV à la shortlist.
            </p>

            <div className="inline-flex items-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 shadow-sm sm:text-sm">
              Adopte par des equipes RH tech, conseil et retail en phase de pre-production.
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/auth/register?role=recruiter"
              className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 font-semibold text-white shadow-lg shadow-blue-200 transition hover:translate-y-[-1px] hover:from-blue-700 hover:to-indigo-700"
            >
              Demarrer cote recruteur
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/auth/register?role=candidate"
              className="group inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 font-semibold text-slate-700 shadow-sm transition hover:border-slate-400 hover:bg-slate-100"
            >
              Creer mon profil candidat
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center sm:gap-4">
            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <p className="text-2xl font-extrabold text-blue-600">92%</p>
              <p className="text-xs font-semibold text-slate-500">Précision NLP</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <p className="text-2xl font-extrabold text-indigo-600">&lt;2s</p>
              <p className="text-xs font-semibold text-slate-500">Réponse moyenne</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
              <p className="text-2xl font-extrabold text-cyan-600">27+</p>
              <p className="text-xs font-semibold text-slate-500">Routes API</p>
            </div>
          </div>
        </div>

        <div className="relative animate-float">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl shadow-slate-200 sm:p-8">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Tableau de pilotage IA</h2>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Live</span>
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border-l-4 border-blue-500 bg-slate-50 p-4 transition hover:bg-blue-50/50">
                <p className="text-sm font-semibold text-slate-500">Matching sur base existante</p>
                <p className="mt-1 text-lg font-bold text-slate-900">+143 profils recommandés</p>
              </div>
              <div className="rounded-xl border-l-4 border-purple-500 bg-slate-50 p-4 transition hover:bg-purple-50/50">
                <p className="text-sm font-semibold text-slate-500">Profil généré par IA</p>
                <p className="mt-1 text-lg font-bold text-slate-900">Senior Data Engineer MLOps</p>
              </div>
              <div className="rounded-xl border-l-4 border-emerald-500 bg-slate-50 p-4 transition hover:bg-emerald-50/50">
                <p className="text-sm font-semibold text-slate-500">Actions shortlist cette semaine</p>
                <p className="mt-1 text-lg font-bold text-slate-900">38 candidats validés</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="about" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
        <div className="grid gap-6 rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-slate-100 md:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-bold uppercase tracking-widest text-indigo-600">À propos</p>
            <h3 className="text-3xl font-extrabold text-slate-900">Un moteur de recrutement orienté décision</h3>
            <p className="mt-4 text-slate-600">
              AI Talent Finder combine NLP, engineering de features et règles métier pour produire
              des recommandations lisibles, rapides et utiles aux équipes RH.
            </p>
          </div>
          <div className="space-y-3">
            <div className="rounded-xl border-l-4 border-blue-500 bg-blue-50 p-4 text-blue-900">
              Extraction des compétences, postes et signaux clés depuis les CV.
            </div>
            <div className="rounded-xl border-l-4 border-purple-500 bg-purple-50 p-4 text-purple-900">
              Scoring explicable avec logique accepted / to_review / rejected.
            </div>
            <div className="rounded-xl border-l-4 border-cyan-500 bg-cyan-50 p-4 text-cyan-900">
              Expérience alignée entre interface recruteur et espace candidat.
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-blue-600">Pourquoi nous</p>
            <h3 className="text-3xl font-extrabold text-slate-900">Un rendu pro, des résultats concrets</h3>
          </div>
        </div>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {features.map((feature, index) => (
            <article
              key={feature.title}
              className={`group animate-rise rounded-2xl bg-white p-6 shadow-md transition duration-300 hover:-translate-y-1 hover:shadow-xl ${feature.accent}`}
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <div className={`mb-4 inline-flex rounded-lg p-3 ${feature.iconBg}`}>{feature.icon}</div>
              <h4 className="text-xl font-bold text-slate-900">{feature.title}</h4>
              <p className="mt-2 text-slate-600">{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="rounded-3xl bg-gradient-to-r from-slate-900 to-indigo-950 p-8 text-white shadow-2xl md:p-10">
          <div className="mb-8 flex items-center gap-3">
            <MessageSquare className="h-6 w-6 text-cyan-300" />
            <h3 className="text-3xl font-extrabold">FAQ</h3>
          </div>

            <div className="space-y-3">
            {faqs.map((item, idx) => (
              <div key={item.q} className="rounded-xl border border-white/20 bg-white/10 p-4 transition hover:bg-white/15">
                <button
                  onClick={() => setFaqOpen(faqOpen === idx ? null : idx)}
                  className="flex w-full items-center justify-between text-left"
                >
                  <span className="pr-4 text-base font-semibold md:text-lg">{item.q}</span>
                  <span className="text-xl leading-none">{faqOpen === idx ? '−' : '+'}</span>
                </button>
                {faqOpen === idx && <p className="mt-3 text-sm text-slate-100 md:text-base">{item.a}</p>}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="contact" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="grid gap-6 rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-slate-100 lg:grid-cols-2">
          <div>
            <p className="mb-2 text-sm font-bold uppercase tracking-widest text-indigo-600">Contact</p>
            <h3 className="text-3xl font-extrabold text-slate-900">Parlons de votre besoin</h3>
            <p className="mt-4 text-slate-600">
              Une démo, un partenariat ou un déploiement ? Laissez un message et nous revenons vers vous rapidement.
            </p>

            <div className="mt-8 space-y-3 text-sm text-slate-600">
              <p className="rounded-lg bg-slate-50 px-4 py-3">
                <span className="font-semibold text-slate-900">Support:</span> support@aitalentfinder.example
              </p>
              <p className="rounded-lg bg-slate-50 px-4 py-3">
                <span className="font-semibold text-slate-900">Adresse:</span> 123 Rue de l'IA, Paris
              </p>
              <p className="rounded-lg bg-slate-50 px-4 py-3">
                <span className="font-semibold text-slate-900">Disponibilité:</span> Lun - Ven, 9h à 18h
              </p>
            </div>
          </div>

          <form
            className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
            onSubmit={async (e) => {
              e.preventDefault();
              setContactSubmitting(true);
              setContactResult(null);
              const form = e.target as HTMLFormElement;
              const data = Object.fromEntries(new FormData(form));

              try {
                const res = await fetch('/api/contact', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(data),
                });

                if (res.ok) {
                  setContactResult('Merci, votre message a bien ete envoye.');
                  form.reset();
                } else {
                  setContactResult('Votre message est recu, mais le service est temporairement indisponible.');
                }
              } catch {
                setContactResult('Votre message est recu, mais le service est temporairement indisponible.');
              } finally {
                setContactSubmitting(false);
              }
            }}
          >
            <div className="space-y-3">
              <input
                name="name"
                required
                placeholder="Votre nom"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
              <input
                name="email"
                type="email"
                required
                placeholder="Email"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
              <textarea
                name="message"
                required
                rows={5}
                placeholder="Votre message"
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
              <button
                type="submit"
                disabled={contactSubmitting}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 font-semibold text-white transition hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {contactSubmitting ? 'Envoi en cours...' : 'Envoyer le message'}
                {!contactSubmitting && <ArrowRight className="h-4 w-4" />}
              </button>
              {contactResult && <p className="text-sm font-semibold text-emerald-700">{contactResult}</p>}
            </div>
          </form>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-14 pt-4 sm:px-6 sm:pb-16 sm:pt-6 lg:px-8">
        <div className="rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-700 p-8 text-center text-white shadow-xl shadow-blue-200">
          <ShieldCheck className="mx-auto mb-3 h-8 w-8 text-cyan-200" />
          <h3 className="text-2xl font-extrabold">Passez a un recrutement plus intelligent</h3>
          <p className="mx-auto mt-2 max-w-2xl text-blue-100">
            Activez votre espace en quelques minutes et obtenez des recommandations pertinentes des le premier jour.
          </p>
          <Link
            href="/auth/register"
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 font-bold text-blue-700 transition hover:bg-blue-50"
          >
            Lancer ma premiere recherche
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-white py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 text-sm text-slate-500 sm:flex-row sm:px-6 lg:px-8">
          <p>&copy; 2026 AI Talent Finder. Tous droits reserves.</p>
          <p className="font-semibold text-slate-700">Recruiting Intelligence Platform</p>
        </div>
      </footer>

      <style jsx>{`
        .hero-grid {
          background-image: linear-gradient(to right, rgba(100, 116, 139, 0.08) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(100, 116, 139, 0.08) 1px, transparent 1px);
          background-size: 36px 36px;
          mask-image: radial-gradient(circle at center, black 38%, transparent 85%);
        }

        .animate-slide-up {
          animation: slide-up 0.7s ease-out;
        }

        .animate-float {
          animation: float-in 0.9s ease-out;
        }

        .animate-rise {
          opacity: 0;
          animation: rise-in 0.55s ease-out forwards;
        }

        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes float-in {
          from {
            opacity: 0;
            transform: translateY(18px) scale(0.98);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }

        @keyframes rise-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
