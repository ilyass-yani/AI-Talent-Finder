import axios from "axios";
import Cookies from "js-cookie";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((c) => {
  const t = Cookies.get("access_token");
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

api.interceptors.response.use((r) => r, (e) => {
  if (e.response?.status === 401) { Cookies.remove("access_token"); if (typeof window !== "undefined") window.location.href = "/login"; }
  return Promise.reject(e);
});

export const authService = {
  register: (data: { email: string; password: string; full_name: string; role: string }) => api.post("/register", data),
  login: async (email: string, password: string) => {
    const fd = new URLSearchParams(); fd.append("username", email); fd.append("password", password);
    const r = await api.post("/login", fd, { headers: { "Content-Type": "application/x-www-form-urlencoded" } });
    Cookies.set("access_token", r.data.access_token, { expires: 1 }); return r.data;
  },
  me: () => api.get("/me"),
  logout: () => Cookies.remove("access_token"),
};

export const candidateService = {
  list: (params?: Record<string, string | number>) => api.get("/api/candidates", { params }),
  get: (id: string) => api.get(`/api/candidates/${id}`),
  delete: (id: string) => api.delete(`/api/candidates/${id}`),
  uploadCV: (files: File[]) => { const fd = new FormData(); files.forEach(f => fd.append("files", f)); return api.post("/api/candidates/upload", fd, { headers: { "Content-Type": "multipart/form-data" } }); },
  downloadCV: (id: string) => api.get(`/api/candidates/${id}/cv`, { responseType: "blob" }),
};

export const criteriaService = {
  list: () => api.get("/api/criteria"),
  create: (data: unknown) => api.post("/api/criteria", data),
  update: (id: string, data: unknown) => api.put(`/api/criteria/${id}`, data),
  delete: (id: string) => api.delete(`/api/criteria/${id}`),
};

export const matchingService = {
  run: (criteriaId: string) => api.post(`/api/matching/${criteriaId}`),
  results: (criteriaId: string) => api.get(`/api/matching/${criteriaId}/results`),
};

export const favoriteService = {
  list: () => api.get("/api/favorites"),
  add: (id: string) => api.post(`/api/favorites/${id}`),
  remove: (id: string) => api.delete(`/api/favorites/${id}`),
};

export const chatService = {
  send: (message: string, conversationId?: string) => api.post("/api/chat", { message, conversation_id: conversationId }),
};

export const exportService = {
  pdf: (id: string) => api.get(`/api/export/pdf/${id}`, { responseType: "blob" }),
  csv: (id: string) => api.get(`/api/export/csv/${id}`, { responseType: "blob" }),
  excel: (id: string) => api.get(`/api/export/excel/${id}`, { responseType: "blob" }),
};

export default api;
