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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 w-full max-w-md">
        <h3 className="text-xl font-semibold mb-4">Add Review</h3>
        <p className="text-zinc-400 mb-4">{note.title}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Star Rating */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Rating
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  className={`text-2xl transition ${
                    star <= rating ? "text-yellow-400" : "text-zinc-600"
                  } hover:text-yellow-300`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>

          {/* Comment */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Comment (optional)
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-100 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Share your experience with this note..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Submitting..." : "Submit Review"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
