'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { authApi } from '@/services/auth';
import { candidatesApi, Candidate } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';
import { SkeletonProfile } from '@/components/SkeletonLoader';
import Layout from '@/components/Layout';

export default function CandidateProfileEdit() {
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [role, setRole] = useState<string | null>(null);

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
      const me = await authApi.me();
      setRole(me.role);

      try {
        const response = await candidatesApi.getMyProfile();
        setCandidate(response.data);

        // Populate form fields from existing candidate profile
        setFullName(response.data.full_name || me.full_name || '');
        setEmail(response.data.email || me.email || '');
        setPhone(response.data.phone || '');
        setLinkedinUrl(response.data.linkedin_url || '');
        setGithubUrl(response.data.github_url || '');
      } catch {
        // No candidate profile yet: allow manual creation.
        setCandidate(null);
        setFullName(me.full_name || '');
        setEmail(me.email || '');
        setPhone('');
        setLinkedinUrl('');
        setGithubUrl('');
      }

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
      // Manual creation uses the same form when extraction failed.
      if (!fullName.trim() || !email.trim()) {
        setError('Le nom et l\'email sont requis');
        return;
      }
    } else if (!fullName.trim() || !email.trim()) {
      setError('Le nom et l\'email sont requis');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await candidatesApi.createOrUpdateMyProfile({
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
      <Layout>
        <div className="max-w-2xl mx-auto">
          <h1 className="font-display text-2xl font-bold text-gray-900 mb-6">Éditer Mon Profil</h1>
          <div className="card-premium p-8">
            <SkeletonProfile />
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
{/* Main Content */}
      <div className="max-w-2xl mx-auto">
        <h1 className="font-display text-2xl font-extrabold text-gray-900 mb-6">Éditer Mon Profil</h1>
        <div className="card-premium p-8">
          {role === 'candidate' && !candidate && (
            <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-800">
              <p className="font-semibold">Profil à créer manuellement</p>
              <p className="text-sm mt-1">
                Si l’extraction du CV a échoué ou si tu veux compléter tes informations, ce formulaire crée directement ton profil candidat.
              </p>
            </div>
          )}

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
              ✓ Profil enregistré avec succès! Redirection en cours...
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
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
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
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
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
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
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
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
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
                className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                placeholder="Ex: https://github.com/jean-dupont"
              />
              <p className="text-xs text-gray-500 mt-1">Optionnel - Votre profil GitHub</p>
            </div>

            {/* Note about NER fields */}
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>📌 Note:</strong> Les informations extraites de votre CV (titres de poste, compagnies, éducation, etc.) sont générées automatiquement. Si l’extraction est incomplète, tu peux compléter manuellement les informations ci-dessus sans re-uploader.
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4 border-t border-gray-200">
              <button
                type="submit"
                disabled={saving}
                aria-label={candidate ? 'Enregistrer les modifications du profil' : 'Créer mon profil'}
                className="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? '💾 Enregistrement...' : candidate ? '💾 Enregistrer' : '💾 Créer mon profil'}
              </button>
              <Link
                href="/candidate/profile"
                aria-label="Annuler et retourner au profil"
                className="btn-ghost flex-1"
              >
                Annuler
              </Link>
            </div>
          </form>

          {/* Danger Zone */}
          <div className="mt-8 pt-8 border-t border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Compléter le CV</h3>
            <p className="text-sm text-gray-600 mb-4">
              Tu peux enrichir ton profil manuellement ou uploader un nouveau CV si tu veux relancer l’extraction.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/candidate/upload"
                aria-label="Uploader un nouveau CV"
                className="inline-block px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                📤 Uploader un nouveau CV
              </Link>
              <Link
                href="/candidate/profile"
                className="inline-block px-6 py-2 bg-slate-200 text-slate-900 rounded-lg hover:bg-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
              >
                👁️ Voir mon profil
              </Link>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
