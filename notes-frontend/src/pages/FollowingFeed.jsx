import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import NoteCard from "../components/NoteCard";
import { useAuth } from "../auth/AuthContext";

export default function FollowingFeed() {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("personalized");
  const { user } = useAuth();

  const fetchFeed = useCallback(async () => {
    if (!user) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const res = await api.get(`/follow/feed?mode=${mode}&limit=30`);
      setNotes(res.data || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load feed");
    } finally {
      setLoading(false);
    }
  }, [user, mode]);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  return (
    <Layout title="Following Feed">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 border-b-2 border-black pb-4">
          <h1 className="mb-2 text-3xl font-black uppercase tracking-tighter text-black">Following Feed</h1>
          <p className="text-xs font-bold uppercase tracking-wide text-gray-500">Notes from creators you follow</p>
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => setMode("personalized")}
              className={`border px-3 py-1.5 text-xs font-bold uppercase tracking-wider ${mode === "personalized" ? "border-black bg-black text-white" : "border-gray-300 bg-white text-gray-600"}`}
            >
              Personalized
            </button>
            <button
              onClick={() => setMode("latest")}
              className={`border px-3 py-1.5 text-xs font-bold uppercase tracking-wider ${mode === "latest" ? "border-black bg-black text-white" : "border-gray-300 bg-white text-gray-600"}`}
            >
              Latest
            </button>
          </div>
        </div>

        <div className="min-h-[400px]">
          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner label="Loading notes..." />
            </div>
          ) : notes.length === 0 ? (
            <div className="border-2 border-dashed border-gray-300 bg-gray-50 py-16 text-center">
              <h3 className="mb-2 text-xl font-black uppercase tracking-wide text-black">No notes from followed creators yet</h3>
              <p className="mx-auto mb-6 max-w-md text-xs font-bold uppercase text-gray-500">
                Follow creators to see their notes here.
              </p>
              <Link to="/dashboard" className="btn-primary text-sm">
                Discover Creators
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {notes.map((n) => (
                <div key={n.id}>
                  <NoteCard note={n} hasAccess={n.has_access} />
                  {n.personalization_reason && (
                    <p className="mt-2 text-[11px] font-bold uppercase tracking-wide text-gray-500">
                      {n.personalization_reason}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
