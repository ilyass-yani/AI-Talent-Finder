import apiClient from './api';

export interface MatchResult {
  id: number;
  criteria_id: number;
  candidate_id: number;
  score: number;
  explanation?: string;
  created_at: string;
}

export const matchingApi = {
  // Get all match results
  getMatchResults: (candidateId?: number, criteriaId?: number, skip = 0, limit = 100) =>
    apiClient.get<MatchResult[]>('/api/matching/results', {
      params: { candidate_id: candidateId, criteria_id: criteriaId, skip, limit },
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
};
