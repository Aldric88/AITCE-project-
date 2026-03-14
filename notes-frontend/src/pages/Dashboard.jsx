import { useCallback, useEffect, useMemo, useState } from "react";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { cachedGet, invalidatePrefix } from "../api/queryCache";
import { apiCachedFetcher, useApiQuery } from "../api/useApiQuery";
import { useAuth } from "../auth/AuthContext";
import Layout from "../components/Layout";
import NoteCard from "../components/NoteCard";
import SkeletonCard from "../components/SkeletonCard";
import toast from "react-hot-toast";
import SuggestedCreators from "../components/SuggestedCreators";
import { checkoutPaidNote } from "../utils/paymentCheckout";

const PAGE_SIZE = 20;
const INITIAL_FILTERS = {
  dept: "",
  semester: "",
  subject: "",
  search: "",
  exam_tag: "",
  sort: "downloads",
  semantic: false,
};

export default function Dashboard() {
  const { user } = useAuth();
  const [notes, setNotes] = useState([]);
  const [likeCounts, setLikeCounts] = useState({});
  const [bookmarkedSet, setBookmarkedSet] = useState(new Set());

  const [downloadingMap, setDownloadingMap] = useState({});
  const [buyingMap, setBuyingMap] = useState({});
  const [bookmarkingMap, setBookmarkingMap] = useState({});
  const [likedSet, setLikedSet] = useState(new Set());
  const [likingMap, setLikingMap] = useState({});

  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);

  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(filters.search), 300);
    return () => clearTimeout(t);
  }, [filters.search]);

  const buildParams = useCallback(
    (skip = 0) => {
      const params = new URLSearchParams();
      if (filters.dept) params.append("dept", filters.dept);
      if (filters.semester) params.append("semester", filters.semester);
      if (filters.subject) params.append("subject", filters.subject);
      if (debouncedSearch) params.append("search", debouncedSearch);
      if (filters.exam_tag) params.append("exam_tag", filters.exam_tag);
      if (filters.sort) params.append("sort", filters.sort);
      if (user?.cluster_id) params.append("cluster_id", user.cluster_id);
      params.append("skip", String(skip));
      params.append("limit", String(PAGE_SIZE));
      return params;
    },
    [
      filters.dept,
      filters.exam_tag,
      filters.semester,
      filters.sort,
      filters.subject,
      debouncedSearch,
      user?.cluster_id,
    ],
  );

  const semanticEnabled = filters.semantic && debouncedSearch.trim().length >= 2;
  const firstPageUrl = useMemo(() => {
    if (semanticEnabled) {
      return `${ENDPOINTS.notes.semanticSearch}?q=${encodeURIComponent(debouncedSearch)}&limit=${PAGE_SIZE}`;
    }
    const params = buildParams(0);
    return `${ENDPOINTS.notes.list}?${params.toString()}`;
  }, [semanticEnabled, debouncedSearch, buildParams]);

  const notesQuery = useApiQuery(
    firstPageUrl,
    apiCachedFetcher(firstPageUrl),
    {
      staleTimeMs: semanticEnabled ? 10000 : 15000,
      onError: () => toast.error("Failed to fetch notes", { id: "notes-fetch-error" }),
    },
  );

  const bookmarksQuery = useApiQuery(
    "bookmarks:mine",
    apiCachedFetcher(ENDPOINTS.bookmarks.mine),
    { enabled: !!user, staleTimeMs: 10000 },
  );
  const likesQuery = useApiQuery(
    "likes:mine",
    apiCachedFetcher(ENDPOINTS.likes.mine),
    { enabled: !!user, staleTimeMs: 10000 },
  );

  const loadMoreNotes = useCallback(async () => {
    if (filters.semantic) return;
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const params = buildParams(nextPage * PAGE_SIZE);
      const res = await cachedGet(`${ENDPOINTS.notes.list}?${params.toString()}`, { ttlMs: 15000 });

      if (res.data.length > 0) {
        setNotes((prev) => [...prev, ...res.data]);
        setPage(nextPage);
        setHasMore(res.data.length === PAGE_SIZE);
      } else {
        setHasMore(false);
      }
    } catch {
      toast.error("Failed to load more notes", { id: "load-more-error" });
    } finally {
      setLoadingMore(false);
    }
  }, [buildParams, hasMore, loadingMore, page, filters.semantic]);

  const buyNote = useCallback(
    async (note) => {
      try {
        setBuyingMap((prev) => ({ ...prev, [note.id]: true }));
        let message = "Unlocked";
        if (note.is_paid) {
          const result = await checkoutPaidNote(note);
          message = result?.alreadyPurchased ? "Already purchased" : "Purchased";
        } else {
          const res = await api.post(
            ENDPOINTS.purchases.buy(note.id),
            {},
            {
              headers: {
                "X-Idempotency-Key": `${note.id}-${Date.now()}-${crypto.randomUUID()}`,
              },
            },
          );
          message = res.data.paid ? "Purchased" : "Unlocked";
        }
        invalidatePrefix(ENDPOINTS.notes.list);
        await notesQuery.refetch();
        toast.success(message);
      } catch (err) {
        toast.error(err.response?.data?.detail || err.message || "Purchase failed");
      } finally {
        setBuyingMap((prev) => ({ ...prev, [note.id]: false }));
      }
    },
    [notesQuery],
  );

  const downloadNote = useCallback(async (note) => {
    try {
      setDownloadingMap((prev) => ({ ...prev, [note.id]: true }));
      const res = await api.get(ENDPOINTS.downloads.note(note.id), { responseType: "blob" });

      const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `${note.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);

      toast.success("Downloaded");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Download failed");
    } finally {
      setDownloadingMap((prev) => ({ ...prev, [note.id]: false }));
    }
  }, []);

  const toggleLike = useCallback(
    async (noteId) => {
      try {
        setLikingMap((prev) => ({ ...prev, [noteId]: true }));

        if (likedSet.has(noteId)) {
          await api.delete(ENDPOINTS.likes.byNote(noteId));
          setLikedSet((prev) => {
            const next = new Set(prev);
            next.delete(noteId);
            return next;
          });
          setLikeCounts((prev) => ({
            ...prev,
            [noteId]: Math.max(0, (prev[noteId] || 0) - 1),
          }));
        } else {
          await api.post(ENDPOINTS.likes.byNote(noteId));
          setLikedSet((prev) => new Set([...prev, noteId]));
          setLikeCounts((prev) => ({
            ...prev,
            [noteId]: (prev[noteId] || 0) + 1,
          }));
        }
        invalidatePrefix(ENDPOINTS.likes.mine);
        await likesQuery.refetch();
      } catch {
        toast.error("Failed to toggle like");
      } finally {
        setLikingMap((prev) => ({ ...prev, [noteId]: false }));
      }
    },
    [likedSet, likesQuery],
  );

  const bookmarkNote = useCallback(
    async (noteId) => {
      try {
        setBookmarkingMap((prev) => ({ ...prev, [noteId]: true }));

        if (bookmarkedSet.has(noteId)) {
          await api.delete(ENDPOINTS.bookmarks.byNote(noteId));
          setBookmarkedSet((prev) => {
            const next = new Set(prev);
            next.delete(noteId);
            return next;
          });
        } else {
          await api.post(ENDPOINTS.bookmarks.byNote(noteId));
          setBookmarkedSet((prev) => new Set([...prev, noteId]));
        }
        invalidatePrefix(ENDPOINTS.bookmarks.mine);
        await bookmarksQuery.refetch();

        window.dispatchEvent(new Event("bookmarks_updated"));
      } catch {
        toast.error("Failed to toggle bookmark");
      } finally {
        setBookmarkingMap((prev) => ({ ...prev, [noteId]: false }));
      }
    },
    [bookmarkedSet, bookmarksQuery],
  );

  const filteredNotes = useMemo(() => {
    const q = debouncedSearch.toLowerCase();
    return notes.filter((note) => {
      return (
        note.title.toLowerCase().includes(q) ||
        note.subject?.toLowerCase().includes(q) ||
        (note.tags && note.tags.some((tag) => tag.toLowerCase().includes(q)))
      );
    });
  }, [debouncedSearch, notes]);

  useEffect(() => {
    setBookmarkedSet(new Set((bookmarksQuery.data || []).map((b) => b.note_id)));
  }, [bookmarksQuery.data]);

  useEffect(() => {
    setLikedSet(new Set(likesQuery.data || []));
  }, [likesQuery.data]);

  useEffect(() => {
    const next = notesQuery.data || [];
    setNotes(next);
    setPage(0);
    setHasMore(!semanticEnabled && next.length === PAGE_SIZE);
  }, [notesQuery.data, semanticEnabled]);

  useEffect(() => {
    const handleScroll = () => {
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 500) {
        loadMoreNotes();
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [loadMoreNotes]);

  return (
    <Layout title="Dashboard">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3 page-enter">
        <div className="lg:col-span-2">
          {/* ── Find Notes Fast panel ── */}
          <div className="relative mb-8 overflow-hidden scale-in border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900">
            {/* Accent top bar */}
            <div className="h-1 w-full bg-black dark:bg-white" />

            {/* Grid pattern decoration */}
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.03] dark:opacity-[0.06]"
              style={{
                backgroundImage:
                  "repeating-linear-gradient(0deg,#000 0,#000 1px,transparent 1px,transparent 32px),repeating-linear-gradient(90deg,#000 0,#000 1px,transparent 1px,transparent 32px)",
              }}
            />

            <div className="relative p-8">
              <div className="mb-6 flex items-center justify-between">
                <h2 className="flex items-center gap-3 text-4xl font-black uppercase tracking-tighter text-black dark:text-white">
                  Find Notes{" "}
                  <span className="relative inline-block bg-black dark:bg-white px-3 py-0.5 text-white dark:text-black">
                    Fast
                    <span className="absolute -right-1 -top-1 h-2 w-2 bg-black dark:bg-white opacity-30" />
                  </span>
                </h2>
                <span className="hidden sm:flex items-center gap-1.5 border border-zinc-200 dark:border-zinc-700 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </span>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="group relative">
                  <label className="mb-1 block text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Semester</label>
                  <select
                    className="w-full border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-black dark:text-white focus:outline-none focus:border-black dark:focus:border-white transition-colors appearance-none cursor-pointer"
                    value={filters.semester}
                    onChange={(e) => setFilters((prev) => ({ ...prev, semester: e.target.value }))}
                  >
                    <option value="">All Semesters</option>
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>{s}th Semester</option>
                    ))}
                  </select>
                </div>

                <div className="group relative">
                  <label className="mb-1 block text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Subject</label>
                  <select
                    className="w-full border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-black dark:text-white focus:outline-none focus:border-black dark:focus:border-white transition-colors appearance-none cursor-pointer"
                    value={filters.subject}
                    onChange={(e) => setFilters((prev) => ({ ...prev, subject: e.target.value }))}
                  >
                    <option value="">All Subjects</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Physics">Physics</option>
                    <option value="Chemistry">Chemistry</option>
                    <option value="Programming">Programming</option>
                    <option value="Data Structures">Data Structures</option>
                    <option value="Algorithms">Algorithms</option>
                    <option value="Database">Database</option>
                    <option value="Networking">Networking</option>
                  </select>
                </div>

                <div className="group relative">
                  <label className="mb-1 block text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Exam Type</label>
                  <select
                    className="w-full border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-black dark:text-white focus:outline-none focus:border-black dark:focus:border-white transition-colors appearance-none cursor-pointer"
                    value={filters.exam_tag}
                    onChange={(e) => setFilters((prev) => ({ ...prev, exam_tag: e.target.value }))}
                  >
                    <option value="">All Types</option>
                    <option value="Mid-Sem">Mid-Sem</option>
                    <option value="End-Sem">End-Sem</option>
                    <option value="Quick Revision">Quick Revision</option>
                    <option value="One-Night Prep">One-Night Prep</option>
                  </select>
                </div>

                <div className="group relative">
                  <label className="mb-1 block text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Sort By</label>
                  <select
                    className="w-full border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-black dark:text-white focus:outline-none focus:border-black dark:focus:border-white transition-colors appearance-none cursor-pointer"
                    value={filters.sort}
                    onChange={(e) => setFilters((prev) => ({ ...prev, sort: e.target.value }))}
                  >
                    <option value="newest">Newest First</option>
                    <option value="downloads">Most Downloaded</option>
                    <option value="rating">Highest Rated</option>
                    <option value="free_first">Free First</option>
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="mb-1 block text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Search</label>
                  <div className="flex gap-2">
                    <input
                      className="flex-1 border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-4 py-2.5 text-sm font-bold uppercase tracking-wide text-black dark:text-white placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none focus:border-black dark:focus:border-white transition-colors"
                      placeholder="Keywords..."
                      value={filters.search}
                      onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && notesQuery.refetch()}
                    />
                    <button
                      onClick={() => notesQuery.refetch()}
                      className="border border-black dark:border-white bg-black dark:bg-white text-white dark:text-black px-5 py-2.5 text-xs font-black uppercase tracking-widest hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-colors whitespace-nowrap"
                    >
                      Search
                    </button>
                  </div>
                </div>

                <label className="md:col-span-2 flex items-center gap-3 cursor-pointer group">
                  <div className="relative">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={!!filters.semantic}
                      onChange={(e) => setFilters((prev) => ({ ...prev, semantic: e.target.checked }))}
                    />
                    <div className="h-4 w-8 border border-zinc-300 dark:border-zinc-600 bg-zinc-100 dark:bg-zinc-800 peer-checked:bg-black dark:peer-checked:bg-white peer-checked:border-black dark:peer-checked:border-white transition-colors" />
                    <div className="absolute top-0.5 left-0.5 h-3 w-3 bg-zinc-400 dark:bg-zinc-600 peer-checked:bg-white dark:peer-checked:bg-black peer-checked:translate-x-4 transition-all" />
                  </div>
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 dark:text-zinc-400 group-hover:text-black dark:group-hover:text-white transition-colors">
                    Semantic Search
                    <span className="ml-2 border border-zinc-300 dark:border-zinc-600 px-1.5 py-0.5 text-[9px]">FREE</span>
                  </span>
                </label>
              </div>

              <div className="mt-5 flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800 pt-4">
                <button
                  onClick={() => setFilters(INITIAL_FILTERS)}
                  className="text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500 hover:text-black dark:hover:text-white transition-colors border border-transparent hover:border-zinc-300 dark:hover:border-zinc-600 px-3 py-1.5"
                >
                  ✕ Clear All
                </button>
                <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-300 dark:text-zinc-700">
                  Notes Market Search Engine
                </span>
              </div>
            </div>
          </div>

          <div className="mb-8 flex items-center justify-between border-b-2 border-black pb-4">
            <h2 className="flex items-center gap-3 text-2xl font-black uppercase tracking-tighter text-black">
              Results
              <span className="border border-gray-200 bg-gray-100 px-2 py-1 text-sm font-bold text-gray-600">
                {filteredNotes.length} found
              </span>
            </h2>
          </div>

          {notesQuery.isLoading || bookmarksQuery.isLoading || likesQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className={`stagger-${Math.min(i % 4 + 1, 8)}`}>
                  <SkeletonCard />
                </div>
              ))}
            </div>
          ) : filteredNotes.length === 0 ? (
            <div className="border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center fade-in">
              <div className="mb-4 text-6xl opacity-40">0</div>
              <h3 className="mb-2 text-xl font-black uppercase tracking-wide text-black">No notes found</h3>
              <p className="text-sm font-bold uppercase text-gray-500">Try adjusting your filters or search terms</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {filteredNotes.map((n, index) => (
                <div key={n.id} className={`relative fade-in-up stagger-${Math.min((index % 6) + 1, 8)}`}>
                  {bookmarkedSet.has(n.id) && (
                    <div className="absolute -right-3 -top-3 z-20">
                      <span className="inline-flex items-center border border-white bg-black px-3 py-1 text-xs font-bold uppercase tracking-wider text-white shadow-md">
                        Saved
                      </span>
                    </div>
                  )}

                  <NoteCard
                    note={n}
                    likeCount={likeCounts[n.id] || 0}
                    hasAccess={n.has_access}
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
                    allowDownload
                  />
                </div>
              ))}
            </div>
          )}

          {loadingMore && (
            <div className="flex justify-center py-8">
              <div className="flex items-center gap-2 text-sm font-bold uppercase text-gray-500">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-black border-t-transparent" />
                Loading more...
              </div>
            </div>
          )}

          {!hasMore && filteredNotes.length > 0 && !notesQuery.isLoading && (
            <div className="py-8 text-center text-sm font-bold uppercase text-gray-400">End of results</div>
          )}
        </div>

        <div className="lg:border-l lg:border-gray-200 lg:pl-8 fade-in-left">
          <SuggestedCreators />
        </div>
      </div>
    </Layout>
  );
}
