import { useState } from "react";
import api from "../api/axios";
import toast from "react-hot-toast";

export default function DisputeModal({ open, note, onClose }) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!note) return;

    if (!message.trim()) {
      toast.error("Please provide a dispute reason");
      return;
    }

    try {
      setLoading(true);
      await api.post(`/disputes/note/${note.id}`, {
        message: message.trim(),
      });

      toast.success("Dispute submitted ✅");
      onClose();
      setMessage("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit dispute");
    } finally {
      setLoading(false);
    }
  };

  if (!open || !note) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 w-full max-w-md">
        <h3 className="text-xl font-semibold mb-4">Raise Dispute</h3>
        <p className="text-zinc-400 mb-4">{note.title}</p>
        <p className="text-zinc-500 text-sm mb-6">
          This will notify the admin about issues with this note.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Dispute Reason
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-100 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Please describe the issue with this note..."
              required
            />
          </div>

          {/* Warning */}
          <div className="rounded-lg border border-yellow-600/30 bg-yellow-600/10 p-3">
            <p className="text-yellow-300 text-sm">
              ⚠️ Disputes are reviewed by administrators. False disputes may affect your account.
            </p>
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
              className="px-4 py-2 rounded-lg bg-yellow-600 text-zinc-900 hover:bg-yellow-500 transition disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
            >
              {loading ? "Submitting..." : "Submit Dispute"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
