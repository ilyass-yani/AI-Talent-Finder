'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { candidatesApi, Candidate } from '@/services/candidates';
import { favoritesApi } from '@/services/favorites';
import { getErrorMessage } from '@/utils/errorHandler';
import { SkeletonProfile } from '@/components/SkeletonLoader';

export default function CandidateDetail() {
  const params = useParams();
  const candidateId = parseInt(params.id as string);

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isFavorite, setIsFavorite] = useState(false);
  const [addingFavorite, setAddingFavorite] = useState(false);

  const parseJsonList = (value?: string | null): string[] => {
    if (!value) {
      return [];
    }

    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : [];
    } catch {
      return [];
    }
  };

  useEffect(() => {
    const fetchCandidate = async () => {
      try {
        const response = await candidatesApi.getCandidate(candidateId);
        setCandidate(response.data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchCandidate();
  }, [candidateId]);

  const toggleFavorite = async () => {
    setAddingFavorite(true);
    try {
      if (isFavorite) {
        await favoritesApi.removeFavorite(candidateId);
        setIsFavorite(false);
      } else {
        await favoritesApi.addFavorite(candidateId);
        setIsFavorite(true);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setAddingFavorite(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-gray-900">Profil Candidat</h1>
          </div>
        </nav>
        <div className="max-w-4xl mx-auto px-4 py-8">
          <SkeletonProfile />
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl mb-4">❌</div>
          <p className="text-gray-600">{error || 'Candidat non trouvé'}</p>
          <Link href="/recruiter/dashboard" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
            ← Retour au Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const extractedJobTitles = parseJsonList(candidate.extracted_job_titles);
  const extractedCompanies = parseJsonList(candidate.extracted_companies);
  const extractedEmails = parseJsonList(candidate.extracted_emails);
  const extractedPhones = parseJsonList(candidate.extracted_phones);
  const extractedEducation = parseJsonList(candidate.extracted_education);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/recruiter/dashboard" className="text-gray-600 hover:text-gray-900">
            ← Retour
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Profil Candidat</h1>
          <button
            onClick={toggleFavorite}
            disabled={addingFavorite}
            aria-pressed={isFavorite}
            aria-label={isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
            className={`text-2xl transition-colors focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded p-1 ${
              isFavorite ? 'text-yellow-400 hover:text-yellow-500' : 'text-gray-400 hover:text-yellow-400'
            }`}
          >
            ★
          </button>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="grid md:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="md:col-span-2 space-y-6">
            {/* Header */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-3xl font-bold text-gray-900" id="candidate-header">
                {candidate.full_name}
              </h2>
              <p className="text-gray-600 mt-1">{candidate.email}</p>
              {candidate.phone && <p className="text-gray-600">{candidate.phone}</p>}

              {/* Links */}
              <div className="flex gap-4 mt-4">
                {candidate.linkedin_url && (
                  <a
                    href={candidate.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Visitez le profil LinkedIn de ce candidat (ouverture dans un nouvel onglet)"
                    className="text-blue-600 hover:text-blue-700 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1"
                  >
                    🔗 LinkedIn
                  </a>
                )}
                {candidate.github_url && (
                  <a
                    href={candidate.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Visitez le profil GitHub de ce candidat (ouverture dans un nouvel onglet)"
                    className="text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-1 focus:ring-gray-500 rounded px-1"
                  >
                    🔗 GitHub
                  </a>
                )}
              </div>

              {/* Quality Score */}
              {candidate.extraction_quality_score && (
                <div className="mt-4">
                  <div className="text-sm font-semibold text-gray-700">Qualité d&apos;extraction</div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${Math.round(candidate.extraction_quality_score * 100)}%` }}
                    />
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {Math.round(candidate.extraction_quality_score * 100)}%
                  </p>
                </div>
              )}
            </div>

            {/* Job Titles */}
            {extractedJobTitles.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6" role="region" aria-labelledby="job-titles-heading">
                <h3 className="text-xl font-bold text-gray-900 mb-3" id="job-titles-heading">
                  💼 Titres de Poste
                </h3>
                <div className="space-y-2" role="list">
                  {extractedJobTitles.map((title: string, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 bg-blue-50 rounded border border-blue-200"
                      role="listitem"
                    >
                      {title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Companies */}
            {extractedCompanies.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6" role="region" aria-labelledby="companies-heading">
                <h3 className="text-xl font-bold text-gray-900 mb-3" id="companies-heading">
                  🏢 Compagnies
                </h3>
                <div className="space-y-2" role="list">
                  {extractedCompanies.map((company: string, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 bg-purple-50 rounded border border-purple-200"
                      role="listitem"
                    >
                      {company}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education */}
            {extractedEducation.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6" role="region" aria-labelledby="education-heading">
                <h3 className="text-xl font-bold text-gray-900 mb-3" id="education-heading">
                  🎓 Éducation
                </h3>
                <div className="space-y-2" role="list">
                  {extractedEducation.map((edu: string, idx: number) => (
                    <div
                      key={idx}
                      className="p-2 bg-green-50 rounded border border-green-200"
                      role="listitem"
                    >
                      {edu}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Contact Info */}
            <div className="bg-white rounded-lg shadow-md p-6" role="region" aria-labelledby="contact-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-4" id="contact-heading">
                📋 Contact
              </h3>

              {extractedEmails.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-semibold text-gray-700 mb-1">Emails</div>
                  <div role="list">
                    {extractedEmails.map((email: string, idx: number) => (
                      <a
                        key={idx}
                        href={`mailto:${email}`}
                        aria-label={`Envoyer un email à ${email}`}
                        className="text-blue-600 hover:text-blue-700 block text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1"
                        role="listitem"
                      >
                        {email}
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {extractedPhones.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-gray-700 mb-1">Téléphones</div>
                  <div role="list">
                    {extractedPhones.map((phone: string, idx: number) => (
                      <a
                        key={idx}
                        href={`tel:${phone}`}
                        aria-label={`Appeler ${phone}`}
                        className="text-blue-600 hover:text-blue-700 block text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1"
                        role="listitem"
                      >
                        {phone}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="bg-white rounded-lg shadow-md p-6" role="region" aria-labelledby="actions-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-4" id="actions-heading">
                ⚡ Actions
              </h3>
              <button
                onClick={toggleFavorite}
                disabled={addingFavorite}
                aria-label={isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                className={`w-full px-4 py-2 rounded-lg transition-colors font-medium focus:outline-none focus:ring-2 ${
                  isFavorite
                    ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 focus:ring-yellow-400'
                    : 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500'
                }`}
              >
                {isFavorite ? '★ En favoris' : '☆ Ajouter aux favoris'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
