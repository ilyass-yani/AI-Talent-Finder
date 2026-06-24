'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Sparkles, KeyRound, Eye, EyeOff } from 'lucide-react';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';
import ThemeToggle from '@/components/ThemeToggle';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setError('Lien de réinitialisation invalide. Veuillez refaire une demande.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setIsLoading(true);
    try {
      await authApi.resetPassword(token, newPassword);
      setSuccess(true);
      setTimeout(() => router.push('/auth/login'), 3000);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card-premium anim-pop w-full p-8 sm:p-9">
      <Link
        href="/auth/login"
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-indigo-600"
      >
        <ArrowLeft className="h-4 w-4" /> Retour à la connexion
      </Link>

      <div className="mb-7">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-md">
          <KeyRound className="h-6 w-6" />
        </div>
        <h2 className="font-display text-3xl font-extrabold text-slate-900">Nouveau mot de passe</h2>
        <p className="mt-1.5 text-slate-600">Choisissez un nouveau mot de passe sécurisé.</p>
      </div>

      {success ? (
        <div
          role="status"
          className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm font-medium text-emerald-700"
        >
          Mot de passe réinitialisé avec succès ! Vous allez être redirigé vers la page de connexion…
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="new-password" className="mb-2 block text-sm font-semibold text-slate-800">
              Nouveau mot de passe
            </label>
            <div className="relative">
              <input
                id="new-password"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-11 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                required
                minLength={6}
                aria-required="true"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
                aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="confirm-password" className="mb-2 block text-sm font-semibold text-slate-800">
              Confirmer le mot de passe
            </label>
            <input
              id="confirm-password"
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
              className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !token}
            className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isLoading ? 'Réinitialisation...' : 'Réinitialiser le mot de passe'}
          </button>
        </form>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
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
        <Suspense fallback={<div className="card-premium w-full p-8 text-center text-slate-500">Chargement…</div>}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
