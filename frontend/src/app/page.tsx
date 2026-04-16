'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

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
      setIsLoggedIn(false);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Navigation */}
      <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            🧠 AI Talent Finder
          </div>
          <div className="flex gap-4">
            <Link
              href="/auth/login"
              className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition-colors"
            >
              Connexion
            </Link>
            <Link
              href="/auth/register"
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all duration-300 font-medium"
            >
              Inscription
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <div className="animate-fade-in space-y-8">
          <div className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight">
            Trouve les meilleurs <br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              talents avec l'IA
            </span>
          </div>
          
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Laisse l'intelligence artificielle trouver les candidats parfaits pour ton entreprise. 
            Ou mets en avant ton CV pour attirer les meilleurs recruteurs.
          </p>

          <div className="flex gap-4 justify-center flex-wrap">
            <Link
              href="/auth/register?role=recruiter"
              className="group px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:shadow-xl transition-all duration-300 font-semibold flex items-center gap-2"
            >
              <span>👨‍💼</span> Je suis recruteur
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
            <Link
              href="/auth/register?role=candidate"
              className="group px-8 py-4 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:shadow-xl transition-all duration-300 font-semibold flex items-center gap-2"
            >
              <span>👤</span> Je suis candidat
              <span className="group-hover:translate-x-1 transition-transform">→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-4xl font-bold text-center text-gray-900 mb-16">
          Pourquoi AI Talent Finder?
        </h2>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Matching par IA</h3>
            <p className="text-gray-600">
              Notre modèle NER et semantic matching trouvent les meilleurs candidats automatiquement
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">⚡</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Rapide & Efficace</h3>
            <p className="text-gray-600">
              Trouve les talents en secondes, pas en jours. Gain de temps garanti.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Résultats Précis</h3>
            <p className="text-gray-600">
              Extraction de CV intelligente avec 92%+ de précision. Données fiables.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">💼</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Pour Recruteurs</h3>
            <p className="text-gray-600">
              Recherche intelligente, generation de profils idéaux, export CSV.
            </p>
          </div>

          {/* Feature 5 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">📱</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Pour Candidats</h3>
            <p className="text-gray-600">
              Upload ton CV, complète ton profil, sois découvert par les meilleurs recruteurs.
            </p>
          </div>

          {/* Feature 6 */}
          <div className="bg-white rounded-xl p-8 shadow-md hover:shadow-xl transition-all duration-300">
            <div className="text-4xl mb-4">🔒</div>
            <h3 className="text-xl font-bold text-gray-900 mb-3">Sécurisé</h3>
            <p className="text-gray-600">
              Authentification JWT, chiffrement des données, conforme RGPD.
            </p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold mb-2">92%</div>
              <p className="text-blue-100">Précision d'extraction</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">&lt;2s</div>
              <p className="text-blue-100">Temps de matching</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">27+</div>
              <p className="text-blue-100">Endpoints API</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">WCAG AA</div>
              <p className="text-blue-100">Accessibilité</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <div className="bg-white rounded-2xl p-12 shadow-lg">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Prêt à révolutionner ton recrutement?
          </h2>
          <p className="text-gray-600 mb-8 text-lg">
            Commence en 30 secondes, sans carte bancaire
          </p>
          <Link
            href="/auth/register"
            className="group inline-block px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:shadow-xl transition-all duration-300 font-semibold text-lg"
          >
            Commencer maintenant
            <span className="group-hover:translate-x-1 transition-transform inline-block ml-2">→</span>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-gray-50/50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-gray-600">
          <p>&copy; 2024 AI Talent Finder. Tous droits réservés.</p>
        </div>
      </footer>

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.8s ease-out;
        }
      `}</style>
    </div>
  );
}
