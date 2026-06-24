'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Sparkles, ShieldCheck } from 'lucide-react';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';
import ThemeToggle from '@/components/ThemeToggle';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSuccess(true);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 text-slate-900">
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
            <Link href="/auth/login" className="text-sm font-semibold text-slate-700 transition hover:text-indigo-600">
              Se connecter
            </Link>
          </div>
        </div>
      </nav>

      <div className="mx-auto flex min-h-[calc(100vh-69px)] w-full max-w-md items-center px-4 py-12 sm:px-6">
        <div className="card-premium anim-pop w-full p-8 sm:p-9">
          <Link
            href="/auth/login"
            className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-indigo-600"
          >
            <ArrowLeft className="h-4 w-4" /> Retour à la connexion
          </Link>

          <div className="mb-7">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-md">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h2 className="font-display text-3xl font-extrabold text-slate-900">Mot de passe oublié</h2>
            <p className="mt-1.5 text-slate-600">
              Renseignez votre email et nous vous enverrons un lien pour réinitialiser votre mot de passe.
            </p>
          </div>

          {success ? (
            <div
              role="status"
              className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm font-medium text-emerald-700"
            >
              Si un compte est associé à cet email, vous recevrez un lien de réinitialisation dans quelques minutes.
              Pensez à vérifier vos spams.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-semibold text-slate-800">
                  Adresse email
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

              {error && (
                <div
                  role="alert"
                  aria-live="assertive"
                  className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isLoading ? 'Envoi en cours...' : 'Envoyer le lien de réinitialisation'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
