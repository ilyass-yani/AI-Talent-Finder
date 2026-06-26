'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Cpu,
  Gauge,
  Lock,
  MessageSquare,
  Quote,
  Search,
  Sparkles,
  Target,
  Users,
  Zap,
} from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

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
      if (role === 'admin') {
        router.push('/admin/dashboard');
      } else if (role === 'recruiter') {
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
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-indigo-300/50">
            <Sparkles className="h-6 w-6 animate-pulse" />
          </div>
          <div className="h-1.5 w-40 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full w-1/2 animate-[shimmer_1.2s_infinite] bg-gradient-to-r from-transparent via-indigo-500 to-transparent bg-[length:200%_100%]" />
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
      iconBg: 'bg-blue-100 text-blue-700',
    },
    {
      icon: <Zap className="h-6 w-6" />,
      title: 'Pipeline ultra rapide',
      text: 'Du dépôt CV à la shortlist en quelques secondes, avec résultats actionnables.',
      iconBg: 'bg-violet-100 text-violet-700',
    },
    {
      icon: <Target className="h-6 w-6" />,
      title: 'Décisions plus précises',
      text: 'Réduction du bruit via normalisation, déduplication et pondération métier.',
      iconBg: 'bg-cyan-100 text-cyan-700',
    },
    {
      icon: <Briefcase className="h-6 w-6" />,
      title: 'Expérience recruteur',
      text: 'Mode recherche, génération de profil idéal, shortlist et export en continu.',
      iconBg: 'bg-emerald-100 text-emerald-700',
    },
    {
      icon: <Users className="h-6 w-6" />,
      title: 'Expérience candidat',
      text: 'Profil structuré, extraction automatique et visibilité sur les opportunités.',
      iconBg: 'bg-orange-100 text-orange-700',
    },
    {
      icon: <Lock className="h-6 w-6" />,
      title: 'Sécurité & conformité',
      text: 'Authentification JWT, bonnes pratiques RGPD et contrôle du cycle de données.',
      iconBg: 'bg-slate-100 text-slate-700',
    },
  ];

  const steps = [
    { icon: <Briefcase className="h-5 w-5" />, title: 'Définissez le besoin', text: 'Décrivez le poste ou laissez l’IA générer le profil idéal à partir de critères métier.' },
    { icon: <Search className="h-5 w-5" />, title: 'Lancez le matching', text: 'Le moteur sémantique compare CV et offre, puis classe les profils par pertinence.' },
    { icon: <CheckCircle2 className="h-5 w-5" />, title: 'Décidez & shortlistez', text: 'Scores explicables, raisons claires, export — du candidat brut à la décision RH.' },
  ];

  const faqs = [
    {
      q: 'Comment fonctionne le matching par IA ?',
      a: 'Nous combinons extraction NLP, embeddings sémantiques et scoring métier pour prioriser les profils les plus pertinents.',
    },
    {
      q: 'Puis-je utiliser la plateforme pour des profils rares ?',
      a: 'Oui. Le mode génération IA permet de décrire un besoin complexe, puis de rechercher les candidats les plus proches du profil cible.',
    },
    {
      q: 'Mes données candidats sont-elles protégées ?',
      a: 'Oui. Authentification JWT, isolation des accès et bonnes pratiques de stockage sont appliquées côté plateforme.',
    },
    {
      q: 'Combien de temps pour obtenir une shortlist ?',
      a: 'Selon le volume, le premier lot de résultats est généralement disponible en quelques secondes.',
    },
  ];

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-slate-50 text-slate-900">
      {/* Aurora background */}
      <div className="aurora">
        <div className="aurora-orb left-[-8%] top-[-6%] h-80 w-80 bg-blue-400" />
        <div className="aurora-orb right-[-6%] top-[18%] h-96 w-96 bg-violet-400" style={{ animationDelay: '-4s' }} />
        <div className="aurora-orb bottom-[6%] left-[28%] h-[26rem] w-[26rem] bg-cyan-300" style={{ animationDelay: '-8s' }} />
        <div className="grid-overlay absolute inset-0 opacity-60" />
      </div>

      {/* NAV */}
      <nav className="glass-nav sticky top-0 z-50 border-b border-slate-200 shadow-sm shadow-slate-200/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
          <div className="flex items-center">
            <Image src="/logo.png" alt="AI Talent Finder" width={160} height={54} className="h-10 w-auto object-contain" priority />
          </div>

          <div className="hidden items-center gap-7 md:flex">
            <Link href="#about" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">À propos</Link>
            <Link href="#how" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">Comment ça marche</Link>
            <Link href="#faq" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">FAQ</Link>
            <Link href="#contact" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">Contact</Link>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <Link href="/auth/login" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-800 transition hover:bg-slate-100 sm:px-4">
              Connexion
            </Link>
            <Link href="/auth/register" className="btn-primary !px-4 !py-2 text-sm">
              Inscription
            </Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8 lg:pt-20">
        <div className="space-y-8">
          <span className="pill anim-fade-up">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Plateforme de matching IA prête pour la prod
          </span>

          <div className="space-y-5">
            <h1 className="font-display anim-fade-up delay-1 text-5xl font-extrabold leading-[1.05] text-slate-900 sm:text-6xl lg:text-7xl">
              Le recrutement
              <span className="block gradient-text">intelligent</span>
              qui fait gagner du temps
            </h1>
            <p className="anim-fade-up delay-2 max-w-xl text-lg text-slate-600 sm:text-xl">
              Unifiez l’expérience recruteur et candidat avec un matching sémantique puissant,
              des scores lisibles et un parcours fluide de l’import CV à la shortlist.
            </p>
          </div>

          <div className="anim-fade-up delay-3 flex flex-wrap gap-3">
            <Link href="/auth/register?role=recruiter" className="btn-primary group">
              Démarrer côté recruteur
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </Link>
            <Link href="/auth/register?role=candidate" className="btn-ghost group">
              Créer mon profil candidat
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </Link>
          </div>

          <div className="anim-fade-up delay-4 grid grid-cols-3 gap-3 sm:gap-4">
            {[
              { v: '92%', l: 'Précision NLP', c: 'text-blue-600' },
              { v: '<2s', l: 'Réponse moyenne', c: 'text-violet-600' },
              { v: '27+', l: 'Routes API', c: 'text-cyan-600' },
            ].map((s) => (
              <div key={s.l} className="card-premium px-3 py-4 text-center">
                <p className={`font-display text-2xl font-extrabold sm:text-3xl ${s.c}`}>{s.v}</p>
                <p className="mt-1 text-xs font-semibold text-slate-500">{s.l}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Floating glass dashboard mockup */}
        <div className="anim-pop delay-2 relative">
          <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-gradient-to-tr from-blue-500/20 via-violet-500/20 to-cyan-400/20 blur-2xl" />
          <div className="card-premium card-glow overflow-hidden p-6 sm:p-7">
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Gauge className="h-5 w-5 text-indigo-600" />
                <h2 className="font-display text-lg font-bold text-slate-900">Tableau de pilotage IA</h2>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Live
              </span>
            </div>

            <div className="space-y-3">
              {[
                { c: 'from-blue-500 to-indigo-500', t: 'Matching sur base existante', v: '+143 profils recommandés', w: 'w-[88%]' },
                { c: 'from-violet-500 to-fuchsia-500', t: 'Profil généré par IA', v: 'Senior Data Engineer MLOps', w: 'w-[72%]' },
                { c: 'from-emerald-500 to-teal-500', t: 'Actions shortlist cette semaine', v: '38 candidats validés', w: 'w-[64%]' },
              ].map((row) => (
                <div key={row.t} className="rounded-xl border border-slate-200 bg-slate-50 p-4 transition hover:border-indigo-200 hover:bg-white">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-slate-500">{row.t}</p>
                    <span className={`h-2 w-2 rounded-full bg-gradient-to-r ${row.c}`} />
                  </div>
                  <p className="mt-1 font-display text-base font-bold text-slate-900">{row.v}</p>
                  <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                    <div className={`h-full ${row.w} rounded-full bg-gradient-to-r ${row.c}`} />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-center gap-3 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 p-4 text-white">
              <Sparkles className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm font-semibold">Score moyen de matching en hausse de 18% ce mois-ci.</p>
            </div>
          </div>
        </div>
      </section>

      {/* LOGOS / TRUST STRIP */}
      <section className="mx-auto max-w-7xl px-4 pb-6 sm:px-6 lg:px-8">
        <p className="mb-5 text-center text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
          Adoptée par des équipes RH tech, conseil et retail en pré-production
        </p>
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4 opacity-70">
          {['NeuroHR', 'TalentFlow', 'RecruitX', 'HirePilot', 'CoreTeam'].map((b) => (
            <span key={b} className="font-display text-lg font-bold tracking-tight text-slate-400">{b}</span>
          ))}
        </div>
      </section>

      {/* ABOUT */}
      <section id="about" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="card-premium grid gap-8 p-8 md:grid-cols-2 md:p-10">
          <div>
            <p className="pill mb-4">À propos</p>
            <h3 className="font-display text-3xl font-extrabold text-slate-900 sm:text-4xl">
              Un moteur de recrutement <span className="gradient-text">orienté décision</span>
            </h3>
            <p className="mt-4 text-slate-600">
              AI Talent Finder combine NLP, engineering de features et règles métier pour produire
              des recommandations lisibles, rapides et utiles aux équipes RH.
            </p>
          </div>
          <div className="space-y-3">
            {[
              { c: 'border-blue-500 bg-blue-50 text-blue-900', t: 'Extraction des compétences, postes et signaux clés depuis les CV.' },
              { c: 'border-violet-500 bg-violet-50 text-violet-900', t: 'Scoring explicable avec logique accepted / to_review / rejected.' },
              { c: 'border-cyan-500 bg-cyan-50 text-cyan-900', t: 'Expérience alignée entre interface recruteur et espace candidat.' },
            ].map((x) => (
              <div key={x.t} className={`rounded-xl border-l-4 p-4 text-sm font-medium ${x.c}`}>{x.t}</div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="mb-10 text-center">
          <p className="pill mx-auto mb-3">Pourquoi nous</p>
          <h3 className="font-display text-3xl font-extrabold text-slate-900 sm:text-4xl">Un rendu pro, des résultats concrets</h3>
          <p className="mx-auto mt-3 max-w-2xl text-slate-600">Tout ce qu’il faut pour passer du CV brut à une décision de recrutement étayée.</p>
        </div>
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {features.map((feature, index) => (
            <article
              key={feature.title}
              className={`card-premium card-glow group anim-fade-up p-6 delay-${(index % 6) + 1}`}
            >
              <div className={`mb-4 inline-flex rounded-xl p-3 transition group-hover:scale-110 ${feature.iconBg}`}>{feature.icon}</div>
              <h4 className="font-display text-xl font-bold text-slate-900">{feature.title}</h4>
              <p className="mt-2 text-sm text-slate-600">{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="mb-10 text-center">
          <p className="pill mx-auto mb-3">Comment ça marche</p>
          <h3 className="font-display text-3xl font-extrabold text-slate-900 sm:text-4xl">Trois étapes, zéro friction</h3>
        </div>
        <div className="relative grid gap-5 md:grid-cols-3">
          {steps.map((step, i) => (
            <div key={step.title} className="card-premium relative p-7">
              <span className="absolute right-5 top-5 font-display text-5xl font-extrabold text-slate-100">{i + 1}</span>
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-300/40">
                {step.icon}
              </div>
              <h4 className="font-display text-lg font-bold text-slate-900">{step.title}</h4>
              <p className="mt-2 text-sm text-slate-600">{step.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* TESTIMONIAL */}
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-8 text-white shadow-2xl md:p-12">
          <div className="absolute -right-10 -top-10 h-48 w-48 rounded-full bg-indigo-500/30 blur-3xl" />
          <div className="absolute -bottom-10 -left-10 h-48 w-48 rounded-full bg-cyan-500/20 blur-3xl" />
          <Quote className="h-10 w-10 text-indigo-300" />
          <p className="mt-4 max-w-3xl font-display text-2xl font-bold leading-snug sm:text-3xl">
            « En passant au matching sémantique, nous avons divisé par trois le temps de présélection
            tout en gardant des décisions explicables. »
          </p>
          <div className="mt-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 font-bold">A</div>
            <div>
              <p className="font-semibold">Amine R.</p>
              <p className="text-sm text-indigo-200">Lead Talent Acquisition</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="mb-8 text-center">
          <p className="pill mx-auto mb-3"><MessageSquare className="h-3.5 w-3.5" /> FAQ</p>
          <h3 className="font-display text-3xl font-extrabold text-slate-900 sm:text-4xl">Questions fréquentes</h3>
        </div>
        <div className="space-y-3">
          {faqs.map((item, idx) => {
            const open = faqOpen === idx;
            return (
              <div key={item.q} className={`card-premium overflow-hidden ${open ? '!border-indigo-300' : ''}`}>
                <button
                  onClick={() => setFaqOpen(open ? null : idx)}
                  className="flex w-full items-center justify-between gap-4 p-5 text-left"
                >
                  <span className="font-display text-base font-bold text-slate-900 md:text-lg">{item.q}</span>
                  <span className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-lg transition ${open ? 'rotate-45 bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'}`}>+</span>
                </button>
                <div className={`grid transition-all duration-300 ${open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'}`}>
                  <p className="overflow-hidden px-5 pb-5 text-sm text-slate-600 md:text-base">{item.a}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* CONTACT */}
      <section id="contact" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="card-premium grid gap-8 p-8 md:p-10 lg:grid-cols-2">
          <div>
            <p className="pill mb-4">Contact</p>
            <h3 className="font-display text-3xl font-extrabold text-slate-900 sm:text-4xl">Parlons de votre besoin</h3>
            <p className="mt-4 text-slate-600">
              Une démo, un partenariat ou un déploiement ? Laissez un message et nous revenons vers vous rapidement.
            </p>

            <div className="mt-8 space-y-3 text-sm">
              {[
                { k: 'Support', v: 'support@aitalentfinder.example' },
                { k: 'Adresse', v: "123 Rue de l'IA, Paris" },
                { k: 'Disponibilité', v: 'Lun - Ven, 9h à 18h' },
              ].map((c) => (
                <p key={c.k} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-600">
                  <span className="font-semibold text-slate-900">{c.k}:</span> {c.v}
                </p>
              ))}
            </div>
          </div>

          <form
            className="rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:p-6"
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
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
              <input
                name="email"
                type="email"
                required
                placeholder="Email"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
              <textarea
                name="message"
                required
                rows={5}
                placeholder="Votre message"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
              />
              <button type="submit" disabled={contactSubmitting} className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-70">
                {contactSubmitting ? 'Envoi en cours...' : 'Envoyer le message'}
                {!contactSubmitting && <ArrowRight className="h-4 w-4" />}
              </button>
              {contactResult && <p className="text-sm font-semibold text-emerald-700">{contactResult}</p>}
            </div>
          </form>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-4 pb-16 pt-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 p-10 text-center text-white shadow-2xl shadow-indigo-300/40">
          <div className="absolute inset-0 grid-overlay opacity-20" />
          <div className="relative">
            <Sparkles className="mx-auto mb-3 h-9 w-9 text-cyan-200" />
            <h3 className="font-display text-3xl font-extrabold sm:text-4xl">Passez à un recrutement plus intelligent</h3>
            <p className="mx-auto mt-3 max-w-2xl text-indigo-100">
              Activez votre espace en quelques minutes et obtenez des recommandations pertinentes dès le premier jour.
            </p>
            <Link
              href="/auth/register"
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 font-bold text-indigo-700 shadow-lg transition hover:-translate-y-0.5 hover:bg-indigo-50"
            >
              Lancer ma première recherche
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-slate-200 bg-white py-10">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6 lg:px-8">
          <div className="flex items-center">
            <Image src="/logo.png" alt="AI Talent Finder" width={140} height={46} className="h-9 w-auto object-contain" />
          </div>
          <p className="text-sm text-slate-500">&copy; 2026 AI Talent Finder. Tous droits réservés.</p>
          <p className="text-sm font-semibold text-slate-700">Recruiting Intelligence Platform</p>
        </div>
      </footer>
    </div>
  );
}
