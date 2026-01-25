import { useEffect, useMemo, useState } from "react";
import api from "../api/axios";
import Layout from "../components/Layout";
import NoteCard from "../components/NoteCard";
import Spinner from "../components/Spinner";
import toast from "react-hot-toast";

export default function Dashboard() {
  const [notes, setNotes] = useState([]);
  const [likeCounts, setLikeCounts] = useState({});
  const [bookmarkedSet, setBookmarkedSet] = useState(new Set());

  const [accessMap, setAccessMap] = useState({}); // ✅ noteId -> true/false

  const [downloadingMap, setDownloadingMap] = useState({}); // noteId -> true/false
  const [buyingMap, setBuyingMap] = useState({});          // noteId -> true/false
  const [bookmarkingMap, setBookmarkingMap] = useState({}); // noteId -> true/false
  const [likedSet, setLikedSet] = useState(new Set());
  const [likingMap, setLikingMap] = useState({});

  const [loadingNotes, setLoadingNotes] = useState(false);
  const [loadingBookmarks, setLoadingBookmarks] = useState(false);

  // ✅ Filters
  const [filters, setFilters] = useState({
    dept: "",
    semester: "",
    subject: "",
    search: "",
  });

  const fetchLikeCount = async (noteId) => {
    try {
      const res = await api.get(`/likes/${noteId}/count`);
      setLikeCounts((p) => ({ ...p, [noteId]: res.data.likes }));
    } catch {}
  };

  const fetchAccess = async (noteId) => {
    try {
      const res = await api.get(`/purchases/${noteId}/has-access`);
      setAccessMap((p) => ({ ...p, [noteId]: res.data.has_access }));
    } catch {
      // if fails, assume locked for safety
      setAccessMap((p) => ({ ...p, [noteId]: false }));
    }
  };

  const fetchBookmarks = async () => {
    setLoadingBookmarks(true);
    try {
      const res = await api.get("/bookmarks/my");
      const ids = new Set(res.data.map((b) => b.note?.id).filter(Boolean));
      setBookmarkedSet(ids);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load bookmarks");
    } finally {
      setLoadingBookmarks(false);
    }
  };

  const fetchMyLikes = async () => {
    try {
      const res = await api.get("/likes/my");
      setLikedSet(new Set(res.data));
    } catch {}
  };

  const fetchNotes = async () => {
    setLoadingNotes(true);
    try {
      const params = {};

      if (filters.dept) params.dept = filters.dept;
      if (filters.semester) params.semester = Number(filters.semester);
      if (filters.subject) params.subject = filters.subject;

      const res = await api.get("/notes/", { params });
      setNotes(res.data);

      res.data.forEach((n) => {
        fetchLikeCount(n.id);

        // ✅ check paid access for paid notes
        if (n.is_paid) fetchAccess(n.id);
        else setAccessMap((p) => ({ ...p, [n.id]: true }));
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load notes");
    } finally {
      setLoadingNotes(false);
    }
  };

  const toggleLike = async (noteId) => {
    try {
      setLikingMap((p) => ({ ...p, [noteId]: true }));

      if (likedSet.has(noteId)) {
        await api.delete(`/likes/${noteId}`);
        toast.success("Unliked ✅");
      } else {
        await api.post(`/likes/${noteId}`);
        toast.success("Liked ✅");
      }

      await fetchMyLikes();
      fetchLikeCount(noteId);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Like action failed");
    } finally {
      setLikingMap((p) => ({ ...p, [noteId]: false }));
    }
  };

  const bookmarkNote = async (noteId) => {
    try {
      setBookmarkingMap((p) => ({ ...p, [noteId]: true }));

      if (bookmarkedSet.has(noteId)) {
        await api.delete(`/bookmarks/${noteId}`);
        toast.success("Bookmark removed ✅");
      } else {
        await api.post(`/bookmarks/${noteId}`);
        toast.success("Bookmarked ✅");
      }

      await fetchBookmarks();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Bookmark action failed");
    } finally {
      setBookmarkingMap((p) => ({ ...p, [noteId]: false }));
    }
  };

  const buyNote = async (note) => {
    try {
      setBuyingMap((p) => ({ ...p, [note.id]: true }));

      toast.loading("Processing purchase...", { id: `buy-${note.id}` });

      await api.post(`/purchases/${note.id}/buy`);

      toast.success("Purchased ✅", { id: `buy-${note.id}` });

      // refresh access + notes
      await fetchNotes();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Purchase failed", {
        id: `buy-${note.id}`,
      });
    } finally {
      setBuyingMap((p) => ({ ...p, [note.id]: false }));
    }
  };

  const downloadNote = async (note) => {
    try {
      toast.loading("Downloading...", { id: "dl" });

      const res = await api.get(`/secure/note/${note.id}/download`, {
        responseType: "blob",
      });

      const blob = new Blob([res.data]);
      const blobUrl = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = blobUrl;

      // ✅ best filename
      const ext = note.file_ext ? note.file_ext.replace(".", "") : "file";
      a.download = `${note.title.replaceAll(" ", "_")}.${ext}`;

      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(blobUrl);

      toast.success("Downloaded ✅", { id: "dl" });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Download failed", { id: "dl" });
    }
  };

  // ✅ local search (title + subject + tags)
  const filteredNotes = useMemo(() => {
    const q = filters.search.toLowerCase().trim();
    if (!q) return notes;

    return notes.filter((n) => {
      const title = (n.title || "").toLowerCase();
      const subject = (n.subject || "").toLowerCase();
      const tags = (n.tags || []).join(" ").toLowerCase();

      return (
        title.includes(q) ||
        subject.includes(q) ||
        tags.includes(q)
      );
    });
  }, [notes, filters.search]);

  useEffect(() => {
    fetchBookmarks();
    fetchMyLikes();
    fetchNotes();
  }, []);

  // refresh when filter changes (dept/semester/subject)
  useEffect(() => {
    fetchNotes();
  }, [filters.dept, filters.semester, filters.subject]);

  return (
    <Layout title="Dashboard">
      {/* Filters */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 mb-6">
        <h2 className="text-lg font-semibold mb-4">Search & Filters</h2>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800"
            placeholder="Search by title..."
            value={filters.search}
            onChange={(e) =>
              setFilters((p) => ({ ...p, search: e.target.value }))
            }
          />

          <select
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800"
            value={filters.dept}
            onChange={(e) => setFilters((p) => ({ ...p, dept: e.target.value }))}
          >
            <option value="">All Depts</option>
            <option value="CSE">CSE</option>
            <option value="ECE">ECE</option>
            <option value="MECH">MECH</option>
          </select>

          <select
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800"
            value={filters.semester}
            onChange={(e) =>
              setFilters((p) => ({ ...p, semester: e.target.value }))
            }
          >
            <option value="">All Sem</option>
            <option value="1">Sem 1</option>
            <option value="2">Sem 2</option>
            <option value="3">Sem 3</option>
            <option value="4">Sem 4</option>
            <option value="5">Sem 5</option>
            <option value="6">Sem 6</option>
            <option value="7">Sem 7</option>
            <option value="8">Sem 8</option>
          </select>

          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800"
            placeholder="Subject (ex: DBMS)"
            value={filters.subject}
            onChange={(e) =>
              setFilters((p) => ({ ...p, subject: e.target.value }))
            }
          />
        </div>

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => {
              setFilters({ dept: "", semester: "", subject: "", search: "" });
              toast.success("Filters cleared ✅");
            }}
            className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
          >
            Clear Filters
          </button>

          <button
            onClick={() => {
              fetchNotes();
              fetchBookmarks();
              toast.success("Refreshed ✅");
            }}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Notes */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-semibold">Approved Notes</h2>

        {(loadingNotes || loadingBookmarks) && (
          <Spinner label="Updating notes..." />
        )}
      </div>

      {loadingNotes ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
          <Spinner label="Fetching approved notes..." />
        </div>
      ) : filteredNotes.length === 0 ? (
        <p className="text-zinc-400">No notes found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {filteredNotes.map((n) => (
            <div key={n.id} className="relative">
              {/* Bookmark badge */}
              {bookmarkedSet.has(n.id) && (
                <div className="absolute -top-2 -right-2 text-xs bg-emerald-600 px-3 py-1 rounded-full shadow">
                  Bookmarked
                </div>
              )}

              <NoteCard
                note={n}
                likeCount={likeCounts[n.id] || 0}
                hasAccess={accessMap[n.id] ?? !n.is_paid}

                onBuy={() => buyNote(n)}
                isBuying={!!buyingMap[n.id]}

                onDownload={() => downloadNote(n)}
                isDownloading={!!downloadingMap[n.id]}

                onLike={() => toggleLike(n.id)}
                isLiked={likedSet.has(n.id)}
                isLiking={!!likingMap[n.id]}

                onBookmark={() => bookmarkNote(n.id)}
                isBookmarked={bookmarkedSet.has(n.id)}
                isBookmarking={!!bookmarkingMap[n.id]}

                // optional: allow download only for doc/ppt
                allowDownload={true}
              />
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
