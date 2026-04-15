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

// Extracted data types
export interface Skill {
  id: number;
  name: string;
  proficiency_level: string;
  category?: string;
  source?: string;
}

export interface Experience {
  id: number;
  job_title?: string;
  title?: string;
  company: string;
  duration_months: number;
  description?: string;
}

export interface Education {
  id: number;
  degree: string;
  institution: string;
  field?: string;
  field_of_study?: string;
  year?: number;
  graduation_year?: number;
}

export interface CandidateProfile {
  candidate_id: number;
  filename: string;
  full_name?: string;
  email?: string | null;
  phone?: string | null;
  headline?: string;
  summary?: string;
  contact?: {
    email?: string | null;
    phone?: string | null;
  };
  sections_detected?: string[];
  skills_count: number;
  experiences_count: number;
  educations_count: number;
  skills: Skill[];
  experiences: Experience[];
  educations: Education[];
}

export const candidatesApi = {
  // GET /api/candidates/ — Liste tous les candidats
  getCandidates: (skip = 0, limit = 100) =>
    apiClient.get<Candidate[]>('/api/candidates/', { params: { skip, limit } }),

  // GET /api/candidates/:id — Détail d'un candidat
  getCandidate: (id: number) =>
    apiClient.get<Candidate>(`/api/candidates/${id}`),

  // GET /api/candidates/:id/profile-complete — Récupérer le profil complet avec toutes les données extraites
  getCandidateProfile: (id: number) =>
    apiClient.get<CandidateProfile>(`/api/candidates/${id}/profile-complete`),

  // GET /api/candidates/:id/skills — Récupérer les compétences
  getCandidateSkills: (id: number) =>
    apiClient.get<{ skills: Skill[] }>(`/api/candidates/${id}/skills`),

  // GET /api/candidates/:id/experiences — Récupérer les expériences
  getCandidateExperiences: (id: number) =>
    apiClient.get<{ experiences: Experience[] }>(`/api/candidates/${id}/experiences`),

  // GET /api/candidates/:id/educations — Récupérer les formations
  getCandidateEducations: (id: number) =>
    apiClient.get<{ educations: Education[] }>(`/api/candidates/${id}/educations`),

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
