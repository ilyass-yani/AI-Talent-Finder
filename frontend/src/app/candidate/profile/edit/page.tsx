'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi, Candidate } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';
import { SkeletonProfile } from '@/components/SkeletonLoader';

export default function CandidateProfileEdit() {
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form fields
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const response = await candidatesApi.getMyProfile();
      setCandidate(response.data);
      
      // Populate form fields
      setFullName(response.data.full_name || '');
      setEmail(response.data.email || '');
      setPhone(response.data.phone || '');
      setLinkedinUrl(response.data.linkedin_url || '');
      setGithubUrl(response.data.github_url || '');
      setError(null);
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!candidate) {
      setError('Profil non chargé');
      return;
    }

    if (!fullName.trim() || !email.trim()) {
      setError('Le nom et l\'email sont requis');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await candidatesApi.updateCandidate(candidate.id, {
        full_name: fullName,
        email: email,
        phone: phone || undefined,
        linkedin_url: linkedinUrl || undefined,
        github_url: githubUrl || undefined,
      });

      setSuccess(true);
      setTimeout(() => {
        router.push('/candidate/profile');
      }, 2000);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Éditer Mon Profil</h1>
          </div>
        </nav>
        <div className="max-w-2xl mx-auto px-4 py-8">
          <div className="bg-white rounded-lg shadow-md p-8">
            <SkeletonProfile />
          </div>
        </div>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Aucun profil trouvé</p>
          <Link
            href="/candidate/upload"
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Uploader un CV
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/candidate/profile" className="text-gray-600 hover:text-gray-900">
            ← Retour
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Éditer Mon Profil</h1>
          <div></div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-md p-8">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              aria-atomic="true"
              className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg"
            >
              {error}
            </div>
          )}

          {success && (
            <div
              role="alert"
              aria-live="assertive"
              aria-atomic="true"
              className="mb-6 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg"
            >
              ✓ Profil mis à jour avec succès! Redirection en cours...
            </div>
          )}

          <form onSubmit={handleSave} className="space-y-6">
            {/* Full Name */}
            <div>
              <label htmlFor="full-name" className="block text-sm font-semibold text-gray-900 mb-2">
                Nom Complet <span aria-label="requis">*</span>
              </label>
              <input
                id="full-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                aria-required="true"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Ex: Jean Dupont"
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
                required
                aria-required="true"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Ex: jean@example.com"
              />
            </div>

            {/* Phone */}
            <div>
              <label htmlFor="phone" className="block text-sm font-semibold text-gray-900 mb-2">
                Téléphone
              </label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Ex: +33 6 12 34 56 78"
              />
            </div>

            {/* LinkedIn URL */}
            <div>
              <label htmlFor="linkedin-url" className="block text-sm font-semibold text-gray-900 mb-2">
                URL LinkedIn
              </label>
              <input
                id="linkedin-url"
                type="url"
                value={linkedinUrl}
                onChange={(e) => setLinkedinUrl(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Ex: https://linkedin.com/in/jean-dupont"
              />
              <p className="text-xs text-gray-500 mt-1">Optionnel - Votre profil LinkedIn complet</p>
            </div>

            {/* GitHub URL */}
            <div>
              <label htmlFor="github-url" className="block text-sm font-semibold text-gray-900 mb-2">
                URL GitHub
              </label>
              <input
                id="github-url"
                type="url"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="Ex: https://github.com/jean-dupont"
              />
              <p className="text-xs text-gray-500 mt-1">Optionnel - Votre profil GitHub</p>
            </div>

            {/* Note about NER fields */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>📌 Note:</strong> Les informations extraites de votre CV (titres de poste, compagnies, éducation, etc.) sont générées automatiquement. Pour les modifier, vous pouvez uploader un nouveau CV.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4 border-t border-gray-200">
              <button
                type="submit"
                disabled={saving}
                aria-label="Enregistrer les modifications du profil"
                className="flex-1 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {saving ? '💾 Enregistrement...' : '💾 Enregistrer'}
              </button>
              <Link
                href="/candidate/profile"
                aria-label="Annuler et retourner au profil"
                className="flex-1 px-6 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors font-medium text-center focus:outline-none focus:ring-2 focus:ring-gray-400 inline-flex items-center justify-center"
              >
                Annuler
              </Link>
            </div>
          </form>

          {/* Danger Zone */}
          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Zone Dangereuse</h3>
            <Link
              href="/candidate/upload"
              aria-label="Uploader un nouveau CV"
              className="inline-block px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              📤 Uploader un nouveau CV
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
