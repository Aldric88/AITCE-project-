import { useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { normalizeLibraryRecord } from "../api/normalizers";
import { cachedGet, invalidateGet } from "../api/queryCache";
import { getMyLibrary } from "../api/typedClient";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import { Link } from "react-router-dom";
import jsPDF from "jspdf";

const LIBRARY_CACHE_KEY = "notes_market:library_cache:v1";

export default function MyLibrary() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [offlineMode, setOfflineMode] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState(null);

  // ✅ search + grouping + sorting + filters
  const [query, setQuery] = useState("");
  const [groupBy, setGroupBy] = useState("subject"); // subject | unit | none
  const [typeFilter, setTypeFilter] = useState("all"); // all | free | paid
  const [sortBy, setSortBy] = useState("newest"); // newest | oldest | price_high | price_low | free_first
  const [bookmarkedIds, setBookmarkedIds] = useState([]);
  const [showBookmarkedOnly, setShowBookmarkedOnly] = useState(false);

  const fetchLibrary = async () => {
    try {
      setLoading(true);
      const rows = await getMyLibrary();
      const normalized = (rows || []).map((row) => normalizeLibraryRecord(row));
      setNotes(normalized);
      setOfflineMode(false);
      const syncedAt = Date.now();
      setLastSyncedAt(syncedAt);
      localStorage.setItem(
        LIBRARY_CACHE_KEY,
        JSON.stringify({
          synced_at: syncedAt,
          rows,
        }),
      );
    } catch (err) {
      const cachedRaw = localStorage.getItem(LIBRARY_CACHE_KEY);
      if (cachedRaw) {
        try {
          const cached = JSON.parse(cachedRaw);
          const cachedRows = Array.isArray(cached?.rows) ? cached.rows : [];
          setNotes(cachedRows.map((row) => normalizeLibraryRecord(row)));
          setLastSyncedAt(cached?.synced_at || null);
          setOfflineMode(true);
          toast.error("Network unavailable. Loaded offline library cache.");
        } catch {
          toast.error(err.response?.data?.detail || "Failed to load library");
        }
      } else {
        toast.error(err.response?.data?.detail || "Failed to load library");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadBookmarks = async () => {
    try {
      const res = await cachedGet(ENDPOINTS.bookmarks.mine, { ttlMs: 10000 });
      setBookmarkedIds(res.data.note_ids || []);
    } catch {
      setBookmarkedIds([]);
    }
  };

  useEffect(() => {
    fetchLibrary();
    loadBookmarks();
  }, []);

  // Listen for bookmark updates
  useEffect(() => {
    const handler = () => loadBookmarks();
    window.addEventListener("bookmarks_updated", handler);
    return () => window.removeEventListener("bookmarks_updated", handler);
  }, []);

  const downloadFree = async (note) => {
    try {
      const res = await api.get(ENDPOINTS.downloads.note(note.note_id), {
        responseType: "blob",
      });

      const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `${note.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);

      toast.success("Downloaded ✅");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Download failed");
    }
  };

  const exportPDF = () => {
    const doc = new jsPDF();

    // ✅ decide export list
    const exportList = showBookmarkedOnly
      ? sortedNotes.filter((n) => bookmarkedIds.includes(n.note_id))
      : sortedNotes;

    doc.setFontSize(16);
    doc.text(showBookmarkedOnly ? "⭐ Bookmarked Notes" : "📚 My Notes Library", 14, 15);

    doc.setFontSize(11);
    let y = 25;

    exportList.forEach((n, idx) => {
      const line = `${idx + 1}. ${n.title} | ${n.subject} | Unit ${n.unit} | ${n.is_paid ? `Paid ₹${n.price}` : "Free"
        }`;

      doc.text(line.slice(0, 95), 14, y);
      y += 8;

      if (y > 280) {
        doc.addPage();
        y = 20;
      }
    });

    const fileName = showBookmarkedOnly ? "bookmarked-notes.pdf" : "my-library.pdf";
    doc.save(fileName);

    toast.success("Exported PDF ✅");
  };

  // ✅ Step 1: search filter
  const searchedNotes = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return notes;

    return notes.filter((n) => {
      const title = (n.title || "").toLowerCase();
      const subject = (n.subject || "").toLowerCase();
      const unit = String(n.unit || "").toLowerCase();
      const dept = (n.dept || "").toLowerCase();
      const desc = (n.description || "").toLowerCase();

      return (
        title.includes(q) ||
        subject.includes(q) ||
        unit.includes(q) ||
        dept.includes(q) ||
        desc.includes(q)
      );
    });
  }, [notes, query]);

  // ✅ Step 2: free/paid filter
  const filteredNotes = useMemo(() => {
    if (typeFilter === "all") return searchedNotes;
    if (typeFilter === "free") return searchedNotes.filter((n) => !n.is_paid);
    if (typeFilter === "paid") return searchedNotes.filter((n) => n.is_paid);
    return searchedNotes;
  }, [searchedNotes, typeFilter]);

  // ✅ Step 3: sorting
  const sortedNotes = useMemo(() => {
    let arr = [...filteredNotes];

    // ✅ show only bookmarked
    if (showBookmarkedOnly) {
      arr = arr.filter((n) => bookmarkedIds.includes(n.note_id));
    }

    const safeNum = (v) => (typeof v === "number" ? v : Number(v || 0));

    if (sortBy === "newest") {
      arr.sort((a, b) => safeNum(b.unlocked_at) - safeNum(a.unlocked_at));
    } else if (sortBy === "oldest") {
      arr.sort((a, b) => safeNum(a.unlocked_at) - safeNum(b.unlocked_at));
    } else if (sortBy === "price_high") {
      arr.sort((a, b) => safeNum(b.price) - safeNum(a.price));
    } else if (sortBy === "price_low") {
      arr.sort((a, b) => safeNum(a.price) - safeNum(b.price));
    } else if (sortBy === "free_first") {
      arr.sort((a, b) => Number(a.is_paid) - Number(b.is_paid)); // free first
    }

    return arr;
  }, [filteredNotes, sortBy, showBookmarkedOnly, bookmarkedIds]);

  // ✅ Step 4: grouping
  const groupedNotes = useMemo(() => {
    if (groupBy === "none") {
      return { "All Notes": sortedNotes };
    }

    const map = {};
    for (const n of sortedNotes) {
      const key =
        groupBy === "subject"
          ? n.subject || "Unknown Subject"
          : `Unit ${n.unit || "?"}`;

      if (!map[key]) map[key] = [];
      map[key].push(n);
    }

    // sort groups by name
    const ordered = {};
    Object.keys(map)
      .sort((a, b) => a.localeCompare(b))
      .forEach((k) => (ordered[k] = map[k]));

    return ordered;
  }, [sortedNotes, groupBy]);

  return (
    <Layout title="My Library">
      <div className="border border-black bg-white p-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8 border-b-2 border-black pb-4">
          <div>
            <h2 className="text-3xl font-black uppercase tracking-tighter text-black">📚 My Library</h2>
            <p className="text-gray-500 font-bold uppercase tracking-wide text-sm mt-1">
              All notes you unlocked (Free + Paid)
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                invalidateGet(ENDPOINTS.library.mine);
                fetchLibrary();
              }}
              className="px-4 py-2 border border-black text-black hover:bg-gray-100 transition font-bold uppercase tracking-wide text-sm"
            >
              Refresh
            </button>

            <button
              onClick={exportPDF}
              className="px-4 py-2 bg-black text-white border border-black hover:bg-neutral-800 transition font-bold uppercase tracking-wide text-sm"
            >
              {showBookmarkedOnly ? "Export Bookmarks" : "Export PDF"}
            </button>
          </div>
        </div>

        {offlineMode && (
          <div className="mb-6 border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-bold uppercase tracking-wider text-amber-700">
            Offline mode active{lastSyncedAt ? ` • Last sync: ${new Date(lastSyncedAt).toLocaleString()}` : ""}
          </div>
        )}

        {/* Controls */}
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-8">
          {/* Search */}
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="SEARCH NOTES..."
            className="md:col-span-2 px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none focus:ring-1 focus:ring-black transition-all rounded-none font-medium placeholder-gray-500 text-black uppercase text-sm"
          />

          {/* Filter: Free/Paid */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none font-bold uppercase text-xs"
          >
            <option value="all">All Types</option>
            <option value="free">Free Only</option>
            <option value="paid">Paid Only</option>
          </select>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none font-bold uppercase text-xs"
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="price_high">Price High → Low</option>
            <option value="price_low">Price Low → High</option>
            <option value="free_first">Free First</option>
          </select>

          {/* Group By */}
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value)}
            className="px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all rounded-none font-bold uppercase text-xs"
          >
            <option value="subject">By Subject</option>
            <option value="unit">By Unit</option>
            <option value="none">No Grouping</option>
          </select>

          {/* Bookmarked Toggle */}
          <button
            onClick={() => setShowBookmarkedOnly((prev) => !prev)}
            className={`px-4 py-3 font-bold uppercase tracking-wide text-xs border transition-all ${showBookmarkedOnly
                ? "bg-black text-white border-black"
                : "bg-white text-gray-500 border-gray-300 hover:border-black hover:text-black"
              }`}
          >
            {showBookmarkedOnly ? "⭐ Bookmarked" : "Show All"}
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <Spinner label="Loading your unlocked notes..." />
        ) : sortedNotes.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-gray-300 bg-gray-50">
            <p className="text-black font-black uppercase text-lg">No notes found</p>
            <p className="text-gray-400 font-bold uppercase text-xs mt-1">Try changing filters or search</p>
          </div>
        ) : (
          <div className="space-y-12">
            {Object.entries(groupedNotes).map(([groupName, groupNotes]) => (
              <div key={groupName}>
                {/* Group Title */}
                <div className="flex items-center gap-4 mb-6">
                  <h3 className="text-xl font-black uppercase tracking-wide text-black bg-white pr-4 z-10">
                    {groupName}
                  </h3>
                  <div className="h-px bg-gray-200 flex-1"></div>
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-widest px-3 py-1 border border-gray-200 bg-gray-50">
                    {groupNotes.length} notes
                  </span>
                </div>

                {/* Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {groupNotes.map((n) => (
                    <div
                      key={n.purchase_id}
                      className="border border-black bg-white p-5 hover:bg-gray-50 transition-colors group relative"
                    >
                      <div className="flex justify-between gap-4">
                        <div className="min-w-0">
                          <h4 className="text-lg font-bold text-black uppercase tracking-tight truncate">{n.title}</h4>

                          <p className="text-gray-500 text-xs font-bold uppercase tracking-wider mt-1">
                            {n.subject} • Unit {n.unit} • Sem {n.semester}
                          </p>

                          <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mt-3 border-l-2 border-gray-200 pl-2">
                            {n.is_paid ? `💰 Paid • ₹${n.price}` : "✅ Free"} •{" "}
                            {n.dept}
                          </p>
                        </div>

                        <div className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 bg-emerald-50 px-2 py-1 h-fit border border-emerald-100">
                          Unlocked
                        </div>
                      </div>

                      {n.description && (
                        <p className="text-gray-600 mt-4 text-sm leading-relaxed line-clamp-2 italic border-t border-gray-100 pt-2">
                          {n.description}
                        </p>
                      )}

                      <div className="mt-5 flex gap-3 flex-wrap">
                        {/* View */}
                        <Link
                          to={`/secure-viewer/${n.note_id}`}
                          className="px-4 py-2 bg-black text-white hover:bg-neutral-800 transition font-bold uppercase text-xs tracking-wide"
                        >
                          View
                        </Link>

                        {/* Download ONLY for free */}
                        {!n.is_paid && (
                          <button
                            onClick={() => downloadFree(n)}
                            className="px-4 py-2 border border-black text-black hover:bg-gray-100 transition font-bold uppercase text-xs tracking-wide"
                          >
                            Download
                          </button>
                        )}

                        {/* Details */}
                        <Link
                          to={`/notes/${n.note_id}`}
                          className="px-4 py-2 text-gray-500 hover:text-black hover:underline transition font-bold uppercase text-xs tracking-wide ml-auto"
                        >
                          Details →
                        </Link>
                      </div>

                      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-300 mt-4 text-right">
                        Unlocked via {n.unlocked_type?.toUpperCase()}
                        {n.unlocked_at && (
                          ` • ${new Date(n.unlocked_at * 1000).toLocaleDateString()}`
                        )}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
