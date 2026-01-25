import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import Spinner from "../components/Spinner";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

export default function SellerDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const res = await api.get("/seller/dashboard");
        setData(res.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load seller dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <Layout title="Seller Dashboard">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {loading ? (
          <Spinner label="Loading seller stats..." />
        ) : !data ? (
          <p className="text-zinc-400">No data available.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-zinc-500 text-sm">Total Notes</p>
                <p className="text-2xl font-bold">{data.total_notes}</p>
              </div>

              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-zinc-500 text-sm">Total Sales</p>
                <p className="text-2xl font-bold">{data.total_sales}</p>
              </div>

              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
                <p className="text-zinc-500 text-sm">Total Earnings</p>
                <p className="text-2xl font-bold text-yellow-300">
                  ₹{data.total_earnings}
                </p>
              </div>
            </div>

            <h3 className="text-xl font-semibold mt-6 mb-3">Top Notes</h3>

            {data.top_notes.length === 0 ? (
              <p className="text-zinc-400">No sales yet.</p>
            ) : (
              <div className="space-y-3">
                {data.top_notes.map((n) => (
                  <Link
                    key={n.id}
                    to={`/notes/${n.id}`}
                    className="block rounded-xl border border-zinc-800 bg-zinc-950 p-4 hover:bg-zinc-900 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold">{n.title}</h4>
                        <p className="text-sm text-zinc-500">
                          {n.subject} • Sales: {n.sales}
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
          </>
        )}
      </div>
    </Layout>
  );
}
