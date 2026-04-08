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
  // GET /candidates/ — Liste tous les candidats
  getCandidates: (skip = 0, limit = 100) =>
    apiClient.get<Candidate[]>('/candidates/', { params: { skip, limit } }),

  // GET /candidates/:id — Détail d'un candidat
  getCandidate: (id: number) =>
    apiClient.get<Candidate>(`/candidates/${id}`),

  // POST /candidates/upload — Upload CV (file + full_name + email)
  uploadCV: (file: File, fullName?: string, email?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (fullName) formData.append('full_name', fullName);
    if (email) formData.append('email', email);
    return apiClient.post('/candidates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // POST /candidates/ — Créer un candidat manuellement
  createCandidate: (data: { full_name: string; email: string; phone?: string; linkedin_url?: string; github_url?: string; cv_path?: string; raw_text?: string }) =>
    apiClient.post<Candidate>('/candidates/', data),

  // PUT /candidates/:id — Modifier un candidat
  updateCandidate: (id: number, data: Partial<Candidate>) =>
    apiClient.put<Candidate>(`/candidates/${id}`, data),

  // DELETE /candidates/:id — Supprimer un candidat
  deleteCandidate: (id: number) =>
    apiClient.delete(`/candidates/${id}`),
};
