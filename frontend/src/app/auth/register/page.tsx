'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/services/auth';
import { getErrorMessage } from '@/utils/errorHandler';

export default function RegisterPage() {
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
      const response = await authApi.register({
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
    } catch (err: any) {
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Navigation */}
      <Link href="/" className="block p-4">
        <div className="text-2xl font-bold text-indigo-600">🧠 AI Talent Finder</div>
      </Link>

      <div className="min-h-screen flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Créez votre compte</h1>
            <p className="text-gray-600">Choisissez votre parcours</p>
          </div>

          {/* Role Selection */}
          <div className="grid md:grid-cols-2 gap-4 mb-8" role="group" aria-label="Sélectionnez votre rôle">
            <button
              onClick={() => handleRoleChange('candidate')}
              role="radio"
              aria-checked={role === 'candidate'}
              aria-label="Candidat: Mettez votre CV en avant"
              className={`p-6 rounded-lg border-2 transition text-left focus:outline-none focus:ring-2 ${
                role === 'candidate'
                  ? 'border-blue-600 bg-blue-50 focus:ring-blue-400'
                  : 'border-gray-200 bg-white hover:border-blue-300 focus:ring-blue-300'
              }`}
            >
              <div className="text-3xl mb-2" aria-hidden="true">
                👤
              </div>
              <h3 className="font-bold text-gray-900 mb-1">Candidat</h3>
              <p className="text-sm text-gray-600">Mettez vos talents en avant</p>
            </button>

            <button
              onClick={() => handleRoleChange('recruiter')}
              role="radio"
              aria-checked={role === 'recruiter'}
              aria-label="Recruteur: Trouvez les meilleurs talents"
              className={`p-6 rounded-lg border-2 transition text-left focus:outline-none focus:ring-2 ${
                role === 'recruiter'
                  ? 'border-purple-600 bg-purple-50 focus:ring-purple-400'
                  : 'border-gray-200 bg-white hover:border-purple-300 focus:ring-purple-300'
              }`}
            >
              <div className="text-3xl mb-2" aria-hidden="true">
                🧑‍💼
              </div>
              <h3 className="font-bold text-gray-900 mb-1">Recruteur</h3>
              <p className="text-sm text-gray-600">Trouvez les meilleurs talents</p>
            </button>
          </div>

          {/* Register Form */}
          <div className="bg-white rounded-lg shadow-md p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Full Name */}
              <div>
                <label htmlFor="full-name" className="block text-sm font-semibold text-gray-900 mb-2">
                  Nom complet <span aria-label="requis">*</span>
                </label>
                <input
                  id="full-name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jean Dupont"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                  aria-required="true"
                />
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-semibold text-gray-900 mb-2">
                  Email <span aria-label="requis">*</span>
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
                  Mot de passe <span aria-label="requis">*</span>
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
                  aria-describedby="password-hint"
                />
                <p id="password-hint" className="text-gray-500 text-xs mt-1">
                  Min. 6 caractères
                </p>
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
                aria-label={`Créer mon compte en tant que ${role === 'candidate' ? 'candidat' : 'recruteur'}`}
                className={`w-full px-6 py-3 text-white font-semibold rounded-lg transition focus:outline-none focus:ring-2 ${
                  role === 'candidate'
                    ? 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
                    : 'bg-purple-600 hover:bg-purple-700 focus:ring-purple-500'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {isLoading ? 'Inscription...' : 'Créer mon compte'}
              </button>
            </form>

            {/* Login Link */}
            <div className="mt-6 text-center">
              <span className="text-gray-600">Vous avez déjà un compte? </span>
              <Link
                href="/auth/login"
                aria-label="Aller à la page de connexion"
                className="text-blue-600 hover:text-blue-700 font-semibold focus:outline-none focus:underline"
              >
                Se connecter
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
