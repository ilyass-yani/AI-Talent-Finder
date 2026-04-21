import { apiClient } from './api';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role: 'candidate' | 'recruiter' | 'admin';
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'candidate' | 'recruiter' | 'admin';
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
  user: User;
}

function persistTokens(payload: AuthResponse) {
  if (payload.access_token) {
    localStorage.setItem('access_token', payload.access_token);
  }
  if (payload.refresh_token) {
    localStorage.setItem('refresh_token', payload.refresh_token);
  }
}

export const authApi = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/auth/login', data);
    persistTokens(response.data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiClient.post('/api/auth/register', data);
    persistTokens(response.data);
    return response.data;
  },

  refresh: async (): Promise<{ access_token: string } | null> => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return null;
    const response = await apiClient.post('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    if (response.data?.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    return response.data;
  },

  me: async (): Promise<User> => {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },

  logout: async (): Promise<void> => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};
