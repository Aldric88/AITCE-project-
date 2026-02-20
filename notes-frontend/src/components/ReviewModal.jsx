import { useState } from "react";
import api from "../api/axios";
import toast from "react-hot-toast";

export default function ReviewModal({ open, note, onClose, onSuccess }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!note) return;

    try {
      setLoading(true);
      await api.post(`/reviews/note/${note.id}`, {
        rating,
        comment: comment.trim() || undefined,
      });

      toast.success("Review added ✅");
      onSuccess();
      onClose();
      setRating(5);
      setComment("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add review");
    } finally {
      setLoading(false);
    }
  };

  if (!open || !note) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="border border-black bg-white p-6 w-full max-w-md shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        <h3 className="text-xl font-black uppercase tracking-wide mb-4 text-black">Add Review</h3>
        <p className="text-gray-500 font-bold uppercase tracking-wide text-xs mb-6 border-b border-gray-100 pb-2">{note.title}</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Star Rating */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
              Rating
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  className={`text-3xl transition-colors ${star <= rating ? "text-yellow-400" : "text-gray-200"
                    } hover:text-yellow-500`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>

          {/* Comment */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
              Comment (optional)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full p-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none text-black"
              placeholder="Share your experience with this note..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 border border-black text-black bg-white hover:bg-gray-100 transition font-bold uppercase text-sm tracking-wide"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-black text-white border border-black hover:bg-neutral-800 transition disabled:opacity-50 disabled:cursor-not-allowed font-bold uppercase text-sm tracking-wide"
            >
              {loading ? "Submitting..." : "Submit Review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
