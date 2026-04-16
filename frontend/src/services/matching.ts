import apiClient from './api';

export interface MatchResult {
  id: number;
  criteria_id: number;
  candidate_id: number;
  score: number;
  explanation?: string;
  created_at: string;
}

export interface SkillBreakdown {
  skill: string;
  weight: number;
  present: boolean;
  score: number;
  contribution: number;
}

export interface CriteriaMatchResult {
  match_result_id: number;
  criteria_id: number;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  score: number;
  coverage: number;
  matched_skills: string[];
  missing_skills: string[];
  skill_breakdown: SkillBreakdown[];
  summary: string;
  created_at: string;
}

export interface CandidateMatch {
  candidate_id: number;
  full_name: string;
  email: string;
  match_score: number;
  explanation?: string;
}

export interface IdealProfile {
  ideal_skills: Array<{ name: string; weight: number; level: string }>;
  ideal_experience_years?: number;
  ideal_education?: string;
  industries?: string[];
}

export const matchingApi = {
  // Get all match results
  getMatchResults: (candidateId?: number, criteriaId?: number, skip = 0, limit = 100) =>
    apiClient.get<MatchResult[]>('/api/matching/results', {
      params: { candidate_id: candidateId, criteria_id: criteriaId, skip, limit },
    }),

  // Get match results for a criteria
  getCriteriaResults: (criteriaId: number, skip = 0, limit = 100) =>
    apiClient.get<MatchResult[]>(`/matching/${criteriaId}/results`, {
      params: { skip, limit },
    }),

  // Get a specific match result
  getMatchResult: (id: number) =>
    apiClient.get<MatchResult>(`/api/matching/results/${id}`),

  // Calculate match between candidate and criteria
  calculateMatch: (candidateId: number, criteriaId: number) =>
    apiClient.post(`/api/matching/calculate/${candidateId}/${criteriaId}`),

  // Delete a match result
  deleteMatchResult: (id: number) =>
    apiClient.delete(`/api/matching/results/${id}`),

  // Mode 1: Search candidates matching criteria
  searchCandidates: (criteriaId: number) =>
    apiClient.post<CandidateMatch[]>(`/api/matching/search/${criteriaId}`),

  // Étape 7 canonical flow: launch matching on every candidate
  runCriteriaMatching: (criteriaId: number) =>
    apiClient.post<CriteriaMatchResult[]>(`/api/matching/${criteriaId}`),

  // Étape 7 canonical flow: retrieve the ranked results for a criteria
  getCriteriaMatchingResults: (criteriaId: number) =>
    apiClient.get<CriteriaMatchResult[]>(`/api/matching/${criteriaId}/results`),

  // Mode 2: Generate ideal profile and match candidates
  generateAndMatch: (jobTitle: string, description: string) =>
    apiClient.post<{
      ideal_profile: IdealProfile;
      matches: CandidateMatch[];
    }>('/api/matching/generate-and-match', {
      job_title: jobTitle,
      description: description,
    }),
};
