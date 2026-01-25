import { useState } from "react";
import api from "../api/axios";
import toast from "react-hot-toast";

export default function ReportModal({ open, note, onClose }) {
  const [reason, setReason] = useState("spam");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!note) return;

    try {
      setLoading(true);
      await api.post(`/reports/note/${note.id}`, {
        reason,
        message: message.trim() || undefined,
      });

      toast.success("Report submitted ✅");
      onClose();
      setReason("spam");
      setMessage("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit report");
    } finally {
      setLoading(false);
    }
  };

  if (!open || !note) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900 p-6 w-full max-w-md">
        <h3 className="text-xl font-semibold mb-4">Report Note</h3>
        <p className="text-zinc-400 mb-4">{note.title}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Reason
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-100 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="spam">Spam</option>
              <option value="fake">Fake Content</option>
              <option value="misleading">Misleading</option>
              <option value="copyright">Copyright Violation</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Additional Details
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-100 p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Please provide more details about your report..."
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
              className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Submitting..." : "Submit Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
