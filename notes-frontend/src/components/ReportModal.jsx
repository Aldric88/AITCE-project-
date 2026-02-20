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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="border border-black bg-white p-6 w-full max-w-md shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        <h3 className="text-xl font-black uppercase tracking-wide mb-4 text-black">Report Note</h3>
        <p className="text-gray-500 font-bold uppercase tracking-wide text-xs mb-6 border-b border-gray-100 pb-2">{note.title}</p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Reason */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
              Reason
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full p-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none text-black appearance-none"
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
            <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
              Additional Details
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              className="w-full p-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none text-black"
              placeholder="Please provide more details about your report..."
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
              className="px-6 py-2 bg-red-600 text-white border border-red-600 hover:bg-red-500 transition disabled:opacity-50 disabled:cursor-not-allowed font-bold uppercase text-sm tracking-wide"
            >
              {loading ? "Submitting..." : "Submit Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
