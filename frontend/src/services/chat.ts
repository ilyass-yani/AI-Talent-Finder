import apiClient from './api';

export interface ChatHistoryEntry {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatContext {
  current_criteria?: {
    id: number;
    title: string;
    required_skills: Array<{ name: string; weight: number }>;
  } | null;
  current_criteria_id?: number;
  top_candidates?: unknown[];
  history?: ChatHistoryEntry[];
}

export interface ChatRequestPayload {
  message: string;
  context: ChatContext;
  session_id?: string;
}

export interface ChatResponsePayload {
  response: string;
  intent: string;
  actions: string[];
}

export interface IdealProfileRequestPayload {
  job_title: string;
  job_description: string;
  required_skills: string[];
}

export interface IdealProfileResponsePayload {
  title: string;
  skills: Array<{ name: string; weight: number }>;
  experience: string;
  education: string;
  languages: string[];
  explanation: string;
}

export const chatApi = {
  sendMessage: (payload: ChatRequestPayload) =>
    apiClient.post<ChatResponsePayload>('/chat', payload),

  generateIdealProfile: (payload: IdealProfileRequestPayload) =>
    apiClient.post<IdealProfileResponsePayload>('/chat/ideal-profile', payload),
};
