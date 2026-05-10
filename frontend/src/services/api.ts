import axios from 'axios';

function resolveApiUrl(): string {
  // In production, always use relative paths to avoid mixed content (HTTP vs HTTPS) issues
  // Relative paths automatically use the same protocol as the page
  if (process.env.NODE_ENV === 'production') {
    return '/api';
  }

  // In development, check for explicit API URL override
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
    // This handles both: /api/path and /api/path?query=value
    if (config.url && typeof config.url === 'string') {
      const u = config.url;
      // Only adjust relative api paths (not full URLs with http/https)
      if (!u.startsWith('http')) {
        // Check if path has a query string
        const hasQuery = u.includes('?');
        if (hasQuery) {
          // URL like "/api/candidates?skip=0" -> "/api/candidates/?skip=0"
          const [path, query] = u.split('?');
          if (!path.endsWith('/')) {
            config.url = path + '/?' + query;
          }
        } else {
          // URL like "/api/candidates" -> "/api/candidates/"
          if (!u.endsWith('/')) {
            config.url = u + '/';
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
