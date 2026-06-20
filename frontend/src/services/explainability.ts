/**
 * Explainability service — Phase 2 feature
 * Fetches human-readable match justifications from backend
 */

import apiClient from './api';
import { criteriaApi } from './criteria';
import { candidatesApi } from './candidates';

export interface ExplainabilityResponse {
  candidate_name: string;
  job_title: string;
  overall_score: number;
  interpretation: string; // "🟢 Strong Match" | "🟡 Moderate Match" | "🔴 Weak Match"
  matching_skills: string[];
  missing_skills: string[];
  experience_alignment: string;
  key_reason: string;
  recommendations: string[];
}

export interface ShortlistSummary {
  total_candidates_screened: number;
  strong_matches: number;
  moderate_matches: number;
  top_skills_in_pool: string[];
  recommendations: string[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function buildFallbackExplanation(candidateName: string, jobTitle: string): ExplainabilityResponse {
  return {
    candidate_name: candidateName,
    job_title: jobTitle,
    overall_score: 0,
    interpretation: '🟡 Moderate Match',
    matching_skills: [],
    missing_skills: [],
    experience_alignment: 'Explication générée en mode dégradé: vérifiez le service IA côté backend.',
    key_reason: 'Le backend d\'explication n\'a pas répondu; affichage d\'une version de secours.',
    recommendations: [
      'Vérifier les logs du backend IA.',
      'Confirmer la disponibilité des dépendances/modeles optionnels.',
    ],
  };
}

/**
 * Get human-readable explanation for a match
 */
export async function getMatchExplanation(
  candidateId: number,
  jobCriteriaId: number
): Promise<ExplainabilityResponse> {
  try {
    const response = await apiClient.post(
      `${API_URL}/api/matching/match-explanation`,
      {
        candidate_id: candidateId,
        job_criteria_id: jobCriteriaId,
      },
    );
    return response.data;
  } catch (error) {
    console.error('Failed to fetch match explanation:', error);
    try {
      const [candidateResponse, criteriaResponse] = await Promise.all([
        candidatesApi.getCandidate(candidateId),
        criteriaApi.getCriteriaById(jobCriteriaId),
      ]);
      return buildFallbackExplanation(
        candidateResponse.data.full_name || 'Candidat',
        criteriaResponse.data.title || 'Poste'
      );
    } catch {
      return buildFallbackExplanation('Candidat', 'Poste');
    }
  }
}

/**
 * Get shortlist summary for a job
 */
export async function getShortlistSummary(
  jobCriteriaId: number
): Promise<ShortlistSummary> {
  try {
    const response = await apiClient.post(
      `${API_URL}/api/matching/shortlist-summary`,
      {
        job_criteria_id: jobCriteriaId,
      },
    );
    return response.data;
  } catch (error) {
    console.error('Failed to fetch shortlist summary:', error);
    return {
      total_candidates_screened: 0,
      strong_matches: 0,
      moderate_matches: 0,
      top_skills_in_pool: [],
      recommendations: ['Version de secours: impossible de calculer le shortlist summary pour le moment.'],
    };
  }
}
