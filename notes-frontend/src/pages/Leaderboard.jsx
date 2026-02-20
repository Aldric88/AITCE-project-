import { useEffect, useState } from "react";
import api from "../api/axios";
import Layout from "../components/Layout";

export default function Leaderboard() {
  const [data, setData] = useState([]);

  useEffect(() => {
    api.get("/leaderboard/").then((res) => setData(res.data)).catch(() => setData([]));
  }, []);

  return (
    <Layout title="Leaderboard">
      <div className="max-w-2xl mx-auto">
        <div className="border border-black bg-white p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
          <h2 className="text-2xl font-black uppercase tracking-tighter text-black mb-8 border-b-2 border-black pb-4">Leaderboard</h2>

          {data.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-gray-300 bg-gray-50">
              <p className="text-gray-400 font-bold uppercase text-sm">No leaderboard data yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.map((u, i) => (
                <div
                  key={u.user_id}
                  className="flex items-center justify-between border border-black bg-white px-4 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="text-gray-300 font-black text-xl w-8">#{i + 1}</div>
                    <div>
                      <div className="font-bold text-black uppercase tracking-wide">{u.name}</div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">{u.dept}</div>
                    </div>
                  </div>

                  <div className="text-black font-black text-lg">
                    ⭐ {u.total_points}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
