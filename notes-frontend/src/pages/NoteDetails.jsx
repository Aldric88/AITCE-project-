import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import ReviewModal from "../components/ReviewModal";
import ReportModal from "../components/ReportModal";
import DisputeModal from "../components/DisputeModal";
import Comments from "../components/Comments";
import { checkoutPaidNote } from "../utils/paymentCheckout";
import { getMyAnnotation, upsertMyAnnotation, getSmartStudyPack } from "../api/typedClient";
import { useAuth } from "../auth/AuthContext";

export default function NoteDetails() {
  const { noteId } = useParams();
  const { user, refreshUser } = useAuth();

  const [note, setNote] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [versions, setVersions] = useState([]);
  const [confidence, setConfidence] = useState(null);
  const [studyPack, setStudyPack] = useState(null);
  const [annotation, setAnnotation] = useState("");
  const [annotationSaving, setAnnotationSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState(false);
  const [couponCode, setCouponCode] = useState("");

  const [openReview, setOpenReview] = useState(false);
  const [openReport, setOpenReport] = useState(false);
  const [openDispute, setOpenDispute] = useState(false);

  const fetchDetails = useCallback(async () => {
    try {
      setLoading(true);
      const [noteRes, reviewRes, recRes] = await Promise.all([
        api.get(ENDPOINTS.notes.details(noteId)),
        api.get(ENDPOINTS.reviews.note(noteId)),
        api.get(ENDPOINTS.recommendations.alsoBought(noteId)),
      ]);
      setNote(noteRes.data);
      setReviews(reviewRes.data);
      setRecommendations(recRes.data);
      const [versionRes, confidenceRes, smartRes, annotationRes] = await Promise.allSettled([
        api.get(ENDPOINTS.notes.versions(noteId)),
        api.get(ENDPOINTS.notes.confidence(noteId)),
        getSmartStudyPack(noteId),
        getMyAnnotation(noteId),
      ]);
      if (versionRes.status === "fulfilled") setVersions(versionRes.value.data || []);
      if (confidenceRes.status === "fulfilled") setConfidence(confidenceRes.value.data || null);
      if (smartRes.status === "fulfilled") setStudyPack(smartRes.value || null);
      if (annotationRes.status === "fulfilled") {
        setAnnotation(annotationRes.value?.content || "");
      } else {
        const draft = localStorage.getItem(`note-annotation-draft:${noteId}`);
        if (draft) setAnnotation(draft);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load note details");
    } finally {
      setLoading(false);
    }
  }, [noteId]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const buyNote = async () => {
    if (!note?.id) return;

    try {
      setBuying(true);
      if (note.is_paid) {
        const result = await checkoutPaidNote(note, { couponCode });
        if (result?.alreadyPurchased) {
          toast.success("Already purchased");
        } else {
          toast.success("Purchased");
        }
      } else {
        const res = await api.post(
          ENDPOINTS.purchases.buy(note.id),
          {},
          {
            headers: {
              "X-Idempotency-Key": `${note.id}-${Date.now()}-${crypto.randomUUID()}`,
            },
          },
        );
        toast.success(res.data.paid ? "Purchased" : "Unlocked");
      }
      fetchDetails();
      refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || "Purchase failed");
    } finally {
      setBuying(false);
    }
  };

  const buyNoteWithPoints = async () => {
    if (!note?.id) return;

    try {
      setBuying(true);
      const res = await api.post(
        ENDPOINTS.purchases.buy(note.id),
        { payment_method: "points" },
        {
          headers: {
            "X-Idempotency-Key": `${note.id}-points-${Date.now()}-${crypto.randomUUID()}`,
          },
        },
      );
      toast.success(res.data?.message || "Purchased with points");
      fetchDetails();
      refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || err.message || "Points purchase failed");
    } finally {
      setBuying(false);
    }
  };

  const saveAnnotation = async () => {
    if (!noteId) return;
    try {
      setAnnotationSaving(true);
      await upsertMyAnnotation(noteId, { content: annotation, source: "web" });
      localStorage.removeItem(`note-annotation-draft:${noteId}`);
      toast.success("Annotations synced");
    } catch {
      localStorage.setItem(`note-annotation-draft:${noteId}`, annotation);
      toast.error("Saved locally (offline draft). Sync will be available when network recovers.");
    } finally {
      setAnnotationSaving(false);
    }
  };

  return (
    <Layout title="Note Details">
      {loading ? (
        <div className="border border-black bg-white p-6">
          <Spinner label="Loading note details..." />
        </div>
      ) : !note ? (
        <p className="font-bold uppercase text-gray-500">Note not found.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="panel-depth relative border border-black bg-white p-8 lg:col-span-2">
            <div className="absolute right-0 top-0 h-4 w-4 bg-black" />

            <div className="mb-6 flex items-start justify-between gap-4">
              <h2 className="text-4xl font-black uppercase tracking-tight leading-tight">{note.title}</h2>
              {note.is_paid ? (
                <span className="whitespace-nowrap border border-black bg-black px-3 py-1 text-sm font-bold text-white">INR {note.price}</span>
              ) : (
                <span className="whitespace-nowrap border border-black bg-white px-3 py-1 text-sm font-bold text-black">FREE</span>
              )}
            </div>

            <div className="mb-6 flex flex-wrap gap-2">
              {note.status === "approved" && (
                <span className="border border-green-700 bg-green-50 px-2 py-0.5 text-xs font-bold uppercase text-green-700">Approved</span>
              )}
              {note.verified_seller && (
                <span className="border border-blue-700 bg-blue-50 px-2 py-0.5 text-xs font-bold uppercase text-blue-700">Verified Seller</span>
              )}
              {note.views > 100 && (
                <span className="border border-amber-700 bg-amber-50 px-2 py-0.5 text-xs font-bold uppercase text-amber-700">Popular</span>
              )}
            </div>

            <p className="mb-6 border-l-4 border-black pl-4 text-lg leading-relaxed text-gray-600">
              {note.description || "No description available for this note."}
            </p>

            <div className="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-6 text-xs font-bold uppercase tracking-wide">
              <span className="border border-gray-300 px-2 py-1 text-gray-500">{note.dept}</span>
              <span className="border border-gray-300 px-2 py-1 text-gray-500">Sem {note.semester}</span>
              <span className="border border-gray-300 px-2 py-1 text-gray-500">{note.subject}</span>
              <span className="border border-gray-300 px-2 py-1 text-gray-500">Unit {note.unit}</span>
            </div>

            <div className="mb-6 flex items-center gap-6">
              <div>
                <span className="block text-lg font-black leading-none text-black">{note.avg_rating}</span>
                <span className="text-xs font-bold uppercase text-gray-400">{note.review_count} reviews</span>
              </div>
              <div>
                <span className="block text-lg font-black leading-none text-black">{note.views}</span>
                <span className="text-xs font-bold uppercase text-gray-400">views</span>
              </div>
              <div>
                <span className="block text-lg font-black leading-none text-black">{note.downloads}</span>
                <span className="text-xs font-bold uppercase text-gray-400">downloads</span>
              </div>
            </div>

            {confidence && (
              <div className="mb-6 border border-zinc-200 bg-zinc-50 p-4">
                <p className="text-xs font-black uppercase tracking-[0.2em] text-zinc-600">Buyer Confidence</p>
                <p className="mt-2 text-2xl font-black uppercase tracking-tight text-black">{confidence.confidence_score}/100</p>
                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                  Badge: {confidence.badge} • Verified buyers: {confidence.verified_buyers} • Duplicates: {confidence.duplicate_count}
                </p>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button onClick={() => setOpenReview(true)} className="btn-secondary px-4 py-2 text-xs">
                Review
              </button>
              <button onClick={() => setOpenReport(true)} className="btn-secondary px-4 py-2 text-xs">
                Report
              </button>
              {note.is_paid && note.has_access && (
                <button onClick={() => setOpenDispute(true)} className="btn-secondary border-red-300 px-4 py-2 text-xs text-red-700 hover:bg-red-50">
                  Dispute
                </button>
              )}
            </div>

            <div className="mt-8 border border-black bg-white">
              {note.has_access || !note.is_paid ? (
                <iframe
                  title="Secure Viewer"
                  src={`${API_BASE_URL}/preview/${noteId}`}
                  className="w-full"
                  style={{ height: "600px" }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center bg-gray-50 p-8 text-center">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center border-2 border-black bg-white">
                    <svg className="h-8 w-8 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <h3 className="mb-2 text-xl font-black uppercase tracking-tight text-black">Content Locked</h3>
                  <p className="mb-1 max-w-sm text-sm text-gray-500">
                    Purchase this note to unlock the secure viewer.
                  </p>
                  <p className="mb-5 text-xs font-bold uppercase tracking-wider text-zinc-500">
                    Price: <span className="text-black">₹{note.price}</span> · Your wallet: <span className="text-black">{user?.wallet_points ?? 0} pts</span>
                  </p>
                  <input
                    className="input-surface mb-4 max-w-xs w-full"
                    placeholder="Coupon code (optional)"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  />
                  <div className="flex flex-wrap justify-center gap-3">
                    <button
                      onClick={buyNoteWithPoints}
                      disabled={buying || (user?.wallet_points ?? 0) < (note?.price ?? 0)}
                      className="btn-secondary disabled:opacity-40 disabled:cursor-not-allowed"
                      title={(user?.wallet_points ?? 0) < (note?.price ?? 0) ? "Not enough points" : ""}
                    >
                      {buying ? "Processing..." : `Use ${note.price} Points`}
                    </button>
                    <button
                      onClick={buyNote}
                      disabled={buying}
                      className="btn-primary"
                    >
                      {buying ? "Processing..." : `Pay ₹${note.price} (Demo)`}
                    </button>
                  </div>
                  <p className="mt-3 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                    Demo mode: INR payment is simulated — no real charge
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="border border-black bg-white p-6">
              <h3 className="mb-4 border-b border-black pb-2 text-lg font-black uppercase tracking-wide">Reviews</h3>

              {reviews.length === 0 ? (
                <p className="text-sm text-gray-400">No reviews yet.</p>
              ) : (
                <div className="space-y-4">
                  {reviews.map((r) => (
                    <div key={r.id} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                      <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm font-bold text-black">Rating: {r.rating}</div>
                        {r.verified_purchase && <span className="border border-black px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">Verified</span>}
                      </div>

                      <p className="text-sm text-gray-600">"{r.comment}"</p>
                      <p className="mt-2 text-xs font-medium uppercase text-gray-400">{r.user_name || "User"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border border-black bg-white p-6">
              <h3 className="mb-4 border-b border-black pb-2 text-lg font-black uppercase tracking-wide">Also Bought</h3>

              {recommendations.length === 0 ? (
                <p className="text-sm text-gray-400">No recommendations yet</p>
              ) : (
                <div className="space-y-3">
                  {recommendations.map((rec) => (
                    <Link key={rec.id} to={`/notes/${rec.id}`} className="group block border border-transparent p-3 transition-all hover:border-black hover:bg-gray-50">
                      <h4 className="line-clamp-1 text-sm font-bold text-black group-hover:underline">{rec.title}</h4>
                      <div className="mt-1 flex items-center justify-between">
                        <p className="text-xs font-bold uppercase text-gray-500">
                          {rec.dept} • Sem {rec.semester}
                        </p>
                        <span className="text-xs font-bold">{rec.is_paid ? `INR ${rec.price}` : "FREE"}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <div className="border border-black bg-white p-6">
              <h3 className="mb-4 border-b border-black pb-2 text-lg font-black uppercase tracking-wide">Version History</h3>
              {versions.length === 0 ? (
                <p className="text-sm text-gray-400">No versions published yet.</p>
              ) : (
                <div className="space-y-3">
                  {versions.map((v) => (
                    <div key={v.id} className="border border-zinc-200 p-3">
                      <p className="text-xs font-black uppercase tracking-wider text-black">Version {v.version_no}</p>
                      <p className="mt-1 text-xs text-zinc-600">{v.changelog || "No changelog provided."}</p>
                      <p className="mt-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">{new Date(v.created_at * 1000).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {studyPack && (
              <div className="border border-black bg-white p-6">
                <h3 className="mb-4 border-b border-black pb-2 text-lg font-black uppercase tracking-wide">Smart Study Pack</h3>
                <p className="text-sm text-zinc-700">{studyPack.summary}</p>
                {Array.isArray(studyPack.key_points) && studyPack.key_points.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {studyPack.key_points.slice(0, 6).map((kp) => (
                      <span key={kp} className="border border-zinc-200 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-zinc-600">
                        {kp}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="border border-black bg-white p-6">
              <h3 className="mb-4 border-b border-black pb-2 text-lg font-black uppercase tracking-wide">My Annotations</h3>
              <textarea
                className="w-full border border-zinc-300 p-3 text-sm text-zinc-700 focus:border-black focus:outline-none"
                rows={6}
                value={annotation}
                onChange={(e) => setAnnotation(e.target.value)}
                placeholder="Write your personal summary, doubts, and quick revision notes..."
              />
              <div className="mt-3 flex justify-end">
                <button onClick={saveAnnotation} disabled={annotationSaving} className="btn-secondary px-4 py-2 text-xs">
                  {annotationSaving ? "Saving..." : "Sync Notes"}
                </button>
              </div>
            </div>

            <div className="border border-black bg-white p-6">
              <Comments noteId={noteId} />
            </div>
          </div>

          <ReviewModal open={openReview} note={note} onClose={() => setOpenReview(false)} onSuccess={() => fetchDetails()} />
          <ReportModal open={openReport} note={note} onClose={() => setOpenReport(false)} />
          <DisputeModal open={openDispute} note={note} onClose={() => setOpenDispute(false)} />
        </div>
      )}
    </Layout>
  );
}
