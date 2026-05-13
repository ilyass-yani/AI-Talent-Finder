import apiClient from './api';

export interface FeedbackRecordRequest {
  criteria_id: number;
  candidate_id: number;
  model_predicted_score: number;
  model_predicted_decision: 'accepted' | 'review' | 'rejected';
  recruiter_decision: 'accepted' | 'rejected' | 'no_action';
  recruiter_score_override?: number | null;
  feedback_reason?: string | null;
}

export interface FeedbackStats {
  total_feedback: number;
  override_rate: string;
  override_count: number;
  distribution: Record<string, number>;
}

export interface SkillRecommendationItem {
  skill_name: string;
  frequency: number;
  trending_score: number;
  category: string;
  reason: string;
  average_proficiency: string;
}

export interface BiasAlertItem {
  alert_type: string;
  severity: string;
  message: string;
  affected_group: string;
  recommendation: string;
}

export interface BiasReport {
  analysis_date: string;
  total_records: number;
  alerts: BiasAlertItem[];
  disparities: Record<string, unknown>;
  recommendations: string[];
}

export interface RetrainingReadiness {
  ready: boolean;
  total_feedback: number;
  override_rate: number;
  min_samples: number;
  min_override_rate: number;
  reasons: string[];
}

export const feedbackApi = {
  recordDecision: (payload: FeedbackRecordRequest) =>
    apiClient.post('/feedback/record-decision', payload),

  getStatistics: () =>
    apiClient.get<FeedbackStats>('/feedback/statistics'),

  getMisclassified: (overrideOnly = true) =>
    apiClient.get('/feedback/misclassified', { params: { override_only: overrideOnly } }),

  recommendSkills: (jobTitle: string, currentSkills = '', missingSkills = '', topK = 5) =>
    apiClient.get<SkillRecommendationItem[]>('/feedback/recommendations/skills', {
      params: {
        job_title: jobTitle,
        current_skills: currentSkills,
        missing_skills: missingSkills,
        top_k: topK,
      },
    }),

  getComplementarySkills: (primarySkills = '', jobDomain = 'backend') =>
    apiClient.get('/feedback/recommendations/complementary', {
      params: {
        primary_skills: primarySkills,
        job_domain: jobDomain,
      },
    }),

  getCertifications: (jobTitle: string) =>
    apiClient.get('/feedback/recommendations/certifications', {
      params: { job_title: jobTitle },
    }),

  analyzeGap: (candidateSkills: string[], requiredSkills: string[]) =>
    apiClient.post('/feedback/recommendations/gap-analysis', {
      candidate_skills: candidateSkills,
      required_skills: requiredSkills,
    }),

  analyzeBias: (minSamples = 30) =>
    apiClient.post<BiasReport>('/feedback/bias-analyze', null, {
      params: { min_samples: minSamples },
    }),

  getBiasSummary: () =>
    apiClient.get<Record<string, unknown>>('/feedback/bias-alerts-summary'),

  getRetrainingStatus: () =>
    apiClient.get('/feedback/retraining-status'),

  getRetrainingReadiness: (minSamples = 50, minOverrideRate = 10) =>
    apiClient.get<RetrainingReadiness>('/feedback/retraining-readiness', {
      params: {
        min_samples: minSamples,
        min_override_rate: minOverrideRate,
      },
    }),

  exportRetrainingData: (outputPath?: string, minSamples = 50) =>
    apiClient.post('/feedback/export-retraining-data', null, {
      params: {
        output_path: outputPath,
        min_samples: minSamples,
      },
    }),

  getCriteriaSummary: (criteriaId: number) =>
    apiClient.get(`/feedback/criteria/${criteriaId}/summary`),

  triggerRetraining: (nEstimators = 100) =>
    apiClient.post('/feedback/retrain-model', null, {
      params: { n_estimators: nEstimators },
    }),
};