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
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {data.length === 0 ? (
          <p className="text-zinc-400">No leaderboard data yet.</p>
        ) : (
          <div className="space-y-3">
            {data.map((u, i) => (
              <div
                key={u.user_id}
                className="flex items-center justify-between rounded-xl bg-zinc-950 border border-zinc-800 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <div className="text-zinc-300 font-bold">#{i + 1}</div>
                  <div>
                    <div className="font-semibold">{u.name}</div>
                    <div className="text-sm text-zinc-500">{u.dept}</div>
                  </div>
                </div>

                <div className="text-yellow-300 font-semibold">
                  ⭐ {u.total_points}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
