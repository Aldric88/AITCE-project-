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
    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        const res = await api.get("/seller/dashboard");
        if (active) setData(res.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load seller dashboard");
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <Layout title="Seller Dashboard">
      <div className="space-y-8">
        {loading ? (
          <Spinner label="Loading seller stats..." />
        ) : !data ? (
          <div className="border border-dashed border-gray-300 p-12 text-center">
            <p className="text-sm font-bold uppercase tracking-widest text-gray-500">No data available yet</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              <div className="minimal-card p-8">
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-500">Total Notes</p>
                <p className="text-5xl font-black text-black">{data.total_notes}</p>
              </div>

              <div className="minimal-card p-8">
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-gray-500">Total Sales</p>
                <p className="text-5xl font-black text-black">{data.total_sales}</p>
              </div>

              <div className="minimal-card border-black bg-black p-8 text-white">
                <p className="mb-2 text-xs font-bold uppercase tracking-widest text-white/70">Total Earnings</p>
                <p className="text-5xl font-black">INR {data.total_earnings}</p>
              </div>
            </div>

            <div className="mt-12">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="text-2xl font-black uppercase tracking-tight text-black">Top Performing Notes</h3>
                <div className="ml-6 hidden h-px flex-1 bg-gray-200 sm:block" />
              </div>

              {data.top_notes.length === 0 ? (
                <div className="border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
                  <p className="text-xs font-bold uppercase tracking-widest text-gray-500">No sales activity yet</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {data.top_notes.map((n) => (
                    <Link key={n.id} to={`/notes/${n.id}`} className="minimal-card block p-6 hover:bg-zinc-50">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <h4 className="text-lg font-bold text-zinc-900">{n.title}</h4>
                          <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
                            {n.subject} • {n.sales} sales
                          </p>
                        </div>

                        <span className="border border-black px-4 py-2 text-sm font-bold uppercase">
                          {n.is_paid ? `INR ${n.price}` : "Free"}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
