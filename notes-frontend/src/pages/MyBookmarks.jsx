import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api/axios";
import Layout from "../components/Layout";

export default function MyBookmarks() {
  const [bookmarks, setBookmarks] = useState([]);

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        const res = await api.get("/bookmarks/my");
        if (active) setBookmarks(res.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load bookmarks");
      }
    };

    run();
    return () => {
      active = false;
    };
  }, []);

  const removeBookmark = async (noteId) => {
    try {
      await api.delete(`/bookmarks/${noteId}`);
      setBookmarks((prev) => prev.filter((b) => b.note.id !== noteId));
      toast.success("Bookmark removed");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Remove failed");
    }
  };

  return (
    <Layout title="My Bookmarks">
      <div className="mx-auto max-w-5xl space-y-8">
        {bookmarks.length === 0 ? (
          <div className="border border-gray-200 bg-white p-16 text-center">
            <h3 className="mb-2 text-sm font-black uppercase tracking-[0.2em] text-zinc-800">No Bookmarks</h3>
            <p className="mx-auto mb-8 max-w-sm text-xs font-medium leading-relaxed text-zinc-500">
              Save notes to build your personal collection.
            </p>
            <Link to="/trending" className="btn-secondary text-xs">
              Browse Trending
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {bookmarks.map((b) => (
              <div key={b.bookmark_id} className="minimal-card p-8">
                <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
                  <div>
                    <h3 className="text-2xl font-black uppercase tracking-tight text-zinc-900">{b.note.title}</h3>
                    <p className="mt-2 text-xs font-bold uppercase tracking-wide text-zinc-500">
                      {b.note.subject} • Unit {b.note.unit} • Semester {b.note.semester}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    {b.note.file_url && (
                      <Link to="/viewer" state={{ note: b.note }} className="btn-primary text-xs">
                        Open Note
                      </Link>
                    )}

                    <button onClick={() => removeBookmark(b.note.id)} className="btn-secondary border-red-300 text-red-700 hover:bg-red-50 text-xs">
                      Remove
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
