'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';
import ThemeToggle from '@/components/ThemeToggle';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await authApi.login({
        email,
        password,
      });

      // Redirect based on user role
      if (response.user.role === 'candidate') {
        router.push('/candidate/dashboard');
      } else if (response.user.role === 'recruiter') {
        router.push('/recruiter/dashboard');
      } else if (response.user.role === 'admin') {
        router.push('/admin/dashboard');
      } else {
        router.push('/');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900">
      {/* Aurora background */}
      <div className="aurora">
        <div className="aurora-orb left-[-8%] top-[-6%] h-80 w-80 bg-blue-400" />
        <div className="aurora-orb right-[-6%] bottom-[2%] h-96 w-96 bg-violet-400" style={{ animationDelay: '-5s' }} />
        <div className="grid-overlay absolute inset-0 opacity-50" />
      </div>

      <nav className="glass-nav border-b border-slate-200 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-indigo-300/50">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[0.7rem] font-bold uppercase tracking-[0.18em] text-indigo-600">AI Recruiting</p>
              <p className="font-display text-lg font-bold leading-none text-slate-900">AI Talent Finder</p>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">
              Retour à l&apos;accueil
            </Link>
          </div>
        </div>
      </nav>

      <div className="mx-auto grid min-h-[calc(100vh-69px)] w-full max-w-6xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:px-8">
        {/* Left brand panel */}
        <aside className="hidden lg:block anim-fade-up">
          <span className="pill mb-5"><ShieldCheck className="h-3.5 w-3.5" /> Espace sécurisé</span>
          <h1 className="font-display text-5xl font-extrabold leading-[1.05] text-slate-900">
            Connecte-toi à
            <span className="block gradient-text">ton espace intelligent</span>
          </h1>
          <p className="mt-5 max-w-md text-lg text-slate-600">
            Accède à ton dashboard recruteur ou candidat, avec suivi de matching et actions prioritaires.
          </p>

          <div className="mt-9 space-y-3">
            {[
              { icon: <Zap className="h-4 w-4" />, c: 'from-blue-500 to-indigo-500', t: 'Recommandations en temps réel.' },
              { icon: <Sparkles className="h-4 w-4" />, c: 'from-violet-500 to-fuchsia-500', t: 'Parcours candidat et recruteur unifié.' },
              { icon: <ShieldCheck className="h-4 w-4" />, c: 'from-emerald-500 to-teal-500', t: 'Authentification JWT et accès contrôlé.' },
            ].map((x) => (
              <div key={x.t} className="glass-panel flex items-center gap-3 rounded-xl px-4 py-3">
                <span className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-white ${x.c}`}>{x.icon}</span>
                <span className="text-sm font-medium text-slate-700">{x.t}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* Login card */}
        <div className="card-premium anim-pop p-8 sm:p-9">
          <div className="mb-7">
            <h2 className="font-display text-3xl font-extrabold text-slate-900">Se connecter</h2>
            <p className="mt-1.5 text-slate-600">Accédez à votre compte</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-semibold text-slate-800">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="votre@email.com"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                required
                aria-required="true"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label htmlFor="password" className="text-sm font-semibold text-slate-800">
                  Mot de passe
                </label>
                <Link
                  href="/auth/forgot-password"
                  className="text-xs font-medium text-indigo-600 transition hover:text-indigo-700"
                >
                  Mot de passe oublié ?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                required
                minLength={6}
                aria-required="true"
              />
            </div>

            {error && (
              <div
                role="alert"
                aria-live="assertive"
                aria-atomic="true"
                className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              aria-label="Se connecter à ton compte"
              className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? 'Connexion...' : 'Se connecter'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-6 flex items-center gap-3 text-xs text-slate-400">
            <span className="h-px flex-1 bg-slate-200" /> ou <span className="h-px flex-1 bg-slate-200" />
          </div>

          <div className="mt-6 text-center text-sm text-slate-600">
            Pas encore de compte ?{' '}
            <Link
              href="/auth/register"
              aria-label="Aller à la page de création de compte"
              className="font-semibold text-indigo-600 transition hover:text-indigo-700"
            >
              Créer un compte
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
