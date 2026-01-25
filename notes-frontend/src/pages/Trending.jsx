import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import Spinner from "../components/Spinner";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

export default function Trending() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const res = await api.get("/notes/trending");
        setData(res.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load trending");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <Layout title="Trending Notes">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {loading ? (
          <Spinner label="Loading trending notes..." />
        ) : data.length === 0 ? (
          <p className="text-zinc-400">No trending notes yet.</p>
        ) : (
          <div className="space-y-3">
            {data.map((n, i) => (
              <Link
                key={n.id}
                to={`/notes/${n.id}`}
                className="block rounded-xl border border-zinc-800 bg-zinc-950 p-4 hover:bg-zinc-900 transition"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-zinc-400 text-sm">#{i + 1} • 👀 {n.views} views</p>
                    <h3 className="text-lg font-semibold">{n.title}</h3>
                    <p className="text-zinc-500 text-sm">
                      {n.subject} • Unit {n.unit} • Sem {n.semester} • {n.dept}
                    </p>
                  </div>

                  {n.is_paid ? (
                    <span className="text-xs px-3 py-1 rounded-full bg-yellow-600/30 text-yellow-200 border border-yellow-500/30">
                      ₹{n.price}
                    </span>
                  ) : (
                    <span className="text-xs px-3 py-1 rounded-full bg-emerald-600/20 text-emerald-200 border border-emerald-500/30">
                      FREE
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
