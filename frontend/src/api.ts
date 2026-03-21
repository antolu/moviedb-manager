import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

export interface Torrent {
  id: string;
  name: string;
  progress: number;
  state: string;
  eta: number;
  upspeed: number;
  dlspeed: number;
}

export interface HistoryItem {
  id: number;
  filename: string;
  final_path: string;
  moved_at: string;
}

export interface StatusResponse {
  status: string;
  version: string;
  errors?: string[];
}

export const addTorrent = (magnet_uri: string, media_type: "movie" | "tv") =>
  api.post("/torrents", { magnet_uri, media_type });

export const getHistory = () => api.get<HistoryItem[]>("/history");

export const getStatus = () => api.get<StatusResponse>("/status");

export default api;
