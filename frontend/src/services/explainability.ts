/**
 * Explainability service — Phase 2 feature
 * Fetches human-readable match justifications from backend
 */

import axios from 'axios';

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

/**
 * Get human-readable explanation for a match
 */
export async function getMatchExplanation(
  candidateId: number,
  jobCriteriaId: number
): Promise<ExplainabilityResponse> {
  try {
    const response = await axios.post(
      `${API_URL}/api/matching/match-explanation`,
      {
        candidate_id: candidateId,
        job_criteria_id: jobCriteriaId,
      },
      {
        withCredentials: true,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to fetch match explanation:', error);
    throw error;
  }
}

/**
 * Get shortlist summary for a job
 */
export async function getShortlistSummary(
  jobCriteriaId: number
): Promise<ShortlistSummary> {
  try {
    const response = await axios.post(
      `${API_URL}/api/matching/shortlist-summary`,
      {
        job_criteria_id: jobCriteriaId,
      },
      {
        withCredentials: true,
      }
    );
    return response.data;
  } catch (error) {
    console.error('Failed to fetch shortlist summary:', error);
    throw error;
  }
}
