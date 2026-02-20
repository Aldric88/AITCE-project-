import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import { showAiResultToast } from "../utils/aiFeedback.jsx";

export default function ModerationPanel() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selected, setSelected] = useState(null);
  const [open, setOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchPending = async () => {
    try {
      setLoading(true);
      const res = await api.get("/notes/pending");
      setNotes(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load pending notes");
    } finally {
      setLoading(false);
    }
  };

  const loadPreview = async (noteId) => {
    try {
      setPreviewLoading(true);

      const res = await api.get(`/secure/note/${noteId}/file`, {
        responseType: "blob",
      });

      const url = URL.createObjectURL(res.data);
      setPreviewUrl(url);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Preview load failed");
    } finally {
      setPreviewLoading(false);
    }
  };

  const runAI = async (noteId) => {
    try {
      toast.loading("Running AI analysis...", { id: `ai-${noteId}` });
      const res = await api.post(`/ai/analyze-note/${noteId}`);
      
      const { validation_success, validation_message, critical_issues, report, metadata } = res.data;
      toast.dismiss(`ai-${noteId}`);
      showAiResultToast({
        validation_success,
        validation_message,
        critical_issues,
        moderation_bucket: res.data.moderation_bucket,
        provider: res.data.provider,
        cached_reuse: res.data.cached_reuse,
      });

      // update local list with enhanced AI data
      setNotes((prev) =>
        prev.map((n) => (n.id === noteId ? { 
          ...n, 
          ai: {
            ...res.data,
            validation_success,
            validation_message,
            critical_issues,
            report,
            metadata
          }
        } : n))
      );

      // update selected if opened
      if (selected?.id === noteId) {
        setSelected((p) => ({ 
          ...p, 
          ai: {
            ...res.data,
            validation_success,
            validation_message,
            critical_issues,
            report,
            metadata
          }
        }));
      }
    } catch (err) {
      toast.dismiss(`ai-${noteId}`);
      showAiResultToast({
        validation_success: false,
        validation_message: err.response?.data?.detail || "AI analysis failed",
        critical_issues: ["Analysis request failed. Please retry."],
        moderation_bucket: "needs_moderator_review",
        provider: "error",
      });
    }
  };

  const approveNote = async (noteId) => {
    try {
      setActionLoading(true);
      await api.patch(`/notes/${noteId}/approve`);
      toast.success("Approved ✅");
      setOpen(false);
      setSelected(null);
      fetchPending();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Approve failed");
    } finally {
      setActionLoading(false);
    }
  };

  const rejectNote = async (noteId) => {
    try {
      if (rejectReason.trim().length < 3) {
        toast.error("Enter reject reason (min 3 chars)");
        return;
      }

      setActionLoading(true);
      await api.patch(`/notes/${noteId}/reject`, {
        reason: rejectReason,
      });

      toast.success("Rejected ❌");
      setRejectReason("");
      setOpen(false);
      setSelected(null);
      fetchPending();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reject failed");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  return (
    <Layout title="Moderation Panel">
      <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span className="text-2xl">⚖️</span>
            Pending Notes
          </h2>

          <button
            onClick={fetchPending}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 transition-all duration-200 font-medium shadow-lg shadow-blue-500/25"
          >
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-12">
            <Spinner label="Loading pending notes..." />
          </div>
        ) : notes.length === 0 ? (
          <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-12 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h3 className="text-xl font-semibold text-slate-200 mb-2">All Clear!</h3>
            <p className="text-slate-400">No pending notes to review</p>
          </div>
        ) : (
          <div className="space-y-4">
            {notes.map((n) => (
              <div
                key={n.id}
                className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 backdrop-blur-sm border border-slate-600/50 rounded-xl p-4 flex items-center justify-between hover:border-slate-500/50 transition-all duration-200"
              >
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-slate-100">{n.title}</h3>
                  <p className="text-slate-400 text-sm mt-1">
                    {n.dept} • Sem {n.semester} • {n.subject} • Unit {n.unit}
                  </p>

                  {n.ai ? (
                    <p className={`text-xs mt-2 flex items-center gap-1 ${
                      n.ai.validation_success 
                        ? 'text-emerald-400' 
                        : 'text-red-400'
                    }`}>
                      <span>{n.ai.validation_success ? '✅' : '❌'}</span> 
                      {n.ai.validation_success ? 'Valid' : 'Invalid'} Content
                    </p>
                  ) : (
                    <p className="text-xs text-yellow-400 mt-2 flex items-center gap-1">
                      <span>⚠️</span> AI not analyzed
                    </p>
                  )}
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => runAI(n.id)}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 text-white hover:from-purple-600 hover:to-purple-700 transition-all duration-200 font-medium shadow-lg shadow-purple-500/25"
                  >
                    🧠 Run AI
                  </button>

                  <button
                    onClick={() => {
                      setSelected(n);
                      setOpen(true);
                      setPreviewUrl("");
                      loadPreview(n.id);
                    }}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 text-white hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 font-medium shadow-lg shadow-indigo-500/25"
                  >
                    👁️ View
                  </button>
                </div>
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
                  <span>🧠</span> Review Note (AI Assisted)
                </h3>
                <button
                  onClick={() => {
                    setOpen(false);
                    setSelected(null);
                    setRejectReason("");
                    setPreviewUrl("");
                    if (previewUrl) {
                      URL.revokeObjectURL(previewUrl);
                    }
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
                  </div>

                  {/* AI Report */}
                  <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-semibold text-slate-100 flex items-center gap-2">
                        <span>🧠</span> AI Report
                      </h4>
                      {!selected.ai && (
                        <button
                          onClick={() => runAI(selected.id)}
                          className="px-3 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 text-white hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 text-sm font-medium"
                        >
                          Run AI Now
                        </button>
                      )}
                    </div>

                    {!selected.ai ? (
                      <p className="text-slate-400">AI analysis not run yet.</p>
                    ) : (
                      <div className="space-y-4">
                        {/* Analysis Header with Timestamp */}
                        <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-slate-300">AI Analysis Record</p>
                              <p className="text-xs text-slate-400">
                                Analyzed on: {new Date().toLocaleString()}
                              </p>
                            </div>
                            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                              selected.ai.validation_success 
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                                : 'bg-red-500/20 text-red-300 border border-red-500/30'
                            }`}>
                              {selected.ai.validation_success ? 'VALID' : 'INVALID'}
                            </div>
                          </div>
                        </div>

                        {/* Validation Status */}
                        <div className={`rounded-xl p-4 border ${
                          selected.ai.validation_success 
                            ? 'bg-gradient-to-br from-emerald-500/20 to-green-500/20 border-emerald-500/30' 
                            : 'bg-gradient-to-br from-red-500/20 to-rose-500/20 border-red-500/30'
                        }`}>
                          <p className="font-semibold text-slate-100 mb-2">
                            {selected.ai.validation_success ? '✅ Content Valid' : '❌ Content Invalid'}
                          </p>
                          <p className="text-sm text-slate-300">
                            {selected.ai.validation_message}
                          </p>
                        </div>

                        {/* Critical Issues */}
                        {selected.ai.critical_issues?.length > 0 && (
                          <div className="bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-200 font-semibold flex items-center gap-2 mb-2">
                              <span>🚨</span> Critical Issues ({selected.ai.critical_issues.length})
                            </p>
                            <ul className="text-red-300 text-sm space-y-1">
                              {selected.ai.critical_issues.map((issue, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  <span className="text-red-400 mt-1">•</span>
                                  <span>{issue}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Metadata Comparison */}
                        {selected.ai.metadata && (
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-sm font-medium text-slate-300 mb-2">📋 Metadata Analyzed:</p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="text-slate-400">Title:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.title}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Description:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.description || 'No description'}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Subject:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.subject}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Tags:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.tags?.join(', ') || 'No tags'}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Dept:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.dept}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Unit:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.unit}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* AI Analysis Summary */}
                        <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-xl p-3">
                          <p className="text-sm font-medium text-slate-300 mb-2">🤖 AI Analysis Summary:</p>
                          <p className="text-sm text-slate-400">{selected.ai.report?.summary}</p>
                        </div>

                        {/* Content Topics */}
                        {selected.ai.report?.topics?.length > 0 && (
                          <div>
                            <p className="text-sm font-medium text-slate-300 mb-2">🏷️ Topics Found:</p>
                            <div className="flex flex-wrap gap-2">
                              {selected.ai.report.topics.map((t, i) => (
                                <span
                                  key={i}
                                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Validation Scores Grid */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">🎯 Spam Score</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.spam_score || 0}%
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.spam_score < 30 ? 'Low Risk' : selected.ai.report?.spam_score < 70 ? 'Medium Risk' : 'High Risk'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">✅ Content Valid</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.content_valid ? '✅ Valid' : '❌ Invalid'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.content_valid ? 'Matches metadata' : 'Does not match'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">📚 Subject Match</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.subject_match ? '✅ Match' : '❌ Mismatch'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.subject_match ? 'Correct subject' : 'Wrong subject'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">🏷️ Tags Relevant</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.tags_relevance ? '✅ Relevant' : '❌ Irrelevant'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.tags_relevance ? 'Tags match content' : 'Tags do not match'}
                            </p>
                          </div>
                        </div>

                        {/* Detailed Validation Analysis */}
                        {selected.ai.report?.validation_details && (
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-sm font-medium text-slate-300 mb-2">🔍 Detailed Analysis:</p>
                            <div className="space-y-2 text-xs">
                              <div>
                                <span className="text-slate-400">Title Analysis:</span>
                                <p className="text-slate-300">{selected.ai.report.validation_details.title_analysis}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Description Analysis:</span>
                                <p className="text-slate-300">{selected.ai.report.validation_details.description_analysis}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Subject Analysis:</span>
                                <p className="text-slate-300">{selected.ai.report.validation_details.subject_analysis}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Tags Analysis:</span>
                                <p className="text-slate-300">{selected.ai.report.validation_details.tags_analysis}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Overall Assessment:</span>
                                <p className="text-slate-300">{selected.ai.report.validation_details.overall_assessment}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Warnings */}
                        {selected.ai.report?.warnings?.length > 0 && (
                          <div className="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border border-yellow-500/30 rounded-xl p-3">
                            <p className="text-yellow-200 font-semibold flex items-center gap-2 mb-2">
                              <span>⚠️</span> Warnings ({selected.ai.report.warnings.length})
                            </p>
                            <ul className="text-yellow-300 text-sm space-y-1">
                              {selected.ai.report.warnings.map((warning, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  <span className="text-yellow-400 mt-1">•</span>
                                  <span>{warning}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* PII Detection */}
                        {selected.ai.personal_info?.emails?.length > 0 || selected.ai.personal_info?.phones?.length > 0 ? (
                          <div className="bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-200 font-semibold flex items-center gap-2">
                              <span>🚨</span> Personal Information Found
                            </p>
                            <div className="text-red-300 text-sm mt-2 space-y-1">
                              {selected.ai.personal_info.emails?.length > 0 && (
                                <div>
                                  <span className="font-medium">Emails:</span> {selected.ai.personal_info.emails.join(', ')}
                                </div>
                              )}
                              {selected.ai.personal_info.phones?.length > 0 && (
                                <div>
                                  <span className="font-medium">Phones:</span> {selected.ai.personal_info.phones.join(', ')}
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="bg-gradient-to-br from-emerald-500/20 to-green-500/20 border border-emerald-500/30 rounded-xl p-3">
                            <p className="text-emerald-200 font-semibold flex items-center gap-2">
                              <span>✅</span> No Personal Information Detected
                            </p>
                            <p className="text-emerald-300 text-sm mt-1">Content appears to be clean of personal data</p>
                          </div>
                        )}

                        {/* Re-run AI Button */}
                        <div className="flex justify-center pt-4">
                          <button
                            onClick={() => runAI(selected.id)}
                            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 transition-all duration-200 text-sm font-medium"
                          >
                            🔄 Re-run Analysis
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* PDF Preview */}
                  <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-4">
                    <h4 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                      <span>📄</span> Note Preview (Secure)
                    </h4>

                    {previewLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Spinner label="Loading preview..." />
                      </div>
                    ) : previewUrl ? (
                      <div className="rounded-xl overflow-hidden border border-slate-600/50">
                        <iframe
                          src={previewUrl}
                          title="Secure Preview"
                          className="w-full"
                          style={{ height: "450px" }}
                        />
                      </div>
                    ) : (
                      <p className="text-slate-400">No preview loaded.</p>
                    )}
                  </div>

                  {/* Approve/Reject */}
                  <div className="space-y-4">
                    <div className="flex gap-3">
                      <button
                        onClick={() => approveNote(selected.id)}
                        disabled={actionLoading}
                        className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                          actionLoading
                            ? "bg-emerald-600/30 text-emerald-300 cursor-not-allowed"
                            : "bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25"
                        }`}
                      >
                        {actionLoading ? "..." : "✅ Approve"}
                      </button>

                      <button
                        onClick={() => rejectNote(selected.id)}
                        disabled={actionLoading}
                        className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                          actionLoading
                            ? "bg-red-600/30 text-red-300 cursor-not-allowed"
                            : "bg-gradient-to-r from-red-500 to-rose-600 text-white hover:from-red-600 hover:to-rose-700 shadow-lg shadow-red-500/25"
                        }`}
                      >
                        {actionLoading ? "..." : "❌ Reject"}
                      </button>
                    </div>

                    <textarea
                      className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-600/50 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all duration-200"
                      placeholder="Reject reason (required if rejecting)"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      rows={3}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
