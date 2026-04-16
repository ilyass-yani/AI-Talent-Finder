'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';

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
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Navigation */}
      <Link href="/" className="block p-4">
        <div className="text-2xl font-bold text-indigo-600">🧠 AI Talent Finder</div>
      </Link>

      <div className="min-h-screen flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Se connecter</h1>
            <p className="text-gray-600">Accédez à votre compte</p>
          </div>

          {/* Login Form */}
          <div className="bg-white rounded-lg shadow-md p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-gray-900 mb-2">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="votre@email.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                  aria-required="true"
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-gray-900 mb-2">
                  Mot de passe
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                  minLength={6}
                  aria-required="true"
                />
              </div>

              {/* Error Message */}
              {error && (
                <div
                  role="alert"
                  aria-live="assertive"
                  aria-atomic="true"
                  className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm"
                >
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading}
                aria-label="Se connecter à ton compte"
                className="w-full px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {isLoading ? 'Connexion...' : 'Se connecter'}
              </button>
            </form>

            {/* Register Link */}
            <div className="mt-6 text-center">
              <span className="text-gray-600">Pas encore de compte? </span>
              <Link
                href="/auth/register"
                aria-label="Aller à la page de création de compte"
                className="text-blue-600 hover:text-blue-700 font-semibold focus:outline-none focus:underline"
              >
                Créer un compte
              </Link>
            </div>

            {/* Back to Home */}
            <div className="mt-4 text-center">
              <Link
                href="/"
                aria-label="Revenir à la page d'accueil"
                className="text-gray-500 hover:text-gray-700 text-sm focus:outline-none focus:underline"
              >
                ← Retour à l'accueil
              </Link>
            </div>
          </div>

          {/* Test Accounts Info */}
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900 font-semibold mb-2">Comptes de test:</p>
            <ul className="text-xs text-blue-800 space-y-1">
              <li><strong>Candidat:</strong> alice@test.com / password123</li>
              <li><strong>Recruteur:</strong> bob@test.com / password123</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
