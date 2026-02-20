import { useEffect, useState } from "react";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import Layout from "../components/Layout";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";

export default function Moderation() {
  const { user } = useAuth();
  const [pending, setPending] = useState([]);
  const [reasonMap, setReasonMap] = useState({});
  const [analyzingMap, setAnalyzingMap] = useState({});

  const fetchPending = async () => {
    try {
      const res = await api.get("/notes/pending");
      setPending(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load pending notes");
    }
  };

  const analyzeNote = async (noteId) => {
    try {
      setAnalyzingMap((p) => ({ ...p, [noteId]: true }));
      toast.loading("Analyzing with AI...", { id: `analyze-${noteId}` });

      await api.post(`/ai/analyze-note/${noteId}`);

      toast.success("AI analysis complete! ✅", { id: `analyze-${noteId}` });
      fetchPending(); // Refresh to show AI results
    } catch (err) {
      toast.error(err.response?.data?.detail || "AI analysis failed", { id: `analyze-${noteId}` });
    } finally {
      setAnalyzingMap((p) => ({ ...p, [noteId]: false }));
    }
  };

  const moderate = async (noteId, status) => {
    try {
      const reason = reasonMap[noteId] || "";

      await api.patch(`/notes/${noteId}/moderate`, {
        status,
        reason,
      });

      toast.success(`Note ${status} ✅`);
      fetchPending();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Moderation failed");
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  if (!user || (user.role !== "admin" && user.role !== "moderator")) {
    return (
      <Layout title="Moderation">
        <p className="text-zinc-400">❌ You are not authorized to access this page.</p>
      </Layout>
    );
  }

  return (
    <Layout title="Moderation">
      <h2 className="text-2xl font-semibold mb-4">Pending Notes</h2>

      {pending.length === 0 ? (
        <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6">
          <p className="text-slate-400">✅ No pending notes right now.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {pending.map((n) => (
            <div
              key={n.id}
              className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-slate-100">{n.title}</h3>
                  <p className="text-slate-400 mt-2">
                    {n.dept} • {n.subject} • Unit {n.unit} • Sem {n.semester}
                  </p>
                </div>
                
                {/* AI Analysis Button */}
                <button
                  onClick={() => analyzeNote(n.id)}
                  disabled={analyzingMap[n.id]}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                    analyzingMap[n.id]
                      ? "bg-blue-600/30 text-blue-300 cursor-not-allowed"
                      : "bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 shadow-lg shadow-blue-500/25"
                  }`}
                >
                  {analyzingMap[n.id] ? "🧠 Analyzing..." : "🧠 AI Analyze"}
                </button>
              </div>

              {/* AI Results Display */}
              {n.ai && (
                <div className="mb-4 p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl">
                  <h4 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                    <span>🧠</span> AI Analysis Results
                  </h4>
                  
                  {/* Summary */}
                  {n.ai.summary && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-slate-300 mb-1">Summary:</p>
                      <p className="text-sm text-slate-400">{n.ai.summary}</p>
                    </div>
                  )}

                  {/* Topics */}
                  {n.ai.topics?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-sm font-medium text-slate-300 mb-2">Topics:</p>
                      <div className="flex flex-wrap gap-2">
                        {n.ai.topics.map((topic, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30"
                          >
                            #{topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Scores */}
                  <div className="grid grid-cols-3 gap-4 mb-3">
                    <div>
                      <p className="text-xs font-medium text-slate-400">Quality</p>
                      <p className="text-sm font-semibold text-slate-200">
                        {Math.round(n.ai.quality_score * 100)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-400">Relevance</p>
                      <p className="text-sm font-semibold text-slate-200">
                        {Math.round(n.ai.relevance_score * 100)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-400">Spam Risk</p>
                      <p className="text-sm font-semibold text-slate-200">
                        {Math.round(n.ai.spam_score * 100)}%
                      </p>
                    </div>
                  </div>

                  {/* Suggestion */}
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-slate-300">AI Suggestion:</p>
                      <p className={`text-sm font-semibold ${
                        n.ai.suggested_status === "approve" 
                          ? "text-emerald-400" 
                          : "text-red-400"
                      }`}>
                        {n.ai.suggested_status === "approve" ? "✅ Approve" : "❌ Reject"}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">{n.ai.reason}</p>
                    </div>

                    {/* PII Warning */}
                    {n.ai.pii_found && (
                      <div className="px-3 py-2 rounded-xl bg-red-500/20 border border-red-500/30">
                        <p className="text-xs font-medium text-red-400">⚠️ PII Detected</p>
                        <p className="text-xs text-red-300 mt-1">
                          {n.ai.pii_matches?.length || 0} items found
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {n.file_url && (
                <a
                  href={`${API_BASE_URL}${n.file_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block mt-3 text-blue-400 hover:text-blue-300 transition-colors"
                >
                  📄 View File
                </a>
              )}

              <div className="mt-4">
                <input
                  placeholder="Reason (optional)"
                  value={reasonMap[n.id] || ""}
                  onChange={(e) =>
                    setReasonMap((p) => ({ ...p, [n.id]: e.target.value }))
                  }
                  className="w-full max-w-md px-4 py-2 rounded-xl bg-slate-800/50 border border-slate-600/50 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                />
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  onClick={() => moderate(n.id, "approved")}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 transition-all duration-200 font-medium shadow-lg shadow-emerald-500/25"
                >
                  ✅ Approve
                </button>
                <button
                  onClick={() => moderate(n.id, "rejected")}
                  className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-red-500 to-rose-600 text-white hover:from-red-600 hover:to-rose-700 transition-all duration-200 font-medium shadow-lg shadow-red-500/25"
                >
                  ❌ Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
