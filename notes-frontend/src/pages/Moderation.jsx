import { useEffect, useState } from "react";
import api from "../api/axios";
import Layout from "../components/Layout";
import { useAuth } from "../auth/AuthContext";

export default function Moderation() {
  const { user } = useAuth();
  const [pending, setPending] = useState([]);
  const [reasonMap, setReasonMap] = useState({});

  const fetchPending = async () => {
    try {
      const res = await api.get("/notes/pending");
      setPending(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to load pending notes");
    }
  };

  const moderate = async (noteId, status) => {
    try {
      const reason = reasonMap[noteId] || "";

      await api.patch(`/notes/${noteId}/moderate`, {
        status,
        reason,
      });

      alert(`Note ${status} ✅`);
      fetchPending();
    } catch (err) {
      alert(err.response?.data?.detail || "Moderation failed");
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  if (!user || (user.role !== "admin" && user.role !== "moderator")) {
    return (
      <Layout title="Moderation">
        <p className="text-zinc-400">❌ You are not authorized to access this page.</p>
      </Layout>
    );
  }

  return (
    <Layout title="Moderation">
      <h2 className="text-2xl font-semibold mb-4">Pending Notes</h2>

      {pending.length === 0 ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <p className="text-zinc-400">✅ No pending notes right now.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pending.map((n) => (
            <div
              key={n.id}
              className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5"
            >
              <h3 className="text-xl font-semibold">{n.title}</h3>
              <p className="text-zinc-400 mt-2">
                {n.dept} • {n.subject} • Unit {n.unit} • Sem {n.semester}
              </p>

              {n.file_url && (
                <a
                  href={`http://127.0.0.1:8001${n.file_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block mt-3 text-indigo-400 hover:text-indigo-300"
                >
                  📄 View File
                </a>
              )}

              <div className="mt-4">
                <input
                  placeholder="Reason (optional)"
                  value={reasonMap[n.id] || ""}
                  onChange={(e) =>
                    setReasonMap((p) => ({ ...p, [n.id]: e.target.value }))
                  }
                  className="w-full max-w-md px-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
                />
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  onClick={() => moderate(n.id, "approved")}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 transition"
                >
                  ✅ Approve
                </button>
                <button
                  onClick={() => moderate(n.id, "rejected")}
                  className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 transition"
                >
                  ❌ Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
