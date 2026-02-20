import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";

export default function RejectedNotes() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selected, setSelected] = useState(null);
  const [open, setOpen] = useState(false);

  const fetchRejected = async () => {
    try {
      setLoading(true);
      const res = await api.get("/notes/rejected");
      setNotes(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load rejected notes");
    } finally {
      setLoading(false);
    }
  };

  const overrideApprove = async (noteId) => {
    try {
      toast.loading("Overriding approval...", { id: `ov-${noteId}` });
      await api.patch(`/notes/${noteId}/override-approve`);
      toast.success("Approved ✅", { id: `ov-${noteId}` });
      setOpen(false);
      fetchRejected();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Override approve failed", {
        id: `ov-${noteId}`,
      });
    }
  };

  useEffect(() => {
    fetchRejected();
  }, []);

  return (
    <Layout title="Rejected Notes">
      <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span className="text-2xl">❌</span>
            Rejected Notes
          </h2>
          <button
            onClick={fetchRejected}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 transition-all duration-200 font-medium shadow-lg shadow-blue-500/25"
          >
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-12">
            <Spinner label="Loading rejected notes..." />
          </div>
        ) : notes.length === 0 ? (
          <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-12 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h3 className="text-xl font-semibold text-slate-200 mb-2">All Clear!</h3>
            <p className="text-slate-400">No rejected notes found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {notes.map((n) => (
              <div
                key={n.id}
                className="bg-gradient-to-br from-red-500/10 to-rose-500/10 backdrop-blur-sm border border-red-500/20 rounded-xl p-4 flex items-center justify-between hover:border-red-500/30 transition-all duration-200"
              >
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-slate-100">{n.title}</h3>
                  <p className="text-slate-400 text-sm mt-1">
                    {n.dept} • Sem {n.semester} • {n.subject} • Unit {n.unit}
                  </p>
                  <p className="text-red-300 text-sm mt-2 flex items-center gap-1">
                    <span>❌</span> {n.rejected_reason}
                  </p>
                  {n.rejected_at && (
                    <p className="text-slate-500 text-xs mt-1">
                      Rejected: {new Date(n.rejected_at * 1000).toLocaleDateString()}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => {
                    setSelected(n);
                    setOpen(true);
                  }}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 text-white hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 font-medium shadow-lg shadow-indigo-500/25"
                >
                  👁️ View AI
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span>🧠</span> Rejected Note Details
                </h3>
                <button
                  onClick={() => {
                    setOpen(false);
                    setSelected(null);
                  }}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  ✕
                </button>
              </div>

              {!selected ? (
                <p className="text-slate-400">No note selected.</p>
              ) : (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-slate-100">{selected.title}</h3>
                    <p className="text-slate-400 text-sm mt-1">
                      {selected.dept} • Sem {selected.semester} • {selected.subject} • Unit{" "}
                      {selected.unit}
                    </p>
                    {selected.is_paid && (
                      <p className="text-yellow-400 text-sm mt-1">💰 Paid: ₹{selected.price}</p>
                    )}
                    <div className="mt-3 p-3 bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl">
                      <p className="text-red-200 font-semibold flex items-center gap-2">
                        <span>❌</span> Rejection Reason
                      </p>
                      <p className="text-red-300 text-sm mt-1">{selected.rejected_reason}</p>
                    </div>
                  </div>

                  {/* AI Report */}
                  <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-4">
                    <h4 className="font-semibold text-slate-100 mb-4 flex items-center gap-2">
                      <span>🧠</span> AI Report
                    </h4>

                    {!selected.ai ? (
                      <p className="text-slate-400">No AI data found.</p>
                    ) : (
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm font-medium text-slate-300 mb-1">Summary:</p>
                          <p className="text-sm text-slate-400">{selected.ai.summary}</p>
                        </div>

                        {selected.ai.topics?.length > 0 && (
                          <div>
                            <p className="text-sm font-medium text-slate-300 mb-2">Topics:</p>
                            <div className="flex flex-wrap gap-2">
                              {selected.ai.topics.map((t, i) => (
                                <span
                                  key={i}
                                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30"
                                >
                                  #{t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Spam Score</p>
                            <p className="text-lg font-bold text-slate-200">
                              {Math.round(selected.ai.spam_score * 100)}%
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Relevance</p>
                            <p className="text-lg font-bold text-slate-200">
                              {Math.round(selected.ai.relevance_score * 100)}%
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">Quality</p>
                            <p className="text-lg font-bold text-slate-200">
                              {Math.round(selected.ai.quality_score * 100)}%
                            </p>
                          </div>
                        </div>

                        <div>
                          <p className="text-sm font-medium text-slate-300">
                            AI Suggestion:{" "}
                            <span className={`font-semibold ${
                              selected.ai.suggested_status === "approve" 
                                ? "text-emerald-400" 
                                : "text-red-400"
                            }`}>
                              {selected.ai.suggested_status === "approve" ? "✅ Approve" : "❌ Reject"}
                            </span>
                          </p>
                          <p className="text-xs text-slate-400 mt-1">{selected.ai.reason}</p>
                        </div>

                        {selected.ai.subject_mismatch && (
                          <div className="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border border-yellow-500/30 rounded-xl p-3">
                            <p className="text-yellow-200 font-semibold flex items-center gap-2">
                              <span>⚠️</span> Subject Mismatch Detected
                            </p>
                            <p className="text-yellow-300 text-sm mt-1">
                              {selected.ai.subject_mismatch_reason}
                            </p>
                          </div>
                        )}

                        {selected.ai.pii_found && (
                          <div className="bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-200 font-semibold flex items-center gap-2">
                              <span>⚠️</span> PII Found
                            </p>
                            <p className="text-red-300 text-sm mt-1">
                              {selected.ai.pii_matches?.join(", ")}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Override Approve Button */}
                  <button
                    onClick={() => overrideApprove(selected.id)}
                    className="w-full px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 transition-all duration-200 font-semibold shadow-lg shadow-emerald-500/25"
                  >
                    ✅ Override Approve
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
