import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import FollowButton from "../components/FollowButton";
import { Link } from "react-router-dom";

export default function TopCreators() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTop = async () => {
    try {
      setLoading(true);
      const res = await api.get("/suggestions/top-creators?limit=25");
      setList(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load top creators");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTop();
  }, []);

  return (
    <Layout title="Top Creators">
      <div className="max-w-4xl mx-auto space-y-12">
        <div className="relative overflow-hidden rounded-[3rem] border border-zinc-200 bg-white p-10 shadow-2xl shadow-zinc-200/50 backdrop-blur-xl">
          <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-transparent via-yellow-400 to-transparent opacity-50"></div>

          <div className="flex items-center justify-between mb-12 border-b border-zinc-100 pb-8">
            <div className="space-y-1">
              <h2 className="text-4xl font-black uppercase tracking-tighter text-zinc-900 leading-none">Leaderboard</h2>
              <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-[0.3em]">Our most impactful contributors</p>
            </div>
            <button
              onClick={fetchTop}
              className="px-8 py-3 bg-zinc-900 text-white hover:bg-black transition-all duration-300 font-black uppercase tracking-widest text-[10px] rounded-xl shadow-lg shadow-zinc-200"
            >
              Refresh Data
            </button>
          </div>

          {loading ? (
            <Spinner label="Recalculating standings..." />
          ) : list.length === 0 ? (
            <div className="text-center py-20 bg-zinc-50/50 rounded-[2rem] border border-dashed border-zinc-200">
              <p className="text-zinc-400 font-bold uppercase tracking-widest text-xs">No entries found yet.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {list.map((c, idx) => {
                const picUrl = c.profile_pic_url
                  ? `${API_BASE_URL}${c.profile_pic_url}`
                  : null;

                const isTopThree = idx < 3;
                const rankColors = [
                  "bg-yellow-400/10 text-yellow-600 border-yellow-400/20",
                  "bg-zinc-200/50 text-zinc-600 border-zinc-300/50",
                  "bg-orange-400/10 text-orange-600 border-orange-400/20"
                ];

                return (
                  <div
                    key={c.id}
                    className="group relative flex items-center justify-between gap-6 rounded-[2.5rem] border border-zinc-100 bg-white/40 p-4 backdrop-blur-md transition-all duration-500 hover:border-zinc-300 hover:bg-white hover:shadow-xl hover:shadow-zinc-200/30"
                  >
                    <div className="flex items-center gap-6">
                      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-black border transition-transform group-hover:scale-105 ${isTopThree ? rankColors[idx] : "bg-zinc-50 text-zinc-300 border-zinc-100"}`}>
                        #{idx + 1}
                      </div>

                      <Link to={`/creator/${c.id}`} className="flex items-center gap-6 group/info">
                        <div className="relative">
                          <div className="w-20 h-20 rounded-[1.5rem] overflow-hidden border-2 border-white shadow-md transition-all duration-500 group-hover:scale-110 group-hover:shadow-xl">
                            {picUrl ? (
                              <img src={picUrl} alt="pic" className="w-full h-full object-cover" />
                            ) : (
                              <div className="w-full h-full bg-zinc-900 flex items-center justify-center">
                                <span className="text-xl font-black text-white">{c.name?.[0]?.toUpperCase()}</span>
                              </div>
                            )}
                          </div>
                          {c.verified_seller && (
                            <div className="absolute -bottom-1 -right-1 w-7 h-7 bg-white rounded-full flex items-center justify-center shadow-lg border border-zinc-100">
                              <span className="text-xs">✅</span>
                            </div>
                          )}
                        </div>

                        <div className="space-y-2">
                          <p className="font-black text-zinc-900 uppercase tracking-tight text-2xl leading-none group-hover/info:text-yellow-600 transition-colors">
                            {c.name}
                          </p>
                          <div className="flex items-center space-x-3">
                            <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest bg-zinc-50 px-2 py-0.5 rounded border border-zinc-100">Year {c.year} • {c.section}</span>
                            <span className="w-1 h-1 bg-zinc-200 rounded-full"></span>
                            <div className="flex items-center space-x-3 text-[10px] text-zinc-400 font-bold uppercase tracking-[0.2em]">
                              <span className="flex items-center">
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                {c.contribution_count}
                              </span>
                              <span className="flex items-center">
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                                {c.followers_count}
                              </span>
                            </div>
                          </div>
                        </div>
                      </Link>
                    </div>

                    <div className="pr-4">
                      <FollowButton creatorId={c.id} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
