'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { Manrope } from 'next/font/google';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';

const manrope = Manrope({
  subsets: ['latin'],
  weight: ['500', '600', '700', '800'],
});

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
      } else {
        // Admin or unknown role
        router.push('/');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`${manrope.className} relative min-h-screen overflow-hidden bg-slate-50 text-slate-900`}>
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-24 -left-16 h-72 w-72 rounded-full bg-blue-300/30 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-indigo-300/30 blur-3xl" />
      </div>

      <nav className="border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-200">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">AI Recruiting</p>
              <p className="text-lg font-bold">AI Talent Finder</p>
            </div>
          </Link>
          <Link href="/" className="text-sm font-semibold text-slate-600 transition hover:text-slate-900">
            Retour a l'accueil
          </Link>
        </div>
      </nav>

      <div className="mx-auto grid min-h-[calc(100vh-72px)] w-full max-w-6xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8">
        <aside className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-100">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            <CheckCircle2 className="h-4 w-4" />
            Espace securise
          </span>
          <h1 className="mt-4 text-4xl font-extrabold leading-tight text-slate-900">
            Connecte-toi a
            <span className="block bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              ton espace intelligent
            </span>
          </h1>
          <p className="mt-4 text-slate-600">
            Accede a ton dashboard recruteur ou candidat, avec suivi de matching et actions prioritaires.
          </p>

          <div className="mt-8 space-y-3 text-sm text-slate-600">
            <p className="rounded-lg border-l-4 border-blue-500 bg-blue-50 px-4 py-3">Recommandations en temps reel.</p>
            <p className="rounded-lg border-l-4 border-indigo-500 bg-indigo-50 px-4 py-3">Parcours candidat et recruteur unifie.</p>
            <p className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50 px-4 py-3">Authentification JWT et acces controle.</p>
          </div>
        </aside>

        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-100">
          <div className="mb-6">
            <h2 className="text-3xl font-extrabold text-slate-900">Se connecter</h2>
            <p className="mt-1 text-slate-600">Accedez a votre compte</p>
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
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                required
                aria-required="true"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-semibold text-slate-800">
                Mot de passe
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
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
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-3 font-semibold text-white transition hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isLoading ? 'Connexion...' : 'Se connecter'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-600">
            Pas encore de compte ?{' '}
            <Link
              href="/auth/register"
              aria-label="Aller à la page de création de compte"
              className="font-semibold text-blue-700 transition hover:text-blue-800"
            >
              Créer un compte
            </Link>
          </div>

          <div className="mt-8 rounded-xl border border-blue-200 bg-blue-50 p-4 text-xs text-blue-900">
            <p className="mb-2 font-semibold">Comptes de test :</p>
            <ul className="space-y-1">
              <li><strong>Candidat:</strong> alice@test.com / password123</li>
              <li><strong>Recruteur:</strong> bob@test.com / password123</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
