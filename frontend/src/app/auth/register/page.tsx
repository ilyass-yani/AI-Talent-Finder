'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [role, setRole] = useState<'candidate' | 'recruiter'>(() => {
    const roleParam = searchParams.get('role');
    return (roleParam as 'candidate' | 'recruiter') || 'recruiter';
  });
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await authApi.register({
        email,
        password,
        full_name: fullName,
        role,
      });
      
      // Redirect based on role
      if (role === 'candidate') {
        router.push('/candidate/dashboard');
      } else {
        router.push('/recruiter/dashboard');
      }
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRoleChange = (newRole: 'candidate' | 'recruiter') => {
    setRole(newRole);
    setError('');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900">
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
            Onboarding rapide
          </span>
          <h1 className="mt-4 text-4xl font-extrabold leading-tight text-slate-900">
            Cree ton compte
            <span className="block bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              et active ton espace
            </span>
          </h1>
          <p className="mt-4 text-slate-600">
            Choisis ton parcours candidat ou recruteur et commence a exploiter le matching IA en quelques minutes.
          </p>

          <div className="mt-8 space-y-3 text-sm text-slate-600">
            <p className="rounded-lg border-l-4 border-blue-500 bg-blue-50 px-4 py-3">Inscription en moins de 60 secondes.</p>
            <p className="rounded-lg border-l-4 border-purple-500 bg-purple-50 px-4 py-3">Experience adaptee a votre role.</p>
            <p className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50 px-4 py-3">Acces instantane au dashboard.</p>
          </div>
        </aside>

        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-100">
          <div className="mb-6">
            <h2 className="text-3xl font-extrabold text-slate-900">Creer un compte</h2>
            <p className="mt-1 text-slate-600">Choisissez votre parcours</p>
          </div>

          <div className="mb-6 grid gap-3 md:grid-cols-2" role="group" aria-label="Sélectionnez votre rôle">
            <button
              onClick={() => handleRoleChange('candidate')}
              role="radio"
              aria-checked={role === 'candidate'}
              aria-label="Candidat: Mettez votre CV en avant"
              className={`rounded-xl border-2 p-4 text-left transition focus:outline-none focus:ring-2 ${
                role === 'candidate'
                  ? 'border-blue-600 bg-blue-50 focus:ring-blue-300'
                  : 'border-slate-200 bg-white hover:border-blue-300 focus:ring-blue-200'
              }`}
            >
              <div className="text-2xl" aria-hidden="true">👤</div>
              <h3 className="mt-2 font-bold text-slate-900">Candidat</h3>
              <p className="text-sm text-slate-600">Mettez vos talents en avant</p>
            </button>

            <button
              onClick={() => handleRoleChange('recruiter')}
              role="radio"
              aria-checked={role === 'recruiter'}
              aria-label="Recruteur: Trouvez les meilleurs talents"
              className={`rounded-xl border-2 p-4 text-left transition focus:outline-none focus:ring-2 ${
                role === 'recruiter'
                  ? 'border-purple-600 bg-purple-50 focus:ring-purple-300'
                  : 'border-slate-200 bg-white hover:border-purple-300 focus:ring-purple-200'
              }`}
            >
              <div className="text-2xl" aria-hidden="true">🧑‍💼</div>
              <h3 className="mt-2 font-bold text-slate-900">Recruteur</h3>
              <p className="text-sm text-slate-600">Trouvez les meilleurs talents</p>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="full-name" className="mb-2 block text-sm font-semibold text-slate-800">
                Nom complet <span aria-label="requis">*</span>
              </label>
              <input
                id="full-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jean Dupont"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                required
                aria-required="true"
              />
            </div>

            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-semibold text-slate-800">
                Email <span aria-label="requis">*</span>
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
                Mot de passe <span aria-label="requis">*</span>
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
                aria-describedby="password-hint"
              />
              <p id="password-hint" className="mt-1 text-xs text-slate-500">
                Min. 6 caractères
              </p>
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
              aria-label={`Créer mon compte en tant que ${role === 'candidate' ? 'candidat' : 'recruteur'}`}
              className={`inline-flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3 font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-70 ${
                role === 'candidate'
                  ? 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700'
                  : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
              }`}
            >
              {isLoading ? 'Inscription...' : 'Créer mon compte'}
              {!isLoading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          <div className="mt-6 text-center text-sm text-slate-600">
            Vous avez déjà un compte ?{' '}
            <Link
              href="/auth/login"
              aria-label="Aller à la page de connexion"
              className="font-semibold text-blue-700 transition hover:text-blue-800"
            >
              Se connecter
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-pulse text-slate-400">Chargement...</div></div>}>
      <RegisterForm />
    </Suspense>
  );
}
