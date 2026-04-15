'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi } from '@/services/candidates';
import type { Skill, Experience, Education } from '@/services/candidates';

export default function CandidateProfile() {
  const router = useRouter();
  const [candidateId, setCandidateId] = useState<number | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [educations, setEducations] = useState<Education[]>([]);
  const [candidateInfo, setCandidateInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProfileData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get candidate ID from localStorage or auth context
        const storedCandidateId = localStorage.getItem('candidateId');
        
        if (!storedCandidateId) {
          // Fallback: Try to get from API /auth/me
          try {
            const userResponse = await candidatesApi.getCandidate(1);
            console.log('User data:', userResponse);
          } catch (authError) {
            console.warn('Could not fetch user data');
          }
          
          // Default to candidate 1 for testing
          setCandidateId(1);
        } else {
          setCandidateId(parseInt(storedCandidateId));
        }
      } catch (err) {
        console.error('Error in useEffect setup:', err);
      }
    };

    loadProfileData();
  }, []);

  // Load complete profile once we have candidate ID
  useEffect(() => {
    const fetchProfileData = async () => {
      if (!candidateId) return;
      
      try {
        setLoading(true);
        setError(null);

        // Fetch complete profile with all extracted data
        const response = await candidatesApi.getCandidateProfile(candidateId);
        
        if (response.data) {
          setCandidateInfo({
            filename: response.data.filename,
            full_name: response.data.full_name,
            headline: response.data.headline,
            summary: response.data.summary,
            contact: response.data.contact,
            sections_detected: response.data.sections_detected,
            skills_count: response.data.skills_count,
            experiences_count: response.data.experiences_count,
            educations_count: response.data.educations_count,
          });
          
          // Set skills
          if (response.data.skills && Array.isArray(response.data.skills)) {
            const formattedSkills = response.data.skills.map((skill: any) => ({
              id: skill.id,
              name: skill.name,
              proficiency_level: skill.proficiency_level || 'intermediate',
              category: skill.category,
              source: skill.source
            }));
            setSkills(formattedSkills);
          }
          
          // Set experiences
          if (response.data.experiences && Array.isArray(response.data.experiences)) {
            setExperiences(response.data.experiences);
          }
          
          // Set educations
          if (response.data.educations && Array.isArray(response.data.educations)) {
            setEducations(response.data.educations);
          }
        }
      } catch (err: any) {
        console.error('Error fetching profile:', err);
        setError(err.response?.data?.detail || 'Erreur lors du chargement du profil');
        // Don't fail completely - show empty data
        setSkills([]);
        setExperiences([]);
        setEducations([]);
      } finally {
        setLoading(false);
      }
    };

    fetchProfileData();
  }, [candidateId]);

  const getSkillColor = (level: string) => {
    switch (level) {
      case 'expert':
        return 'bg-red-50 border-red-200 text-red-700';
      case 'advanced':
        return 'bg-blue-50 border-blue-200 text-blue-700';
      case 'intermediate':
        return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      case 'beginner':
        return 'bg-green-50 border-green-200 text-green-700';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const formatDuration = (months: number) => {
    if (months < 12) return `${months} mois`;
    const years = Math.floor(months / 12);
    const remainingMonths = months % 12;
    if (remainingMonths === 0) return `${years} ans`;
    return `${years} ans ${remainingMonths} mois`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/candidate/dashboard" className="text-gray-600 hover:text-gray-900">
            ← Retour
          </Link>
          <h1 className="text-2xl font-bold text-blue-600">🧑 Mon Profil</h1>
          <div></div>
        </div>
      </nav>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Profile Card */}
        <div className="bg-white rounded-lg shadow-md p-8 mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Ton Profil Structuré</h2>
          <p className="text-gray-600 mb-6">
            Voici comment les recruteurs verront ton profil
          </p>

          {candidateInfo?.headline && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm uppercase tracking-wide text-blue-700 font-semibold mb-1">Titre détecté</p>
              <p className="text-lg font-bold text-blue-900">{candidateInfo.headline}</p>
              {candidateInfo.summary && (
                <p className="text-sm text-blue-800 mt-2 leading-relaxed">{candidateInfo.summary}</p>
              )}
              {Array.isArray(candidateInfo.sections_detected) && candidateInfo.sections_detected.length > 0 && (
                <p className="text-xs text-blue-700 mt-3">
                  Sections détectées: {candidateInfo.sections_detected.join(', ')}
                </p>
              )}
            </div>
          )}

          {candidateInfo?.contact && (
            <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700">
              <p className="font-semibold text-gray-900 mb-1">Contact reconnu</p>
              <p>Email: {candidateInfo.contact.email || 'Non détecté'}</p>
              <p>Téléphone: {candidateInfo.contact.phone || 'Non détecté'}</p>
            </div>
          )}

          {loading && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-center">
              <p className="text-blue-700">Chargement de ton profil...</p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
              <p className="text-red-700">⚠️ {error}</p>
            </div>
          )}

          {!loading && (
            <>
              {/* Skills */}
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">
                  🎯 Compétences Détectées ({skills.length})
                </h3>
                
                {skills.length === 0 ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-yellow-700">
                      Aucune compétence détectée. Upload un CV pour que l'IA les extraise automatiquement!
                    </p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {skills.map((skill) => (
                      <div 
                        key={skill.id} 
                        className={`p-4 rounded-lg border ${getSkillColor(skill.proficiency_level)}`}
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <span className="font-semibold text-gray-900">{skill.name}</span>
                            <p className="text-xs text-gray-500 mt-1">
                              {skill.category} • {skill.source}
                            </p>
                          </div>
                          <span className="text-sm bg-opacity-20 px-3 py-1 rounded-full font-semibold">
                            {skill.proficiency_level}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Experiences */}
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">💼 Expériences ({experiences.length})</h3>
                
                {experiences.length === 0 ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-yellow-700">
                      Aucune expérience détectée. Upload un CV avec tes expériences professionnelles!
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {experiences.map((exp) => (
                      <div key={exp.id} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h4 className="font-bold text-gray-900 text-lg">{exp.job_title || exp.title}</h4>
                            <p className="text-gray-600 font-semibold">{exp.company}</p>
                            <p className="text-sm text-gray-500 mt-2">
                              📅 {formatDuration(exp.duration_months)}
                            </p>
                            {exp.description && (
                              <p className="text-gray-600 text-sm mt-2">{exp.description}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Educations */}
              <div className="mb-8">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">🎓 Formations ({educations.length})</h3>
                
                {educations.length === 0 ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-yellow-700">
                      Aucune formation détectée. Upload un CV avec tes études et certifications!
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {educations.map((edu) => (
                      <div key={edu.id} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h4 className="font-bold text-gray-900 text-lg">{edu.degree}</h4>
                            <p className="text-gray-600 font-semibold">{edu.institution}</p>
                            {(edu.field_of_study || edu.field) && (
                              <p className="text-sm text-gray-500 mt-1">Spécialité: {edu.field_of_study || edu.field}</p>
                            )}
                            {(edu.graduation_year || edu.year) && (
                              <p className="text-sm text-gray-500">🎓 {edu.graduation_year || edu.year}</p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Visibility Badge */}
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center">
                  <span className="text-3xl mr-3">✓</span>
                  <div>
                    <p className="font-bold text-green-700">Ton profil est visible!</p>
                    <p className="text-sm text-green-600">
                      Les recruteurs peuvent maintenant te découvrir
                    </p>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Info */}
        <div className="bg-blue-50 border-l-4 border-blue-500 rounded p-6">
          <h3 className="font-bold text-gray-900 mb-2">📊 Visibilité et Opportunités</h3>
          <p className="text-gray-700 text-sm">
            Plus tu complètes ton profil, plus tu seras visible auprès des recruteurs. 
            Les recruteurs utiliseront la recherche et l'IA pour te trouver et t'envoyer des propositions adaptées!
          </p>
        </div>
      </div>
    </div>
  );
}
