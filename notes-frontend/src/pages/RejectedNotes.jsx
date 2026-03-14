import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";

export default function RejectedNotes() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [appealText, setAppealText] = useState("");
  const [submittingAppeal, setSubmittingAppeal] = useState(false);
  const [appealedNotes, setAppealedNotes] = useState(new Set());

  const fetchRejected = async () => {
    try {
      setLoading(true);
      // student-accessible: own rejected notes only
      const res = await api.get("/notes/my/rejected");
      setNotes(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load rejected notes");
    } finally {
      setLoading(false);
    }
  };

  const submitAppeal = async () => {
    if (!selected) return;
    if (!appealText.trim() || appealText.trim().length < 10) {
      toast.error("Appeal message must be at least 10 characters");
      return;
    }
    try {
      setSubmittingAppeal(true);
      await api.post(`/moderation/features/appeals/${selected.id}`, {
        message: appealText.trim(),
      });
      toast.success("Appeal submitted! Moderators will review it.");
      setAppealedNotes((prev) => new Set([...prev, selected.id]));
      setAppealText("");
      setModalOpen(false);
      setSelected(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit appeal");
    } finally {
      setSubmittingAppeal(false);
    }
  };

  const openModal = (note) => {
    setSelected(note);
    setAppealText("");
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelected(null);
    setAppealText("");
  };

  useEffect(() => {
    fetchRejected();
  }, []);

  return (
    <Layout title="Rejected Notes">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight text-black">Rejected Notes</h2>
            <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
              Your notes that were rejected. You can appeal each rejection.
            </p>
          </div>
          <button onClick={fetchRejected} className="btn-secondary text-xs px-4 py-2">
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="border border-black bg-white p-12">
            <Spinner label="Loading rejected notes..." />
          </div>
        ) : notes.length === 0 ? (
          <div className="border border-dashed border-zinc-300 bg-zinc-50 p-16 text-center">
            <div className="text-4xl mb-4">✅</div>
            <h3 className="text-sm font-black uppercase tracking-[0.2em] text-zinc-800 mb-2">All Clear</h3>
            <p className="text-xs font-medium text-zinc-500">None of your notes have been rejected.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {notes.map((n) => {
              const alreadyAppealed = appealedNotes.has(n.id);
              return (
                <div key={n.id} className="border border-red-200 bg-white p-6">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className="border border-red-200 bg-red-50 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-red-700">
                          Rejected
                        </span>
                        {n.is_paid && (
                          <span className="border border-zinc-200 bg-zinc-50 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-zinc-700">
                            Paid · ₹{n.price}
                          </span>
                        )}
                      </div>

                      <h3 className="text-xl font-black uppercase tracking-tight text-zinc-900">{n.title}</h3>
                      <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
                        {n.dept} · Sem {n.semester} · {n.subject} · Unit {n.unit}
                      </p>

                      <div className="mt-3 border-l-4 border-red-400 bg-red-50 py-2 pl-4 pr-3">
                        <p className="text-[10px] font-black uppercase tracking-wider text-red-600 mb-1">
                          Rejection Reason
                        </p>
                        <p className="text-sm text-red-700">{n.rejected_reason || "No reason provided"}</p>
                      </div>

                      {n.rejected_at && (
                        <p className="mt-2 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                          Rejected on{" "}
                          {new Date(n.rejected_at * 1000).toLocaleDateString("en-IN", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })}
                        </p>
                      )}

                      {/* AI scores if available */}
                      {n.ai && (
                        <div className="mt-3 grid grid-cols-3 gap-2">
                          {[
                            { label: "Quality", value: n.ai.quality_score },
                            { label: "Relevance", value: n.ai.relevance_score },
                            { label: "Spam", value: n.ai.spam_score },
                          ].map(({ label, value }) => (
                            <div key={label} className="border border-zinc-200 bg-zinc-50 p-2 text-center">
                              <p className="text-[10px] font-black uppercase tracking-wider text-zinc-400">{label}</p>
                              <p className="text-sm font-black text-zinc-800">{Math.round((value || 0) * 100)}%</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 lg:items-end shrink-0">
                      {alreadyAppealed ? (
                        <span className="border border-blue-200 bg-blue-50 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-blue-700">
                          Appeal Submitted
                        </span>
                      ) : (
                        <button
                          onClick={() => openModal(n)}
                          className="btn-primary text-xs px-4 py-2"
                        >
                          Submit Appeal
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Appeal Modal */}
      {modalOpen && selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg border border-black bg-white">
            <div className="border-b border-black p-4 flex items-center justify-between">
              <h3 className="text-sm font-black uppercase tracking-wider text-black">Submit Appeal</h3>
              <button
                onClick={closeModal}
                className="text-zinc-500 hover:text-black font-bold text-lg leading-none"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <p className="text-[10px] font-black uppercase tracking-wider text-zinc-500 mb-1">Note</p>
                <p className="text-sm font-bold text-zinc-900">{selected.title}</p>
              </div>

              <div className="bg-red-50 border border-red-200 p-3">
                <p className="text-[10px] font-black uppercase tracking-wider text-red-600 mb-1">
                  Rejection Reason
                </p>
                <p className="text-sm text-red-700">{selected.rejected_reason || "No reason provided"}</p>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-600 mb-2">
                  Your Appeal <span className="text-red-500">*</span>
                </label>
                <textarea
                  className="w-full border border-zinc-300 p-3 text-sm text-zinc-800 focus:border-black focus:outline-none resize-none"
                  rows={5}
                  placeholder="Explain why your note should be reconsidered. Describe the content, accuracy, and why the rejection doesn't apply..."
                  value={appealText}
                  onChange={(e) => setAppealText(e.target.value)}
                  maxLength={2000}
                />
                <p className="text-right text-[10px] font-bold uppercase tracking-wider text-zinc-400 mt-1">
                  {appealText.length}/2000 · min 10 chars
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={submitAppeal}
                  disabled={submittingAppeal || appealText.trim().length < 10}
                  className="btn-primary flex-1 text-xs py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submittingAppeal ? "Submitting..." : "Submit Appeal"}
                </button>
                <button onClick={closeModal} className="btn-secondary text-xs px-4">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
