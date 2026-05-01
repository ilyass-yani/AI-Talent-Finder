import axios from 'axios';

const runtimeApiUrl = typeof window !== 'undefined' ? (window as any).__NEXT_PUBLIC_API_URL : undefined;
let apiUrl: string | undefined;

if (typeof window !== 'undefined') {
  // Prefer runtime-injected value when available
  if (runtimeApiUrl && runtimeApiUrl !== 'undefined') {
    // If runtime config points at the backend public domain, prefer the
    // same-origin proxy to avoid CORS regardless of hostname checks. This
    // avoids edge-cache or hostname mismatches causing cross-origin calls.
    if (runtimeApiUrl.includes('ai-talent-finder-backend-production.up.railway.app')) {
      apiUrl = '/api';
    } else {
      apiUrl = runtimeApiUrl;
    }
  } else if (window.location.hostname.includes('ai-talent-finder-production-ed09.up.railway.app')) {
    // In production, prefer same-origin proxy to avoid CORS while DNS/edge caches update
    apiUrl = '/api';
  } else {
    apiUrl = process.env.NEXT_PUBLIC_API_URL;
  }
} else {
  apiUrl = process.env.NEXT_PUBLIC_API_URL;
}
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
      // Handle unauthorized
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
