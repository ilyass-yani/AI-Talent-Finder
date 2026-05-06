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
  // NER Extraction Fields (Étape 5-6)
  extracted_name?: string | null;
  extracted_emails?: string | null;
  extracted_phones?: string | null;
  extracted_job_titles?: string | null;
  extracted_companies?: string | null;
  extracted_education?: string | null;
  extraction_quality_score?: number;
  ner_extraction_data?: string | null;
  is_fully_extracted?: boolean;
}

export interface CandidateVisibilityLike {
  full_name?: string | null;
  email?: string | null;
  raw_text?: string | null;
  extraction_quality_score?: number | null;
  is_fully_extracted?: boolean | null;
}

const placeholderPatterns = [
  /^unknown$/,
  /^target test$/,
  /^test$/,
  /^demo$/,
  /^sample$/,
  /^mock$/,
  /\bunknown\b/,
  /\btarget\s+test\b/,
  /\btest\b/,
  /\bdemo\b/,
  /\bsample\b/,
  /\bmock\b/,
];

export function isDisplayableIdentity(fullName?: string | null, email?: string | null): boolean {
  const name = (fullName || '').trim().toLowerCase();
  const normalizedEmail = (email || '').trim().toLowerCase();
  const combined = `${name} ${normalizedEmail}`.trim();
  if (!combined) {
    return false;
  }
  return !placeholderPatterns.some((pattern) => pattern.test(combined));
}

export function isDisplayableCandidate(candidate: CandidateVisibilityLike): boolean {
  if (!candidate.raw_text || !candidate.raw_text.trim()) {
    return false;
  }

  if ((candidate.extraction_quality_score ?? 0) < 0.8) {
    return false;
  }

  return isDisplayableIdentity(candidate.full_name, candidate.email);
}

export function filterDisplayableCandidates<T extends CandidateVisibilityLike>(candidates: T[]): T[] {
  return candidates.filter(isDisplayableCandidate);
}

export function filterDisplayableIdentities<T extends { full_name?: string | null; email?: string | null }>(items: T[]): T[] {
  return items.filter((item) => isDisplayableIdentity(item.full_name, item.email));
}

export function filterDisplayableCandidateNames<T extends { candidate_name?: string | null; candidate_email?: string | null }>(items: T[]): T[] {
  return items.filter((item) => isDisplayableIdentity(item.candidate_name, item.candidate_email));
}

export const candidatesApi = {
  UPLOAD_TIMEOUT_MS: Number(process.env.NEXT_PUBLIC_CV_UPLOAD_TIMEOUT_MS || 180000),

  // GET /api/candidates/me/profile — Récupérer mon profil (candidat authentifié)
  getMyProfile: () =>
    apiClient.get<Candidate>('/candidates/me/profile'),

  // GET /api/candidates/ — Liste tous les candidats
  getCandidates: (skip = 0, limit = 100) =>
    apiClient.get<Candidate[]>('/candidates/', { params: { skip, limit } }),

  // GET /api/candidates/:id — Détail d'un candidat
  getCandidate: (id: number) =>
    apiClient.get<Candidate>(`/candidates/${id}`),

  // POST /api/candidates/upload — Upload CV (file + full_name + email)
  uploadCV: (file: File, fullName?: string, email?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (fullName) formData.append('full_name', fullName);
    if (email) formData.append('email', email);
    // Don't manually set Content-Type for FormData - axios will set it with proper boundary
    return apiClient.post('/candidates/upload', formData, {
      timeout: candidatesApi.UPLOAD_TIMEOUT_MS,
    });
  },

  // POST /api/candidates/ — Créer un candidat manuellement
  createCandidate: (data: { full_name: string; email: string; phone?: string; linkedin_url?: string; github_url?: string; cv_path?: string; raw_text?: string }) =>
    apiClient.post<Candidate>('/candidates/', data),

  // PUT /api/candidates/:id — Modifier un candidat
  updateCandidate: (id: number, data: Partial<Candidate>) =>
    apiClient.put<Candidate>(`/candidates/${id}`, data),

  // DELETE /api/candidates/:id — Supprimer un candidat
  deleteCandidate: (id: number) =>
    apiClient.delete(`/candidates/${id}`),
};
