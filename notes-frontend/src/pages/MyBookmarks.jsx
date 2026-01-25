import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios";
import Layout from "../components/Layout";

export default function MyBookmarks() {
  const [bookmarks, setBookmarks] = useState([]);

  const fetchBookmarks = async () => {
    try {
      const res = await api.get("/bookmarks/my");
      setBookmarks(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to load bookmarks");
    }
  };

  const removeBookmark = async (noteId) => {
    try {
      await api.delete(`/bookmarks/${noteId}`);
      alert("Bookmark removed ✅");
      fetchBookmarks();
    } catch (err) {
      alert(err.response?.data?.detail || "Remove failed");
    }
  };

  useEffect(() => {
    fetchBookmarks();
  }, []);

  return (
    <Layout title="My Bookmarks">
      {bookmarks.length === 0 ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <p className="text-zinc-400">No bookmarks yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {bookmarks.map((b) => (
            <div
              key={b.bookmark_id}
              className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5"
            >
              <h3 className="text-xl font-semibold">{b.note.title}</h3>
              <p className="text-zinc-400 mt-2">
                {b.note.subject} • Unit {b.note.unit} • Sem {b.note.semester}
              </p>

              <div className="mt-4 flex flex-wrap gap-3">
                {b.note.file_url && (
                  <Link
                    to="/viewer"
                    state={{ note: b.note }}
                    className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
                  >
                    📄 View Note
                  </Link>
                )}

                <button
                  onClick={() => removeBookmark(b.note.id)}
                  className="px-4 py-2 rounded-xl bg-red-600/80 hover:bg-red-500 transition"
                >
                  Remove Bookmark
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
