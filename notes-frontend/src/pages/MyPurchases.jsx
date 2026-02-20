import { useEffect, useState } from "react";
import { ENDPOINTS } from "../api/endpoints";
import { normalizePurchaseRecord } from "../api/normalizers";
import { cachedGet } from "../api/queryCache";
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
      const res = await cachedGet(ENDPOINTS.purchases.mine, { ttlMs: 15000 });
      setData((res.data || []).map((row) => normalizePurchaseRecord(row)));
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
      <div className="max-w-5xl mx-auto space-y-12">
        {loading ? (
          <Spinner label="Accessing your library..." />
        ) : data.length === 0 ? (
          <div className="relative overflow-hidden rounded-[3rem] border border-zinc-100 bg-white p-20 text-center shadow-2xl shadow-zinc-200/50">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-zinc-200 to-transparent opacity-20"></div>
            <div className="relative z-10">
              <div className="w-20 h-20 bg-zinc-50 rounded-[2rem] flex items-center justify-center mx-auto mb-8 border border-zinc-100 shadow-inner group transition-transform duration-500 hover:scale-110">
                <svg className="w-10 h-10 text-zinc-300 group-hover:text-zinc-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
              </div>
              <h3 className="text-zinc-800 text-sm font-black uppercase tracking-[0.3em] mb-3">Library Empty</h3>
              <p className="text-zinc-400 text-xs font-medium max-w-xs mx-auto mb-10 leading-relaxed">Your purchased documents will appear here once you've completed a transaction.</p>
              <Link to="/trending" className="inline-flex items-center space-x-2 group">
                <span className="text-yellow-600 text-[10px] font-black uppercase tracking-widest border-b-2 border-yellow-200 group-hover:border-yellow-500 transition-all duration-300 pb-1">Start Browsing Notes</span>
                <svg className="w-4 h-4 text-yellow-500 transform group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-8">
            {data.map((p) => (
              <div
                key={p.purchase_id || p.id}
                className="group relative rounded-[2.5rem] border border-zinc-200 bg-white p-1.5 transition-all duration-700 hover:border-zinc-300 hover:shadow-[0_20px_50px_rgba(0,0,0,0.04)]"
              >
                <div className="bg-white rounded-[2rem] p-8 sm:p-10">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-center gap-4">
                        <div className="px-4 py-1.5 bg-yellow-50 border border-yellow-100 rounded-full shadow-sm">
                          <span className="text-yellow-700 text-[10px] font-black uppercase tracking-widest leading-none">₹{p.amount} Paid</span>
                        </div>
                        <h3 className="text-3xl font-black text-zinc-900 group-hover:text-black transition-colors uppercase tracking-tight leading-none">{p.note?.title || "Note unavailable"}</h3>
                      </div>

                      <div className="flex items-center flex-wrap gap-y-3">
                        <span className="bg-zinc-50 text-zinc-600 px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest border border-zinc-100">{p.note?.subject || "Unknown subject"}</span>
                        <div className="flex items-center ml-4 space-x-4">
                          <span className="w-1 h-1 bg-zinc-200 rounded-full"></span>
                          <span className="text-zinc-400 text-[10px] font-bold uppercase tracking-[0.2em]">Unit {p.note?.unit ?? "-"}</span>
                          <span className="w-1 h-1 bg-zinc-200 rounded-full"></span>
                          <span className="text-zinc-400 text-[10px] font-bold uppercase tracking-[0.2em]">Semester {p.note?.semester ?? "-"}</span>
                        </div>
                      </div>
                    </div>

                    <Link
                      to="/viewer"
                      state={{ note: p.note || { id: p.note_id } }}
                      className="px-10 py-5 rounded-2xl bg-zinc-900 text-white text-[10px] font-black uppercase tracking-[0.3em] hover:bg-black hover:scale-[1.02] active:scale-95 transition-all duration-300 flex items-center justify-center shadow-lg shadow-zinc-200"
                    >
                      <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                      Open Archive
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
