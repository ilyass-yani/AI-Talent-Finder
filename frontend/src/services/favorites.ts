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
    apiClient.get<Favorite[]>('/favorites/', { params: { skip, limit } }),

  // Add candidate to favorites
  addFavorite: (candidateId: number) =>
    apiClient.post<Favorite>(`/favorites/${candidateId}`),

  // Remove candidate from favorites
  removeFavorite: (candidateId: number) =>
    apiClient.delete(`/favorites/${candidateId}`),
};
