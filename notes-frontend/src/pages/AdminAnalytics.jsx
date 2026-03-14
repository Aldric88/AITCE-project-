import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";

export default function AdminAnalytics() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [riskUsers, setRiskUsers] = useState([]);
  const [days, setDays] = useState(30);
  const [rewardTopN, setRewardTopN] = useState(10);
  const [bootstrapLimit, setBootstrapLimit] = useState(500);
  const [rewardLoading, setRewardLoading] = useState(false);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);

  const canView = user?.role === "admin";

  const load = useCallback(async (windowDays = days) => {
    try {
      const [res, riskRes] = await Promise.all([
        api.get(`${ENDPOINTS.admin.analyticsFunnel}?days=${windowDays}`),
        api.get(`${ENDPOINTS.risk.users}?min_score=45&limit=20`),
      ]);
      setData(res.data);
      setRiskUsers(riskRes.data?.users || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load admin analytics");
    }
  }, [days]);

  useEffect(() => {
    if (!canView) return;
    const t = setTimeout(() => {
      load();
    }, 0);
    return () => clearTimeout(t);
  }, [canView, load]);

  const rewardTopContributors = async () => {
    try {
      setRewardLoading(true);
      const res = await api.post(`${ENDPOINTS.admin.rewardTopContributors}?top_n=${rewardTopN}`);
      toast.success(`Top contributor bonus applied to ${res.data?.awarded || 0} users`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to reward top contributors");
    } finally {
      setRewardLoading(false);
    }
  };

  const bootstrapInitialPoints = async () => {
    try {
      setBootstrapLoading(true);
      const res = await api.post(`${ENDPOINTS.wallet.bootstrapInitial}?limit=${bootstrapLimit}`);
      toast.success(`Initial points backfilled for ${res.data?.awarded || 0} users`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to bootstrap points");
    } finally {
      setBootstrapLoading(false);
    }
  };

  if (!canView) {
    return (
      <Layout title="Admin Analytics">
        <div className="border border-red-300 bg-red-50 p-8">
          <h2 className="text-sm font-black uppercase tracking-wider text-red-700">Admin access required</h2>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Admin Analytics">
      <div className="mb-6 flex items-center gap-3">
        <select className="input-surface max-w-xs" value={days} onChange={(e) => setDays(parseInt(e.target.value, 10) || 30)}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
        <button onClick={() => load(days)} className="btn-primary text-xs px-4">Refresh</button>
      </div>

      {!data ? (
        <div className="border border-black bg-white p-6 text-sm text-zinc-500">Loading...</div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <Metric title="Views" value={data.funnel?.views || 0} />
            <Metric title="Previews" value={data.funnel?.previews || 0} />
            <Metric title="Purchases" value={data.funnel?.purchases || 0} />
            <Metric title="Reviews" value={data.funnel?.reviews || 0} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="border border-black bg-white p-6">
              <h3 className="mb-3 text-sm font-black uppercase tracking-wider">Top Creators</h3>
              <div className="space-y-2">
                {(data.top_creators || []).map((c) => (
                  <div key={c.creator_id} className="border border-zinc-200 p-3 text-xs">
                    <p className="font-black uppercase">{c.creator_name}</p>
                    <p className="text-zinc-600">{c.dept} • Notes {c.notes} • Views {c.views}</p>
                    <p className="font-bold text-black">Sales INR {c.sales}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="border border-black bg-white p-6">
              <h3 className="mb-3 text-sm font-black uppercase tracking-wider">Cohorts by Dept</h3>
              <div className="space-y-2">
                {(data.cohorts_by_dept || []).map((c) => (
                  <div key={c.dept} className="flex items-center justify-between border border-zinc-200 px-3 py-2 text-xs">
                    <span className="font-bold text-zinc-700">{c.dept}</span>
                    <span className="font-black text-black">{c.active_users}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 border-t border-zinc-100 pt-3">
                <p className="text-xs font-bold uppercase tracking-wider text-zinc-500">Inactive users: {data.churn_signals?.inactive_users || 0}</p>
              </div>
            </div>
          </div>

          <div className="border border-black bg-white p-6">
            <h3 className="mb-4 text-sm font-black uppercase tracking-wider">Points Economy Controls</h3>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="border border-zinc-200 p-4">
                <p className="mb-2 text-xs font-black uppercase tracking-wider text-zinc-700">Top Contributor Reward</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    className="input-surface max-w-[140px]"
                    min={1}
                    max={100}
                    value={rewardTopN}
                    onChange={(e) => setRewardTopN(parseInt(e.target.value, 10) || 10)}
                  />
                  <button
                    onClick={rewardTopContributors}
                    disabled={rewardLoading}
                    className="btn-primary px-4 py-2 text-xs"
                  >
                    {rewardLoading ? "Running..." : "Reward Top N"}
                  </button>
                </div>
              </div>

              <div className="border border-zinc-200 p-4">
                <p className="mb-2 text-xs font-black uppercase tracking-wider text-zinc-700">Initial Points Backfill</p>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    className="input-surface max-w-[140px]"
                    min={1}
                    max={5000}
                    value={bootstrapLimit}
                    onChange={(e) => setBootstrapLimit(parseInt(e.target.value, 10) || 500)}
                  />
                  <button
                    onClick={bootstrapInitialPoints}
                    disabled={bootstrapLoading}
                    className="btn-secondary px-4 py-2 text-xs"
                  >
                    {bootstrapLoading ? "Running..." : "Backfill"}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="border border-black bg-white p-6">
            <h3 className="mb-3 text-sm font-black uppercase tracking-wider">Anti-Abuse Risk Queue</h3>
            <div className="space-y-2">
              {riskUsers.map((u) => (
                <div key={u.id} className="flex items-center justify-between border border-zinc-200 px-3 py-2 text-xs">
                  <div>
                    <p className="font-black uppercase text-zinc-800">{u.name}</p>
                    <p className="font-bold uppercase text-zinc-500">{u.email}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-black uppercase text-black">{u.risk_score}</p>
                    <p className="font-bold uppercase text-zinc-500">{u.risk_level}</p>
                  </div>
                </div>
              ))}
              {riskUsers.length === 0 && <p className="text-xs text-zinc-500">No risky users above threshold.</p>}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

function Metric({ title, value }) {
  return (
    <div className="border border-black bg-white p-4">
      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">{title}</p>
      <p className="mt-2 text-2xl font-black uppercase tracking-tight text-black">{value}</p>
    </div>
  );
}
