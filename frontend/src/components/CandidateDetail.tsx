'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Mail, Phone, MapPin, Linkedin, Github, FileText, Award, Briefcase, Book } from 'lucide-react';
import SkillBadge from './SkillBadge';
import { candidatesApi } from '@/services/candidates';
import type { Candidate, Skill, Experience, Education } from '@/services/candidates';

interface CandidateDetailProps {
  candidateId: number;
}

export default function CandidateDetail({ candidateId }: CandidateDetailProps) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [educations, setEducations] = useState<Education[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Charge candidat
        const candidateRes = await candidatesApi.getCandidate(candidateId);
        setCandidate(candidateRes.data);

        // Charge skills
        const skillsRes = await candidatesApi.getCandidateSkills(candidateId);
        setSkills(skillsRes.data?.skills || []);

        // Charge experiences
        const experiencesRes = await candidatesApi.getCandidateExperiences(candidateId);
        setExperiences(experiencesRes.data?.experiences || []);

        // Charge educations
        const educationsRes = await candidatesApi.getCandidateEducations(candidateId);
        setEducations(educationsRes.data?.educations || []);
      } catch (err) {
        console.error('Error loading candidate details:', err);
        setError('Erreur lors du chargement du profil');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [candidateId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-500">Chargement du profil...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
          {error}
        </div>
        <Link href="/candidates" className="mt-4 text-indigo-600 hover:text-indigo-700">
          ← Retour aux candidats
        </Link>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="text-gray-500">Candidat non trouvé</div>
        <Link href="/candidates" className="mt-4 text-indigo-600 hover:text-indigo-700">
          ← Retour aux candidats
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Link href="/candidates" className="text-indigo-600 hover:text-indigo-700 mb-4 inline-block">
            ← Retour aux candidats
          </Link>
        </div>

        {/* Profile Card */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                {candidate.full_name || 'Candidat'}
              </h1>
              <p className="text-gray-600">ID: {candidate.id}</p>
            </div>
            {candidate.cv_path && (
              <a
                href={`/api/candidates/${candidate.id}/cv`}
                download
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
              >
                <FileText className="w-5 h-5" />
                Télécharger CV
              </a>
            )}
          </div>

          {/* Contact Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 pb-6 border-b">
            {candidate.email && (
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <a href={`mailto:${candidate.email}`} className="text-indigo-600 hover:underline">
                    {candidate.email}
                  </a>
                </div>
              </div>
            )}
            {candidate.phone && (
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-600">Téléphone</p>
                  <a href={`tel:${candidate.phone}`} className="text-gray-900">
                    {candidate.phone}
                  </a>
                </div>
              </div>
            )}
            {candidate.linkedin_url && (
              <div className="flex items-center gap-3">
                <Linkedin className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-600">LinkedIn</p>
                  <a
                    href={candidate.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:underline truncate"
                  >
                    Profil
                  </a>
                </div>
              </div>
            )}
            {candidate.github_url && (
              <div className="flex items-center gap-3">
                <Github className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-600">GitHub</p>
                  <a
                    href={candidate.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:underline truncate"
                  >
                    Profil
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Date */}
          <p className="text-sm text-gray-500">
            Profil créé le {new Date(candidate.created_at).toLocaleDateString('fr-FR')}
          </p>
        </div>

        {/* Skills Section */}
        {skills.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Award className="w-6 h-6 text-indigo-600" />
              <h2 className="text-2xl font-bold text-gray-900">Compétences</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              {skills.map((skill) => (
                <div key={skill.id} className="flex flex-col items-start">
                  <SkillBadge name={skill.name} category={skill.category} />
                  <p className="text-xs text-gray-500 mt-1">
                    {skill.proficiency_level || 'Non spécifié'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Experiences Section */}
        {experiences.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Briefcase className="w-6 h-6 text-indigo-600" />
              <h2 className="text-2xl font-bold text-gray-900">Expériences Professionnelles</h2>
            </div>
            <div className="space-y-6">
              {experiences.map((exp) => (
                <div key={exp.id} className="border-l-4 border-indigo-600 pl-4 pb-4">
                  <h3 className="text-lg font-semibold text-gray-900">{exp.job_title}</h3>
                  <p className="text-indigo-600 font-medium">{exp.company}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    {exp.duration_months ? `${exp.duration_months} mois` : 'Durée non spécifiée'}
                  </p>
                  {exp.description && (
                    <p className="text-gray-700 mt-2">{exp.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Education Section */}
        {educations.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <div className="flex items-center gap-3 mb-6">
              <Book className="w-6 h-6 text-indigo-600" />
              <h2 className="text-2xl font-bold text-gray-900">Formation</h2>
            </div>
            <div className="space-y-6">
              {educations.map((edu) => (
                <div key={edu.id} className="border-l-4 border-green-600 pl-4 pb-4">
                  <h3 className="text-lg font-semibold text-gray-900">{edu.degree}</h3>
                  <p className="text-green-600 font-medium">{edu.institution}</p>
                  {edu.field_of_study && (
                    <p className="text-sm text-gray-600 mt-1">
                      Domaine: {edu.field_of_study}
                    </p>
                  )}
                  {edu.graduation_year && (
                    <p className="text-sm text-gray-600">
                      Graduation: {edu.graduation_year}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Raw CV Text */}
        {candidate.raw_text && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Texte du CV</h2>
            <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
                {candidate.raw_text}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
