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

export interface PredictSkillBreakdown {
  skill: string;
  present: boolean;
  weight: number;
  matched: boolean;
}

export interface PredictCandidateResult {
  candidate_id: number;
  full_name: string;
  email: string;
  predicted_score: number;
  coverage: number;
  matched_skills: string[];
  missing_skills: string[];
  skill_breakdown: PredictSkillBreakdown[];
  summary: string;
}

export interface PredictCriteriaResult {
  criteria_id: number;
  model: string;
  top_k: number;
  results: PredictCandidateResult[];
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
    apiClient.get<MatchResult[]>('/matching/results', {
      params: { candidate_id: candidateId, criteria_id: criteriaId, skip, limit },
    }),

  // Get match results for a criteria
  getCriteriaResults: (criteriaId: number, skip = 0, limit = 100) =>
    apiClient.get<MatchResult[]>(`/matching/${criteriaId}/results`, {
      params: { skip, limit },
    }),

  // Get a specific match result
  getMatchResult: (id: number) =>
    apiClient.get<MatchResult>(`/matching/results/${id}`),

  // Calculate match between candidate and criteria
  calculateMatch: (candidateId: number, criteriaId: number) =>
    apiClient.post(`/matching/calculate/${candidateId}/${criteriaId}`),

  // Delete a match result
  deleteMatchResult: (id: number) =>
    apiClient.delete(`/matching/results/${id}`),

  // Mode 1: Search candidates matching criteria
  searchCandidates: (criteriaId: number) =>
    apiClient.post<CandidateMatch[]>(`/matching/search/${criteriaId}`),

  // Étape 7 canonical flow: launch matching on every candidate
  runCriteriaMatching: (criteriaId: number) =>
    apiClient.post<CriteriaMatchResult[]>(`/matching/${criteriaId}/results`),

  // Étape 7 canonical flow: retrieve the ranked results for a criteria
  getCriteriaMatchingResults: (criteriaId: number) =>
    apiClient.get<CriteriaMatchResult[]>(`/matching/${criteriaId}/results`),

  // Baseline model prediction with explainability
  predictCriteria: (criteriaId: number, topK = 20) =>
    apiClient.post<PredictCriteriaResult>(`/matching/${criteriaId}/predict`, null, {
      params: { top_k: topK },
    }),

  // Mode 2: Generate ideal profile and match candidates
  generateAndMatch: (jobTitle: string, description: string) =>
    apiClient.post<{
      ideal_profile: IdealProfile;
      matches: CandidateMatch[];
    }>('/matching/generate-and-match', {
      job_title: jobTitle,
      description: description,
    }),
};
