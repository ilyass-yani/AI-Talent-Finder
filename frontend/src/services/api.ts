import axios from 'axios';

function resolveApiUrl(): string {
  const runtimeUrl = typeof window !== 'undefined'
    ? (window as typeof window & { __NEXT_PUBLIC_API_URL?: string }).__NEXT_PUBLIC_API_URL
    : process.env.NEXT_PUBLIC_API_URL;

  if (runtimeUrl) {
    if (runtimeUrl.startsWith('http')) {
      return `${runtimeUrl.replace(/\/$/, '')}/api`;
    }

    if (runtimeUrl.startsWith('/') && process.env.NODE_ENV === 'production') {
      return runtimeUrl;
    }
  }

  // Local development should talk directly to the FastAPI backend.
  return process.env.NODE_ENV === 'production'
    ? '/api'
    : 'http://127.0.0.1:8000/api';
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
