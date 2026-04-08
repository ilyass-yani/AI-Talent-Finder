import apiClient from './api';

export interface JobCriteria {
  id: number;
  recruiter_id: number;
  title: string;
  description: string;
  created_at: string;
}

export const jobsApi = {
  // Get all jobs
  getJobs: (skip = 0, limit = 100) =>
    apiClient.get<JobCriteria[]>('/jobs/', { params: { skip, limit } }),

  // Get a specific job
  getJob: (id: number) =>
    apiClient.get<JobCriteria>(`/jobs/${id}`),

  // Create a job
  createJob: (data: { title: string; description: string; recruiter_id?: number }) =>
    apiClient.post<JobCriteria>('/jobs/', { ...data, recruiter_id: data.recruiter_id ?? 1 }),

  // Update a job
  updateJob: (id: number, data: Partial<JobCriteria>) =>
    apiClient.put<JobCriteria>(`/jobs/${id}`, data),

  // Delete a job
  deleteJob: (id: number) =>
    apiClient.delete(`/jobs/${id}`),
};
