'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi, Candidate } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';
import { SkeletonProfile } from '@/components/SkeletonLoader';

export default function CandidateProfile() {
  const router = useRouter();
  const didLoadRef = useRef(false);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Prevent duplicate calls in React StrictMode during development.
    if (didLoadRef.current) return;
    didLoadRef.current = true;
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      console.log('📡 Fetching profile...');
      const response = await candidatesApi.getMyProfile();
      console.log('✅ Profile fetched:', response.data);
      setCandidate(response.data);
      setError(null);
    } catch (err: unknown) {
      if (err?.response?.status === 404) {
        router.replace('/candidate/upload');
        return;
      }
      console.error('❌ Profile fetch error:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-6xl mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-blue-600">🧑 Mon Profil</h1>
          </div>
        </nav>
        <div className="max-w-4xl mx-auto px-4 py-8">
          <SkeletonProfile />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full">
          <div
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
            className="bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <p className="text-red-700 font-semibold">❌ Erreur</p>
            <p className="text-red-600 text-sm mt-2">{error}</p>
            <Link
              href="/candidate/upload"
              className="mt-4 inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              ← Uploader un CV
            </Link>
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

  // Parse les champs JSON si nécessaire - avec gestion d'erreur
  const safeJsonParse = (
    jsonString: string | null,
    fallback: unknown[] = [],
    useFallbackIfEmpty = false
  ) => {
    try {
      if (!jsonString) {
        console.log('⚠️  Empty string, using fallback');
        return fallback;
      }
      const parsed = JSON.parse(jsonString);
      console.log('✅ Parsed:', jsonString.substring(0, 50), '...');
      if (!Array.isArray(parsed)) {
        return fallback;
      }
      if (useFallbackIfEmpty && parsed.length === 0 && fallback.length > 0) {
        return fallback;
      }
      return parsed;
    } catch (e) {
      console.error('❌ JSON Parse Error:', e, 'String:', jsonString);
      return fallback;
    }
  };

  const safeJsonObjectParse = (jsonString: string | null, fallback: Record<string, unknown> = {}) => {
    try {
      if (!jsonString) return fallback;
      const parsed = JSON.parse(jsonString);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        return fallback;
      }
      return parsed;
    } catch (e) {
      console.error('❌ JSON Object Parse Error:', e, 'String:', jsonString);
      return fallback;
    }
  };

  const toStringArray = (value: unknown): string[] => {
    if (!Array.isArray(value)) return [];
    return value
      .map((item) => String(item || '').trim())
      .filter((item) => item.length > 0);
  };

  type ExtractedExperience = {
    title?: string;
    company?: string;
    period?: string | null;
    responsibilities?: string[];
  };

  const toExperienceArray = (value: unknown): ExtractedExperience[] => {
    if (!Array.isArray(value)) return [];
    return value
      .map((item) => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
        const data = item as Record<string, unknown>;
        const title = typeof data.title === 'string' ? data.title.trim() : '';
        const company = typeof data.company === 'string' ? data.company.trim() : '';
        const period = typeof data.period === 'string' ? data.period.trim() : null;
        const responsibilities = toStringArray(data.responsibilities).filter((line) => line.length > 0);
        if (!title && !company && responsibilities.length === 0) return null;
        return { title, company, period, responsibilities };
      })
      .filter((item): item is ExtractedExperience => item !== null);
  };

  const jobTitles = safeJsonParse(candidate.extracted_job_titles, []);
  const companies = safeJsonParse(candidate.extracted_companies, []);
  const education = safeJsonParse(candidate.extracted_education, []);
  const emails = safeJsonParse(candidate.extracted_emails, [candidate.email].filter(Boolean), true);
  const phones = safeJsonParse(candidate.extracted_phones, [candidate.phone].filter(Boolean), true);
  const nerData = safeJsonObjectParse(candidate.ner_extraction_data);

  const languages = toStringArray(nerData.languages);
  const softSkills = toStringArray(nerData.soft_skills);
  const interests = toStringArray(nerData.interests);
  const locations = toStringArray(nerData.locations);
  const linkedins = toStringArray(nerData.linkedin_urls);
  const githubUrls = toStringArray(nerData.github_urls);
  const portfolioUrls = toStringArray(nerData.portfolio_urls);
  const certifications = toStringArray(nerData.certifications);
  const projects = toStringArray(nerData.projects);
  const profileSummary = typeof nerData.profile_summary === 'string' ? nerData.profile_summary.trim() : '';
  const linkedinUrl = candidate.linkedin_url || linkedins[0] || null;
  const experiences = toExperienceArray(nerData.experiences);

  console.log('🎯 Parsed data:', {
    jobTitles,
    companies,
    education,
    emails,
    phones,
    languages,
    softSkills,
    interests,
    locations,
    linkedins,
    githubUrls,
    portfolioUrls,
    certifications,
    projects,
    profileSummary,
    experiences,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/candidate/dashboard" className="text-gray-600 hover:text-gray-900">
            ← Retour
          </Link>
          <h1 className="text-2xl font-bold text-blue-600">🧑 Mon Profil</h1>
          <div className="flex gap-2">
            <button
              onClick={loadProfile}
              aria-label="Rafraîchir le profil"
              className="bg-blue-50 hover:bg-blue-100 text-blue-600 px-4 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              🔄 Rafraîchir
            </button>
            <Link
              href="/candidate/profile/edit"
              aria-label="Éditer le profil"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 inline-block"
            >
              ✏️ Éditer
            </Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Profile Header Card */}
        <div className="bg-white rounded-lg shadow-md p-8 mb-8">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                {candidate.extracted_name || candidate.full_name}
              </h2>
              <p className="text-gray-600">
                {candidate.is_fully_extracted ? '✅ Profil extrait du CV' : '⚠️ Données partielles'}
              </p>
            </div>
          </div>

          {/* Quality Score */}
          {candidate.extraction_quality_score && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-900">Qualité de l&apos;extraction:</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500"
                      style={{ width: `${candidate.extraction_quality_score}%` }}
                    />
                  </div>
                  <span className="font-bold text-green-700">
                    {candidate.extraction_quality_score.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Contact Info */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div role="region" aria-labelledby="emails-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="emails-heading">
                📧 Emails
              </h3>
              <div className="space-y-2" role="list">
                {emails.filter((e: string) => e).map((email: string, idx: number) => (
                  <p key={idx} className="text-gray-600" role="listitem">
                    {email}
                  </p>
                ))}
                {emails.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucun email
                  </p>
                )}
              </div>
            </div>
            <div role="region" aria-labelledby="phones-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="phones-heading">
                📱 Téléphones
              </h3>
              <div className="space-y-2" role="list">
                {phones.filter((p: string) => p).map((phone: string, idx: number) => (
                  <p key={idx} className="text-gray-600" role="listitem">
                    {phone}
                  </p>
                ))}
                {phones.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucun téléphone
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Links & Location */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div role="region" aria-labelledby="links-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="links-heading">
                🔗 Liens
              </h3>
              <div className="space-y-2" role="list">
                {linkedinUrl && (
                  <a
                    href={linkedinUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-blue-600 hover:text-blue-700 break-all"
                    role="listitem"
                  >
                    LinkedIn: {linkedinUrl}
                  </a>
                )}
                {githubUrls.map((url: string, idx: number) => (
                  <a
                    key={`github-${idx}`}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-slate-700 hover:text-slate-900 break-all"
                    role="listitem"
                  >
                    GitHub: {url}
                  </a>
                ))}
                {portfolioUrls.map((url: string, idx: number) => (
                  <a
                    key={`portfolio-${idx}`}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-emerald-700 hover:text-emerald-900 break-all"
                    role="listitem"
                  >
                    Portfolio: {url}
                  </a>
                ))}
                {!linkedinUrl && githubUrls.length === 0 && portfolioUrls.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucun lien détecté
                  </p>
                )}
              </div>
            </div>
            <div role="region" aria-labelledby="locations-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="locations-heading">
                📍 Localisation
              </h3>
              <div className="space-y-2" role="list">
                {locations.map((location: string, idx: number) => (
                  <p key={idx} className="text-gray-600" role="listitem">
                    {location}
                  </p>
                ))}
                {locations.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Localisation non détectée
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Profile Summary */}
          {profileSummary && (
            <div className="mb-8" role="region" aria-labelledby="summary-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="summary-heading">
                📝 Profil
              </h3>
              <p className="text-gray-700 p-4 bg-indigo-50 rounded leading-relaxed">{profileSummary}</p>
            </div>
          )}

          {/* Jobs & Companies */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div role="region" aria-labelledby="jobs-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="jobs-heading">
                💼 Derniers Postes
              </h3>
              <div className="space-y-2" role="list">
                {jobTitles.map((title: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-blue-50 rounded" role="listitem">
                    {title}
                  </p>
                ))}
                {jobTitles.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucun poste trouvé
                  </p>
                )}
              </div>
            </div>
            <div role="region" aria-labelledby="companies-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="companies-heading">
                🏢 Entreprises
              </h3>
              <div className="space-y-2" role="list">
                {companies.map((company: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-purple-50 rounded" role="listitem">
                    {company}
                  </p>
                ))}
                {companies.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucune entreprise trouvée
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Professional Experiences */}
          <div className="mb-8" role="region" aria-labelledby="experiences-heading">
            <h3 className="text-lg font-bold text-gray-900 mb-3" id="experiences-heading">
              🧭 Expériences Professionnelles
            </h3>
            <div className="space-y-4" role="list">
              {experiences.map((experience, idx) => (
                <div key={idx} className="p-4 rounded border border-slate-200 bg-slate-50" role="listitem">
                  <div className="flex flex-wrap justify-between items-start gap-2 mb-2">
                    <p className="font-semibold text-slate-900">{experience.title || 'Poste non détecté'}</p>
                    {experience.period && (
                      <span className="text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded px-2 py-1">
                        {experience.period}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-700 mb-2">{experience.company || 'Entreprise non détectée'}</p>
                  {experience.responsibilities && experience.responsibilities.length > 0 && (
                    <ul className="space-y-1 text-sm text-slate-700 list-disc pl-5">
                      {experience.responsibilities.map((item, itemIdx) => (
                        <li key={itemIdx}>{item}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
              {experiences.length === 0 && (
                <p className="text-gray-400" role="listitem">
                  Aucune expérience détaillée trouvée
                </p>
              )}
            </div>
          </div>

          {/* Education */}
          <div className="mb-8" role="region" aria-labelledby="education-heading">
            <h3 className="text-lg font-bold text-gray-900 mb-3" id="education-heading">
              🎓 Formation
            </h3>
            <div className="space-y-2" role="list">
              {education.map((edu: string, idx: number) => (
                <p key={idx} className="text-gray-600 p-2 bg-orange-50 rounded" role="listitem">
                  {edu}
                </p>
              ))}
              {education.length === 0 && (
                <p className="text-gray-400" role="listitem">
                  Aucune formation trouvée
                </p>
              )}
            </div>
          </div>

          {/* Certifications & Projects */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div role="region" aria-labelledby="certifications-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="certifications-heading">
                📜 Certifications
              </h3>
              <div className="space-y-2" role="list">
                {certifications.map((certification: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-amber-50 rounded" role="listitem">
                    {certification}
                  </p>
                ))}
                {certifications.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucune certification trouvée
                  </p>
                )}
              </div>
            </div>
            <div role="region" aria-labelledby="projects-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="projects-heading">
                🚀 Projets
              </h3>
              <div className="space-y-2" role="list">
                {projects.map((project: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-lime-50 rounded" role="listitem">
                    {project}
                  </p>
                ))}
                {projects.length === 0 && (
                  <p className="text-gray-400" role="listitem">
                    Aucun projet trouvé
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Languages, Skills, Interests */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <div role="region" aria-labelledby="languages-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="languages-heading">
                🌍 Langues
              </h3>
              <div className="space-y-2" role="list">
                {languages.map((language: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-cyan-50 rounded" role="listitem">
                    {language}
                  </p>
                ))}
                {languages.length === 0 && <p className="text-gray-400">Aucune langue trouvée</p>}
              </div>
            </div>
            <div role="region" aria-labelledby="soft-skills-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="soft-skills-heading">
                🤝 Compétences
              </h3>
              <div className="space-y-2" role="list">
                {softSkills.map((skill: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-emerald-50 rounded" role="listitem">
                    {skill}
                  </p>
                ))}
                {softSkills.length === 0 && <p className="text-gray-400">Aucune compétence trouvée</p>}
              </div>
            </div>
            <div role="region" aria-labelledby="interests-heading">
              <h3 className="text-lg font-bold text-gray-900 mb-3" id="interests-heading">
                🎯 Centres d’intérêt
              </h3>
              <div className="space-y-2" role="list">
                {interests.map((interest: string, idx: number) => (
                  <p key={idx} className="text-gray-600 p-2 bg-rose-50 rounded" role="listitem">
                    {interest}
                  </p>
                ))}
                {interests.length === 0 && <p className="text-gray-400">Aucun centre d’intérêt trouvé</p>}
              </div>
            </div>
          </div>

          {/* Visibility Badge */}
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <span className="text-3xl mr-3">✓</span>
              <div>
                <p className="font-bold text-green-700">Ton profil est visible!</p>
                <p className="text-sm text-green-600">
                  {candidate.is_fully_extracted
                    ? 'Les recruteurs peuvent te découvrir avec toutes tes données'
                    : 'Complète ton profil pour être plus visible'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
