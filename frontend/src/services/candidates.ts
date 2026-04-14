import apiClient from './api';

// Interface correspondant au schéma CandidateResponse du backend
export interface Candidate {
  id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  cv_path?: string | null;
  raw_text?: string | null;
  created_at: string;
}

export const candidatesApi = {
  // GET /api/candidates/ — Liste tous les candidats
  getCandidates: (skip = 0, limit = 100) =>
    apiClient.get<Candidate[]>('/api/candidates/', { params: { skip, limit } }),

  // GET /api/candidates/:id — Détail d'un candidat
  getCandidate: (id: number) =>
    apiClient.get<Candidate>(`/api/candidates/${id}`),

  // POST /api/candidates/upload — Upload CV (file + full_name + email)
  uploadCV: (file: File, fullName?: string, email?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (fullName) formData.append('full_name', fullName);
    if (email) formData.append('email', email);
    return apiClient.post('/api/candidates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // POST /api/candidates/ — Créer un candidat manuellement
  createCandidate: (data: { full_name: string; email: string; phone?: string; linkedin_url?: string; github_url?: string; cv_path?: string; raw_text?: string }) =>
    apiClient.post<Candidate>('/api/candidates/', data),

  // PUT /api/candidates/:id — Modifier un candidat
  updateCandidate: (id: number, data: Partial<Candidate>) =>
    apiClient.put<Candidate>(`/api/candidates/${id}`, data),

  // DELETE /api/candidates/:id — Supprimer un candidat
  deleteCandidate: (id: number) =>
    apiClient.delete(`/api/candidates/${id}`),
};
