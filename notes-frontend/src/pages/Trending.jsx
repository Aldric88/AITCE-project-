import { memo } from "react";
import Layout from "../components/Layout";
import NoteCard from "../components/NoteCard";
import SkeletonCard from "../components/SkeletonCard";
import { useApiQuery, apiCachedFetcher } from "../api/useApiQuery";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

const Trending = memo(function Trending() {
  const trendingQuery = useApiQuery(
    "trending:notes",
    apiCachedFetcher(ENDPOINTS.notes.trending),
    {
      staleTimeMs: 30000,
      onError: () => toast.error("Failed to load trending notes"),
    }
  );

  const notesData = trendingQuery.data || [];

  return (
    <Layout title="Trending Notes">
      <div className="page-enter">
        <div className="mb-8 fade-in">
          <p className="text-sm font-bold uppercase tracking-wide text-gray-600">
            Most popular notes right now
          </p>
        </div>

        {trendingQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={`fade-in stagger-${Math.min(i % 6 + 1, 8)}`}>
                <SkeletonCard />
              </div>
            ))}
          </div>
        ) : notesData.length === 0 ? (
          <div className="border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center fade-in">
            <h3 className="mb-2 text-xl font-black uppercase tracking-wide text-black">No trending notes</h3>
            <p className="text-sm font-bold uppercase text-gray-500">Check back later</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {notesData.map((note, index) => (
              <div key={note.id} className={`fade-in-up stagger-${Math.min((index % 6) + 1, 8)}`}>
                <NoteCard
                  note={note}
                  hasAccess={note.has_access}
                  ribbon={index < 3 ? `#${index + 1}` : null}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
});

export default Trending;
