import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios";
import Layout from "../components/Layout";

export default function MyUploads() {
  const [notes, setNotes] = useState([]);

  const fetchMyNotes = async () => {
    try {
      const res = await api.get("/notes/my");
      setNotes(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to load uploads");
    }
  };

  useEffect(() => {
    fetchMyNotes();
  }, []);

  const getStatusColor = (status) => {
    if (status === "approved") return "text-emerald-400";
    if (status === "rejected") return "text-red-400";
    return "text-yellow-400";
  };

  return (
    <Layout title="My Uploads">
      {notes.length === 0 ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <p className="text-zinc-400">No uploads yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {notes.map((n) => (
            <div
              key={n.id}
              className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5"
            >
              <h3 className="text-xl font-semibold">{n.title}</h3>
              <p className="text-zinc-400 mt-2">
                {n.subject} • Unit {n.unit} • Sem {n.semester}
              </p>
              <p className="mt-2">
                Status:{" "}
                <span className={`font-semibold ${getStatusColor(n.status)}`}>
                  {n.status}
                </span>
              </p>

              {n.file_url && (
                <Link
                  to="/viewer"
                  state={{ note: n }}
                  className="inline-block mt-3 text-indigo-400 hover:text-indigo-300"
                >
                  📄 View Note
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
