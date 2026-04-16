import apiClient from './api';
import { Candidate } from './candidates';

export interface Favorite {
  id: number;
  recruiter_id: number;
  candidate_id: number;
  added_at: string;
  candidate?: Candidate;
}

export const favoritesApi = {
  // Get all favorites
  getFavorites: (skip = 0, limit = 100) =>
    apiClient.get<Favorite[]>('/api/favorites/', { params: { skip, limit } }),

  // Add candidate to favorites
  addFavorite: (candidateId: number) =>
    apiClient.post<Favorite>(`/api/favorites/${candidateId}`),

  // Remove candidate from favorites
  removeFavorite: (candidateId: number) =>
    apiClient.delete(`/api/favorites/${candidateId}`),
};
