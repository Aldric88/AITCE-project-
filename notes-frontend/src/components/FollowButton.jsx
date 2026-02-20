import { useCallback, useEffect, useState } from "react";
import api from "../api/axios";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";

export default function FollowButton({ creatorId }) {
  const [followingIds, setFollowingIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const { user } = useAuth();

  const fetchFollowing = useCallback(async () => {
    if (!user) {
      setFollowingIds([]);
      setInitialLoading(false);
      return;
    }

    try {
      const res = await api.get("/follow/me/following");
      setFollowingIds(res.data.following_ids || []);
    } catch {
      setFollowingIds([]);
    } finally {
      setInitialLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchFollowing();
  }, [fetchFollowing]);

  const isFollowing = followingIds.includes(creatorId);

  const follow = async () => {
    if (!user) {
      toast.error("Please login to follow creators");
      return;
    }

    try {
      setLoading(true);
      await api.post(`/follow/${creatorId}`);
      toast.success("Followed");
      fetchFollowing();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Follow failed");
    } finally {
      setLoading(false);
    }
  };

  const unfollow = async () => {
    if (!user) {
      toast.error("Please login to unfollow creators");
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/follow/${creatorId}`);
      toast.success("Unfollowed");
      fetchFollowing();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Unfollow failed");
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.id === creatorId) return null;

  if (initialLoading) {
    return (
      <div className="px-3 py-2 text-sm font-medium text-gray-400">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <button
      disabled={loading}
      onClick={isFollowing ? unfollow : follow}
      className={`min-w-[100px] border px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
        isFollowing ? "border-black bg-white text-black hover:bg-gray-100" : "border-black bg-black text-white hover:bg-neutral-800"
      }`}
    >
      {loading ? "Wait..." : isFollowing ? "Following" : "Follow"}
    </button>
  );
}
