import { useEffect, useState } from "react";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import FollowButton from "./FollowButton";
import Spinner from "./Spinner";
import { Link } from "react-router-dom";

export default function SuggestedCreators() {
  const [creators, setCreators] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchSuggestions = async () => {
    try {
      setLoading(true);
      const res = await api.get("/suggestions/creators?limit=8");
      setCreators(res.data);
    } catch {
      // Fail silently — suggestions are non-critical, no toast needed
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuggestions();
  }, []);

  return (
    <div className="border border-black bg-white p-6">
      <div className="flex items-center justify-between mb-6 border-b border-black pb-4">
        <h3 className="text-lg font-black uppercase tracking-wide text-black">Suggested Creators</h3>

        <button
          onClick={fetchSuggestions}
          className="text-xs px-3 py-1 bg-white border border-black text-black hover:bg-black hover:text-white transition font-bold uppercase tracking-wider"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <Spinner label="Finding best creators..." />
      ) : creators.length === 0 ? (
        <p className="text-gray-400 text-xs font-bold uppercase tracking-wide">
          No suggestions right now. Upload notes or follow more people ✅
        </p>
      ) : (
        <div className="space-y-4">
          {creators.map((c) => {
            const picUrl = c.profile_pic_url
              ? `${API_BASE_URL}${c.profile_pic_url}`
              : null;

            return (
              <div
                key={c.id}
                className="flex items-center justify-between gap-3 p-3 bg-gray-50 border border-gray-200 hover:border-black transition-colors"
              >
                <Link to={`/creator/${c.id}`} className="flex items-center gap-3 overflow-hidden">
                  <div className="w-10 h-10 border border-black bg-white flex items-center justify-center shrink-0">
                    {picUrl ? (
                      <img
                        src={picUrl}
                        alt="pic"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span className="text-black font-bold text-sm">
                        {c.name?.[0]?.toUpperCase() || "U"}
                      </span>
                    )}
                  </div>

                  <div className="min-w-0">
                    <p className="font-bold text-black uppercase tracking-wide text-sm truncate">
                      {c.name} {c.verified_seller ? "✅" : ""}
                    </p>

                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider truncate">
                      {c.dept} • {c.year} • {c.section}
                    </p>
                  </div>
                </Link>

                <FollowButton creatorId={c.id} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
