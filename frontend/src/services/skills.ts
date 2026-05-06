import apiClient from './api';

export interface Skill {
  id: number;
  name: string;
  category: 'tech' | 'soft' | 'language';
}

export const skillsApi = {
  // Get all skills
  getSkills: (category?: string, skip = 0, limit = 100) =>
    apiClient.get<Skill[]>('/skills/', { params: { category, skip, limit } }),

  // Get a specific skill
  getSkill: (id: number) =>
    apiClient.get<Skill>(`/skills/${id}`),

  // Create a skill
  createSkill: (data: { name: string; category: string }) =>
    apiClient.post<Skill>('/skills/', data),

  // Delete a skill
  deleteSkill: (id: number) =>
    apiClient.delete(`/skills/${id}`),
};
