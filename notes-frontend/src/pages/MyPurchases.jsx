import { useEffect, useState } from "react";
import api from "../api/axios";
import Layout from "../components/Layout";
import Spinner from "../components/Spinner";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

export default function MyPurchases() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPurchases = async () => {
    try {
      setLoading(true);
      const res = await api.get("/purchases/my");
      setData(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load purchases");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPurchases();
  }, []);

  return (
    <Layout title="My Purchases">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {loading ? (
          <Spinner label="Loading purchases..." />
        ) : data.length === 0 ? (
          <p className="text-zinc-400">No purchases yet.</p>
        ) : (
          <div className="space-y-4">
            {data.map((p) => (
              <div
                key={p.purchase_id}
                className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 flex items-center justify-between"
              >
                <div>
                  <h3 className="font-semibold text-lg">{p.note.title}</h3>
                  <p className="text-zinc-400 text-sm">
                    {p.note.subject} • Unit {p.note.unit} • Sem {p.note.semester}
                  </p>
                  <p className="text-yellow-300 text-sm mt-1">
                    Paid ₹{p.amount}
                  </p>
                </div>

                <Link
                  to="/viewer"
                  state={{ note: p.note }}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition"
                >
                  View
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
