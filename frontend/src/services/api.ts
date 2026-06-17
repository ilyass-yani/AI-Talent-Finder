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
    // Ensure URL paths end with a slash to match backend routing.
    // This handles both: /api/path and /api/path?query=value.
    // Auth routes are excluded because the backend defines them without a trailing slash.
    if (config.url && typeof config.url === 'string') {
      const u = config.url;
      if (!u.startsWith('http')) {
        const authRoutes = ['/auth/login', '/auth/register', '/auth/me', '/auth/logout'];
        const isAuthRoute = authRoutes.some((route) => u.startsWith(route));

        if (!isAuthRoute) {
          const hasQuery = u.includes('?');
          if (hasQuery) {
            const [path, query] = u.split('?');
            if (!path.endsWith('/')) {
              config.url = `${path}/?${query}`;
            }
          } else if (!u.endsWith('/')) {
            config.url = `${u}/`;
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
