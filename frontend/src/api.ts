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

export const addTorrent = (magnet_uri: string, media_type: "movie" | "tv") =>
  api.post("/api/torrents", { magnet_uri, media_type });

export const getHistory = () => api.get<HistoryItem[]>("/api/history");

export default api;
