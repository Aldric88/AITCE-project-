import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import ReviewModal from "../components/ReviewModal";
import ReportModal from "../components/ReportModal";
import DisputeModal from "../components/DisputeModal";

export default function NoteDetails() {
  const { noteId } = useParams();

  const [note, setNote] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);

  const [openReview, setOpenReview] = useState(false);
  const [openReport, setOpenReport] = useState(false);
  const [openDispute, setOpenDispute] = useState(false);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      const [noteRes, reviewRes] = await Promise.all([
        api.get(`/notes/${noteId}/details`),
        api.get(`/reviews/note/${noteId}`),
      ]);
      setNote(noteRes.data);
      setReviews(reviewRes.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load note details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [noteId]);

  return (
    <Layout title="Note Details">
      {loading ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <Spinner label="Loading note details..." />
        </div>
      ) : !note ? (
        <p className="text-zinc-400">Note not found.</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* LEFT: note info */}
          <div className="lg:col-span-2 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-3xl font-bold">{note.title}</h2>
                <p className="text-zinc-400 mt-2">{note.description || "No description"}</p>

                <div className="mt-4 flex flex-wrap gap-2 text-sm">
                  <span className="px-3 py-1 rounded-full bg-zinc-800">
                    {note.dept}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-zinc-800">
                    Sem {note.semester}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-zinc-800">
                    {note.subject}
                  </span>
                  <span className="px-3 py-1 rounded-full bg-zinc-800">
                    Unit {note.unit}
                  </span>
                </div>

                <div className="mt-4 text-zinc-300">
                  ⭐ <b>{note.avg_rating}</b> ({note.review_count} reviews) • ❤️ {note.likes} likes
                </div>
              </div>

              {/* PRICE badge */}
              {note.is_paid ? (
                <span className="text-xs px-3 py-1 rounded-full bg-yellow-600/30 text-yellow-200 border border-yellow-500/30">
                  PAID ₹{note.price}
                </span>
              ) : (
                <span className="text-xs px-3 py-1 rounded-full bg-emerald-600/20 text-emerald-200 border border-emerald-500/30">
                  FREE
                </span>
              )}
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={() => setOpenReview(true)}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition"
              >
                ✍️ Add Review
              </button>

              <button
                onClick={() => setOpenReport(true)}
                className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
              >
                🚩 Report
              </button>

              {note.is_paid && note.has_access && (
                <button
                  onClick={() => setOpenDispute(true)}
                  className="px-4 py-2 rounded-xl bg-yellow-500 hover:bg-yellow-400 transition text-zinc-950 font-semibold"
                >
                  🧾 Raise Dispute
                </button>
              )}
            </div>

            {/* Secure Viewer */}
            <div className="mt-6 rounded-xl border border-zinc-800 overflow-hidden">
              {note.has_access || !note.is_paid ? (
                <iframe
                  title="Secure Viewer"
                  src={""}
                  className="hidden"
                />
              ) : (
                <div className="p-5 text-zinc-400">
                  🔒 This note is locked. Buy it from Dashboard to view.
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: reviews */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
            <h3 className="text-xl font-semibold mb-4">Reviews</h3>

            {reviews.length === 0 ? (
              <p className="text-zinc-400">No reviews yet.</p>
            ) : (
              <div className="space-y-3">
                {reviews.map((r) => (
                  <div
                    key={r.id}
                    className="rounded-xl border border-zinc-800 bg-zinc-950 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-yellow-300 font-semibold">
                        ⭐ {r.rating}
                      </div>

                      {r.verified_purchase && (
                        <span className="text-xs px-2 py-1 rounded-full bg-emerald-600/20 text-emerald-200 border border-emerald-500/30">
                          ✅ Verified Purchase
                        </span>
                      )}
                    </div>

                    <p className="text-zinc-300 mt-2">
                      {r.comment || "No comment"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Modals */}
          <ReviewModal
            open={openReview}
            note={note}
            onClose={() => setOpenReview(false)}
            onSuccess={() => fetchDetails()}
          />

          <ReportModal
            open={openReport}
            note={note}
            onClose={() => setOpenReport(false)}
          />

          <DisputeModal
            open={openDispute}
            note={note}
            onClose={() => setOpenDispute(false)}
          />
        </div>
      )}
    </Layout>
  );
}
