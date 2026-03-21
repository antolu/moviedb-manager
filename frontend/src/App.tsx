import { useEffect, useState } from "react";
import axios from "axios";
import {
  Download,
  History,
  Activity,
  Play,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowDownCircle,
  ArrowUpCircle,
} from "lucide-react";
import {
  addTorrent,
  getHistory,
  getStatus,
  type Torrent,
  type HistoryItem,
  type StatusResponse,
} from "./api";

function App() {
  type Tab = "download" | "status" | "history";
  const [activeTab, setActiveTab] = useState<Tab>("status");
  const [magnet, setMagnet] = useState("");
  const [mediaType, setMediaType] = useState<"movie" | "tv">("movie");
  const [torrents, setTorrents] = useState<Torrent[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const buildVersion = import.meta.env.VITE_APP_VERSION;
  const [message, setMessage] = useState<{
    text: string;
    type: "success" | "error";
  } | null>(null);

  const tabs: Array<{ id: Tab; icon: typeof Download; label: string }> = [
    { id: "download", icon: Download, label: "Add Link" },
    { id: "status", icon: Activity, label: "Live Status" },
    { id: "history", icon: History, label: "Reports" },
  ];

  // SSE for real-time status
  useEffect(() => {
    const eventSource = new EventSource("/api/torrents/stream");

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // SSE returns an array of torrent updates
      if (Array.isArray(data)) {
        setTorrents(data.map((torrent) => normalizeTorrent(torrent)));
      }
    };

    eventSource.onerror = () => {
      console.error("SSE connection failed");
      eventSource.close();
    };

    return () => eventSource.close();
  }, []);

  useEffect(() => {
    void getStatus().then((response) => setStatus(response.data));
  }, []);

  // Fetch history
  useEffect(() => {
    if (activeTab === "history") {
      getHistory().then((res) => setHistory(res.data));
    }
  }, [activeTab]);

  const handleAddTorrent = async () => {
    if (!magnet) return;
    setLoading(true);
    setMessage(null);
    try {
      await addTorrent(magnet, mediaType);
      setMagnet("");
      setMessage({ text: "Added to download queue!", type: "success" });
      setTimeout(() => setActiveTab("status"), 1000);
    } catch (error: unknown) {
      const messageText = axios.isAxiosError(error)
        ? ((error.response?.data as { detail?: string } | undefined)?.detail ??
          "Failed to add torrent")
        : "Failed to add torrent";

      setMessage({ text: messageText, type: "error" });
    } finally {
      setLoading(false);
    }
  };

  function normalizeTorrent(torrent: Torrent): Torrent {
    return {
      ...torrent,
      progress: Number.parseFloat(String(torrent.progress)) || 0,
      dlspeed: Number.parseInt(String(torrent.dlspeed), 10) || 0,
      upspeed: Number.parseInt(String(torrent.upspeed), 10) || 0,
      eta: Number.parseInt(String(torrent.eta), 10) || 0,
    };
  }

  const formatSpeed = (bytes: number) => {
    if (bytes === 0) return "0 B/s";
    const k = 1024;
    const sizes = ["B/s", "KB/s", "MB/s", "GB/s"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatEta = (seconds: number) => {
    if (seconds <= 0 || seconds > 864000) return "∞";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m ${s}s`;
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 w-full flex flex-col items-center selection:bg-blue-500/30">
      {/* Dynamic Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
        <div
          className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse"
          style={{ animationDelay: "1s" }}
        />
      </div>

      <header className="w-full max-w-5xl p-6 flex flex-col sm:flex-row justify-between items-center border-b border-white/5 gap-6 backdrop-blur-xl sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Play className="fill-white text-white ml-1" size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              MOVIEDB
            </h1>
            <p className="text-xs uppercase tracking-[0.3em] text-neutral-500">
              {buildVersion
                ? `v${buildVersion}`
                : status?.version
                  ? `v${status.version}`
                  : "Loading version"}
            </p>
          </div>
        </div>

        <nav className="flex bg-white/5 p-1 rounded-2xl border border-white/5">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-xl transition-all font-medium ${
                activeTab === tab.id
                  ? "bg-white/10 text-white shadow-inner"
                  : "hover:bg-white/5 text-neutral-400"
              }`}
            >
              <tab.icon size={18} />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </nav>
      </header>

      <main className="w-full max-w-5xl p-6 sm:p-10 flex-1">
        {activeTab === "download" && (
          <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white/5 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 sm:p-12 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 blur-3xl -mr-16 -mt-16" />

              <h2 className="text-3xl font-bold mb-2">New Magnet</h2>
              <p className="text-neutral-400 mb-8">
                Drop your magnet link to start the automated pipeline.
              </p>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-neutral-500 mb-2 ml-1">
                    Magnet URI
                  </label>
                  <input
                    type="text"
                    value={magnet}
                    onChange={(e) => setMagnet(e.target.value)}
                    placeholder="magnet:?xt=urn:btih:..."
                    className="w-full bg-black/40 border border-white/10 rounded-2xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-mono text-sm placeholder:text-neutral-700"
                  />
                </div>

                <div className="flex gap-4">
                  {(["movie", "tv"] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setMediaType(type)}
                      className={`flex-1 py-4 rounded-2xl border transition-all font-semibold capitalize ${
                        mediaType === type
                          ? "bg-white/10 border-white/20 text-white"
                          : "bg-transparent border-white/5 text-neutral-500 hover:border-white/10"
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleAddTorrent}
                  disabled={loading || !magnet}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 text-white py-4 rounded-2xl font-bold shadow-lg shadow-blue-600/20 transition-all active:scale-[0.98] flex items-center justify-center gap-2"
                >
                  {loading ? (
                    "Adding..."
                  ) : (
                    <>
                      <Download size={20} /> Process Link
                    </>
                  )}
                </button>

                {message && (
                  <div
                    className={`p-4 rounded-2xl flex items-start gap-3 animate-in fade-in zoom-in duration-300 ${
                      message.type === "success"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}
                  >
                    {message.type === "success" ? (
                      <CheckCircle2 size={20} className="mt-0.5" />
                    ) : (
                      <AlertCircle size={20} className="mt-0.5" />
                    )}
                    <p className="text-sm font-medium">{message.text}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "status" && (
          <div className="animate-in fade-in duration-500">
            <div className="flex justify-between items-center mb-8">
              <div>
                <h2 className="text-3xl font-bold tracking-tight">
                  Active Transfers
                </h2>
                <p className="text-neutral-400">
                  Monitoring {torrents.length} active torrents in real-time.
                </p>
              </div>
            </div>

            {torrents.length === 0 ? (
              <div className="bg-white/5 border border-white/5 rounded-3xl py-24 flex flex-col items-center justify-center text-center px-6">
                <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-6 text-neutral-700">
                  <Activity size={32} />
                </div>
                <h3 className="text-lg font-semibold text-neutral-400">
                  No active transfers
                </h3>
                <p className="text-neutral-600 max-w-xs mt-2">
                  Active downloads will appear here with live speed and progress
                  metrics.
                </p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
                {torrents.map((torrent) => (
                  <div
                    key={torrent.id}
                    className="bg-white/5 backdrop-blur-md border border-white/10 rounded-3xl p-6 sm:p-8 hover:bg-white/[0.07] transition-all relative group"
                  >
                    <div className="flex flex-col gap-6">
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-bold text-lg truncate mb-1 pr-6">
                            {torrent.name}
                          </h3>
                          <div className="flex items-center gap-4 text-xs font-medium uppercase tracking-wider text-neutral-500">
                            <span className="flex items-center gap-1.5">
                              <Clock size={14} /> {formatEta(torrent.eta)}
                            </span>
                            <span className="flex items-center gap-1.5 text-blue-400">
                              <ArrowDownCircle size={14} />{" "}
                              {formatSpeed(torrent.dlspeed)}
                            </span>
                            <span className="flex items-center gap-1.5">
                              <ArrowUpCircle size={14} />{" "}
                              {formatSpeed(torrent.upspeed)}
                            </span>
                          </div>
                        </div>
                        <button className="text-neutral-600 hover:text-red-400 transition-colors p-2 rounded-xl hover:bg-red-400/10">
                          <Trash2 size={20} />
                        </button>
                      </div>

                      <div className="space-y-4">
                        <div className="w-full bg-black/40 h-3 rounded-full overflow-hidden border border-white/5">
                          <div
                            className="bg-gradient-to-r from-blue-600 to-purple-500 h-full rounded-full shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-all duration-1000 ease-out"
                            style={{ width: `${torrent.progress * 100}%` }}
                          />
                        </div>
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-neutral-400 font-semibold">
                            {torrent.state}
                          </span>
                          <span className="text-white font-black text-lg">
                            {(torrent.progress * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "history" && (
          <div className="animate-in fade-in duration-500">
            <h2 className="text-3xl font-bold mb-2">History Report</h2>
            <p className="text-neutral-400 mb-8">
              Registry of successfully processed media files.
            </p>

            {history.length === 0 ? (
              <div className="bg-white/5 border border-white/5 rounded-3xl py-32 flex flex-col items-center justify-center text-center px-6">
                <History size={48} className="text-neutral-800 mb-6" />
                <p className="text-neutral-500 font-medium">
                  Your download history is currently empty.
                </p>
              </div>
            ) : (
              <div className="bg-white/5 backdrop-blur-md border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-white/5 bg-white/[0.02]">
                      <th className="px-8 py-5 text-xs font-bold uppercase tracking-widest text-neutral-500">
                        Filename
                      </th>
                      <th className="px-8 py-5 text-xs font-bold uppercase tracking-widest text-neutral-500 text-right">
                        Destination
                      </th>
                      <th className="px-8 py-5 text-xs font-bold uppercase tracking-widest text-neutral-500 text-right">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {history.map((item) => (
                      <tr
                        key={item.id}
                        className="hover:bg-white/[0.02] transition-colors group"
                      >
                        <td className="px-8 py-6 font-semibold max-w-sm">
                          <div className="flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-sm" />
                            <span className="truncate">{item.filename}</span>
                          </div>
                        </td>
                        <td className="px-8 py-6 text-sm text-neutral-400 font-mono text-right max-w-xs truncate">
                          {item.final_path}
                        </td>
                        <td className="px-8 py-6 text-sm text-neutral-500 text-right">
                          {new Date(item.moved_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="w-full max-w-5xl p-10 flex border-t border-white/5 mt-auto opacity-20 text-xs font-medium justify-center items-center gap-6 grayscale">
        <span className="flex items-center gap-2">REDIS CORED</span>
        <span className="w-1 h-1 bg-white rounded-full" />
        <span className="flex items-center gap-2 text-blue-400 uppercase">
          Production Ready v2.1.0
        </span>
      </footer>
    </div>
  );
}

export default App;
