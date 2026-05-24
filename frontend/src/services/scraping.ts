import apiClient from './api';

export interface ScrapeRequest {
  keywords: string;
  location: string;
  sources: string[];
  max_per_source: number;
  fetch_descriptions: boolean;
}

export interface ScrapedJob {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  description: string | null;
  url: string | null;
  source: string | null;
  keywords: string | null;
  contract_type: string | null;
  salary_range: string | null;
  posted_at: string | null;
  imported: boolean;
}

export interface ScrapeStats {
  total: number;
  sources: Record<string, number>;
  keywords_summary: string[];
}

export const scrapingApi = {
  scrapeSync: (req: ScrapeRequest) =>
    apiClient.post<{ saved: number; keywords: string; sources: string[] }>('/scraping/jobs/sync', req),

  scrapeAsync: (req: ScrapeRequest) =>
    apiClient.post<{ status: string; message: string }>('/scraping/jobs', req),

  listJobs: (params?: { keywords?: string; source?: string; imported?: boolean; limit?: number; offset?: number }) =>
    apiClient.get<ScrapedJob[]>('/scraping/jobs', { params }),

  getStats: () =>
    apiClient.get<ScrapeStats>('/scraping/jobs/stats'),

  importJob: (jobId: number) =>
    apiClient.post<{ message: string; criteria_id: number; scraped_job_id: number }>(`/scraping/jobs/${jobId}/import`),

  deleteJob: (jobId: number) =>
    apiClient.delete(`/scraping/jobs/${jobId}`),
};
