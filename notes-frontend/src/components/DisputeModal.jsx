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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="border border-black bg-white p-6 w-full max-w-md shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        <h3 className="text-xl font-black uppercase tracking-wide mb-4 text-black">Raise Dispute</h3>
        <p className="text-gray-500 font-bold uppercase tracking-wide text-xs mb-2 border-b border-gray-100 pb-2">{note.title}</p>
        <p className="text-gray-400 text-xs mb-6 font-medium">
          This will notify the admin about issues with this note.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Message */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
              Dispute Reason
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="w-full p-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none text-black"
              placeholder="Please describe the issue with this note..."
              required
            />
          </div>

          {/* Warning */}
          <div className="border border-yellow-600 bg-yellow-50 p-3">
            <p className="text-yellow-800 text-xs font-bold">
              ⚠️ Disputes are reviewed by administrators. False disputes may affect your account.
            </p>
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
              className="px-6 py-2 bg-yellow-400 text-black border border-black hover:bg-yellow-300 transition disabled:opacity-50 disabled:cursor-not-allowed font-bold uppercase text-sm tracking-wide"
            >
              {loading ? "Submitting..." : "Submit Dispute"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
