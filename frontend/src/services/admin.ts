import apiClient from './api';

export type Role = 'admin' | 'recruiter' | 'candidate';

export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface GlobalStats {
  total_users: number;
  users_by_role: Record<string, number>;
  total_candidates: number;
  total_jobs: number;
  total_match_results: number;
  total_feedback: number;
  total_skills: number;
  average_match_score: number | null;
  recent_signups: number;
}

export interface ActivityLog {
  id: number;
  timestamp: string;
  level: string;
  action: string;
  user_id: number | null;
  detail: string | null;
}

export interface SystemHealth {
  status: string;
  database_connected: boolean;
  capabilities: Record<string, unknown>;
  counts: Record<string, number>;
  log_levels: Record<string, number>;
}

export interface PipelineConfig {
  skill_weight: number;
  semantic_weight: number;
  experience_weight: number;
  education_weight: number;
  perfect_match_bonus: number;
  accept_threshold: number;
  review_threshold: number;
  defaults: Record<string, number>;
}

export const adminApi = {
  // Gérer les utilisateurs (CRUD)
  listUsers: (params?: { role?: Role; search?: string }) =>
    apiClient.get<AdminUser[]>('/admin/users', { params }),
  createUser: (data: { email: string; password: string; full_name: string; role: Role }) =>
    apiClient.post<AdminUser>('/admin/users', data),
  updateUser: (id: number, data: { full_name?: string; role?: Role; password?: string }) =>
    apiClient.patch<AdminUser>(`/admin/users/${id}`, data),
  deleteUser: (id: number) => apiClient.delete(`/admin/users/${id}`),

  // Consulter les statistiques globales
  getStats: () => apiClient.get<GlobalStats>('/admin/stats'),

  // Superviser les logs et performances
  getLogs: (params?: { level?: string; action?: string; limit?: number }) =>
    apiClient.get<ActivityLog[]>('/admin/logs', { params }),
  getHealth: () => apiClient.get<SystemHealth>('/admin/health'),

  // Configurer les paramètres du pipeline IA
  getPipelineConfig: () => apiClient.get<PipelineConfig>('/admin/pipeline-config'),
  updatePipelineConfig: (data: Partial<Omit<PipelineConfig, 'defaults'>>) =>
    apiClient.put<PipelineConfig>('/admin/pipeline-config', data),
  resetPipelineConfig: () => apiClient.post<PipelineConfig>('/admin/pipeline-config/reset'),
};
