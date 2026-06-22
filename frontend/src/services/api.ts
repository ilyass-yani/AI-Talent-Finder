import axios from 'axios';

function resolveApiUrl(): string {
  // Always prefer the explicit env variable (works in both dev and production).
  // NEXT_PUBLIC_API_URL must be set to https://RHmaster-ai-talent-finder-backend.hf.space
  // in Vercel (no trailing slash, no /api — the /api prefix is appended below).
  const runtimeUrl = typeof window !== 'undefined'
    ? (window as typeof window & { __NEXT_PUBLIC_API_URL?: string }).__NEXT_PUBLIC_API_URL
    : process.env.NEXT_PUBLIC_API_URL;

  if (runtimeUrl && runtimeUrl.startsWith('http')) {
    return `${runtimeUrl.replace(/\/$/, '')}/api`;
  }

  // Default: local development backend
  return 'http://127.0.0.1:8000/api';
}

const apiUrl = resolveApiUrl();
const defaultTimeoutMs = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS || 30000);

export const apiClient = axios.create({
  baseURL: apiUrl,
  timeout: defaultTimeoutMs,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Only set Content-Type for non-FormData requests
    if (!(config.data instanceof FormData)) {
      if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
    }
    
    // Add auth token if available
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    // Insert a slash before query strings so list endpoints reach their canonical
    // "/?skip=…" form without a 307 redirect.  Do NOT add a trailing slash to
    // paths without a query string: individual-resource routes (/candidates/23,
    // /criteria/2, …) are defined without one on the backend, so adding it here
    // causes a 307 redirect on every single call.
    if (config.url && typeof config.url === 'string') {
      const u = config.url;
      if (!u.startsWith('http')) {
        const authRoutes = ['/auth/login', '/auth/register', '/auth/me', '/auth/logout'];
        const isAuthRoute = authRoutes.some((route) => u.startsWith(route));

        if (!isAuthRoute && u.includes('?')) {
          const [path, query] = u.split('?');
          if (!path.endsWith('/')) {
            config.url = `${path}/?${query}`;
          }
        }
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        const pathname = window.location.pathname;
        const allowUnauthedDemo = pathname === '/demo' || pathname === '/recruiter/chatbot';

        if (!allowUnauthedDemo) {
          localStorage.removeItem('access_token');
          window.location.href = '/auth/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
