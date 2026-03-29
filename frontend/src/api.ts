import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent("moviedb-auth-required"));
    }
    return Promise.reject(error);
  },
);

export interface Torrent {
  id: string;
  name: string;
  progress: number;
  state: string;
  eta: number;
  upspeed: number;
  dlspeed: number;
  message?: string;
}

export interface HistoryItem {
  id: number;
  filename: string;
  final_path: string;
  moved_at: string;
  media_type: string;
}

export interface StatusResponse {
  status: string;
  version: string;
  errors?: string[];
}

export interface AuthUser {
  id: string;
  username?: string;
  email?: string;
  is_admin?: boolean;
}

export const exchangeAuthCode = (code: string) =>
  api.post<{ access_token: string; expires_in: number; user?: AuthUser }>(
    "/auth/exchange",
    { code },
  );

export const getCurrentUser = () => api.get<AuthUser>("/auth/me");

export const logout = () => api.post("/auth/logout");

export const addTorrent = (magnet_uri: string, media_type: "movie" | "tv") =>
  api.post("/torrents", { magnet_uri, media_type });

export const getHistory = () => api.get<HistoryItem[]>("/history");

export const getStatus = () => api.get<StatusResponse>("/status");

export default api;
