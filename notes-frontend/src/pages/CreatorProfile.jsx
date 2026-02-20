import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import FollowButton from "../components/FollowButton";
import NoteCard from "../components/NoteCard";

export default function CreatorProfile() {
  const { creatorId } = useParams();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/users/${creatorId}/profile`);
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load creator");
    } finally {
      setLoading(false);
    }
  }, [creatorId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  if (loading) {
    return (
      <Layout title="Creator Profile">
        <div className="border border-black bg-white p-6">
          <Spinner label="Loading creator..." />
        </div>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout title="Creator Profile">
        <p className="text-gray-500">Creator not found.</p>
      </Layout>
    );
  }

  const { creator, followers_count, following_count, notes } = data;
  const picUrl = creator.profile_pic_url ? `${API_BASE_URL}${creator.profile_pic_url}` : null;

  return (
    <Layout title="Creator Profile">
      <div className="mx-auto max-w-4xl">
        <div className="border border-black bg-white p-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row md:items-start">
            <div className="flex flex-col items-center gap-6 md:flex-row">
              <div className="flex h-24 w-24 shrink-0 items-center justify-center border border-black bg-gray-50">
                {picUrl ? (
                  <img src={picUrl} alt="creator" className="h-full w-full object-cover" />
                ) : (
                  <span className="text-3xl font-black text-gray-300">{creator.name?.[0]?.toUpperCase() || "U"}</span>
                )}
              </div>

              <div className="text-center md:text-left">
                <h2 className="flex items-center justify-center gap-2 text-3xl font-black uppercase tracking-tighter text-black md:justify-start">
                  {creator.name} {creator.verified_seller ? "✓" : ""}
                </h2>
                <p className="mt-1 text-xs font-bold uppercase tracking-wide text-gray-500">
                  {creator.dept} • Year {creator.year} • {creator.section}
                </p>

                <div className="mt-4 flex justify-center gap-6 text-xs font-bold uppercase tracking-widest text-gray-400 md:justify-start">
                  <span>
                    Followers: <b className="text-black">{followers_count}</b>
                  </span>
                  <span>
                    Following: <b className="text-black">{following_count}</b>
                  </span>
                </div>
              </div>
            </div>

            <FollowButton creatorId={creator.id} />
          </div>
        </div>

        <div className="mt-8">
          <h3 className="mb-6 inline-block border-b-2 border-black pb-2 text-xl font-black uppercase tracking-wide text-black">
            Notes by {creator.name}
          </h3>

          {notes.length === 0 ? (
            <div className="border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
              <p className="text-sm font-bold uppercase text-gray-400">No notes uploaded yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-2">
              {notes.map((n) => (
                <NoteCard key={n.id} note={n} />
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
