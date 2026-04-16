import apiClient from './api';

export interface CriteriaSkillInput {
  name: string;
  weight: number;
}

export interface Criteria {
  id: number;
  recruiter_id: number;
  title: string;
  description?: string | null;
  created_at: string;
  required_skills: CriteriaSkillInput[];
}

export interface CriteriaCreatePayload {
  title: string;
  description?: string;
  required_skills: CriteriaSkillInput[];
}

export interface CriteriaUpdatePayload {
  title?: string;
  description?: string;
  required_skills?: CriteriaSkillInput[];
}

export const criteriaApi = {
  getCriteria: () => apiClient.get<Criteria[]>('/api/criteria'),

  getCriteriaById: (id: number) => apiClient.get<Criteria>(`/api/criteria/${id}`),

  createCriteria: (payload: CriteriaCreatePayload) =>
    apiClient.post<Criteria>('/api/criteria', payload),

  updateCriteria: (id: number, payload: CriteriaUpdatePayload) =>
    apiClient.put<Criteria>(`/api/criteria/${id}`, payload),

  deleteCriteria: (id: number) => apiClient.delete(`/api/criteria/${id}`),
};
