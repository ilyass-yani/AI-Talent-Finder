import apiClient from './api';

export type ModerationStatus = 'pending' | 'approved' | 'rejected';

export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface PaginatedUsers {
  total: number;
  items: AdminUser[];
}

export interface AdminJob {
  id: number;
  title: string;
  description: string | null;
  moderation_status: ModerationStatus;
  recruiter_id: number;
  recruiter_email: string | null;
  created_at: string;
}

export interface PaginatedJobs {
  total: number;
  items: AdminJob[];
}

export interface AdminStats {
  total_candidates: number;
  total_recruiters: number;
  total_active_jobs: number;
  total_matchings: number;
}

export interface ActivityLog {
  id: number;
  timestamp: string;
  level: string;
  action: string;
  detail: string | null;
}

export interface SystemHealth {
  status: string;
  database_connected: boolean;
  capabilities: Record<string, unknown>;
  counts: Record<string, number>;
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
  // Users
  getUsers: (params?: { skip?: number; limit?: number; role?: string; is_active?: boolean }) =>
    apiClient.get<PaginatedUsers>('/admin/users', { params }),

  setUserStatus: (userId: number, is_active: boolean) =>
    apiClient.patch<AdminUser>(`/admin/users/${userId}/status`, { is_active }),

  deleteUser: (userId: number) =>
    apiClient.delete(`/admin/users/${userId}`),

  // Jobs
  getJobs: (params?: { skip?: number; limit?: number; moderation_status?: string }) =>
    apiClient.get<PaginatedJobs>('/admin/jobs', { params }),

  moderateJob: (jobId: number, moderation_status: ModerationStatus) =>
    apiClient.patch<AdminJob>(`/admin/jobs/${jobId}/moderate`, { moderation_status }),

  deleteJob: (jobId: number) =>
    apiClient.delete(`/admin/jobs/${jobId}`),

  // Stats
  getStats: () =>
    apiClient.get<AdminStats>('/admin/stats'),

  // Monitoring
  getHealth: () =>
    apiClient.get<SystemHealth>('/admin/health'),

  getLogs: (params?: { level?: string; limit?: number }) =>
    apiClient.get<ActivityLog[]>('/admin/logs', { params }),

  // Pipeline
  getPipelineConfig: () =>
    apiClient.get<PipelineConfig>('/admin/pipeline/config'),

  updatePipelineConfig: (config: Partial<Omit<PipelineConfig, 'defaults'>>) =>
    apiClient.patch<PipelineConfig>('/admin/pipeline/config', config),

  resetPipelineConfig: () =>
    apiClient.post<PipelineConfig>('/admin/pipeline/config/reset'),
};
