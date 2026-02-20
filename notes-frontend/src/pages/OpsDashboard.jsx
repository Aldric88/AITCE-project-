import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import Spinner from "../components/Spinner";
import { ENDPOINTS } from "../api/endpoints";
import { cachedGet, invalidateGet } from "../api/queryCache";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";

export default function OpsDashboard() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [opsHealth, setOpsHealth] = useState(null);
  const [runtime, setRuntime] = useState(null);
  const [workerHealth, setWorkerHealth] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(0);

  const canView = user?.role === "admin" || user?.role === "moderator";

  const fetchAll = useCallback(async (force = false) => {
    try {
      if (!lastUpdated) setLoading(true);
      const [opsRes, runtimeRes, workerRes] = await Promise.allSettled([
        cachedGet(ENDPOINTS.ops.health, { ttlMs: 10000, force }),
        cachedGet(ENDPOINTS.ops.runtime, { ttlMs: 10000, force }),
        cachedGet(ENDPOINTS.ai.workerHealth, { ttlMs: 10000, force }),
      ]);

      if (opsRes.status === "fulfilled") setOpsHealth(opsRes.value.data || null);
      if (runtimeRes.status === "fulfilled") setRuntime(runtimeRes.value.data || null);
      if (workerRes.status === "fulfilled") setWorkerHealth(workerRes.value.data || null);
      setLastUpdated(Date.now());
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to fetch ops metrics");
    } finally {
      setLoading(false);
    }
  }, [lastUpdated]);

  useEffect(() => {
    if (!canView) return;
    fetchAll(true);
    const timer = setInterval(() => fetchAll(true), 15000);
    return () => clearInterval(timer);
  }, [canView, fetchAll]);

  if (!canView) {
    return (
      <Layout title="Ops Dashboard">
        <div className="border border-red-300 bg-red-50 p-8">
          <h2 className="text-lg font-black uppercase tracking-wide text-red-700">Access denied</h2>
          <p className="mt-2 text-sm text-red-600">
            This page is available only to moderator/admin roles.
          </p>
        </div>
      </Layout>
    );
  }

  const queue = workerHealth?.queue || opsHealth?.ai_queue || {};

  return (
    <Layout title="Ops Dashboard">
      {loading ? (
        <Spinner label="Loading platform health..." />
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3 border border-gray-200 bg-white p-4">
            <button
              onClick={() => {
                invalidateGet(ENDPOINTS.ops.health);
                invalidateGet(ENDPOINTS.ops.runtime);
                invalidateGet(ENDPOINTS.ai.workerHealth);
                fetchAll(true);
              }}
              className="btn-primary text-xs"
            >
              Refresh Now
            </button>
            <span className="text-xs font-bold uppercase tracking-wider text-gray-500">
              Last Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "N/A"}
            </span>
            <span className={`ml-auto border px-3 py-1 text-xs font-bold uppercase tracking-wider ${opsHealth?.status === "ok" ? "border-emerald-300 bg-emerald-50 text-emerald-700" : "border-amber-300 bg-amber-50 text-amber-700"}`}>
              API {opsHealth?.status || "unknown"}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Metric title="DB Status" value={opsHealth?.db_ok ? "Healthy" : "Degraded"} />
            <Metric title="Queue Lag" value={`${queue.queue_lag_seconds || 0}s`} />
            <Metric title="Queued Jobs" value={queue.queued ?? 0} />
            <Metric title="Processing Jobs" value={queue.processing ?? 0} />
            <Metric title="Dead-Letter Jobs" value={queue.dead_letter ?? 0} />
            <Metric title="Failed Jobs" value={queue.failed ?? 0} />
            <Metric title="AI Mode" value={workerHealth?.moderation_mode || runtime?.moderation_mode || "rules"} />
            <Metric title="Security Headers" value={runtime?.security_headers ? "On" : "Off"} />
          </div>

          <div className="border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-sm font-black uppercase tracking-[0.2em] text-black">Runtime Config</h3>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <ConfigRow label="Environment" value={runtime?.app_env || "unknown"} />
              <ConfigRow label="Slow Query Threshold" value={`${runtime?.slow_query_threshold_ms ?? "N/A"} ms`} />
              <ConfigRow label="Max AI Attempts" value={`${workerHealth?.max_attempts ?? "N/A"}`} />
              <ConfigRow label="Paid AI API Usage" value={workerHealth?.uses_paid_api === false ? "Disabled" : "Unknown"} />
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

function Metric({ title, value }) {
  return (
    <div className="border border-gray-200 bg-white p-4">
      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-gray-500">{title}</p>
      <p className="mt-2 text-2xl font-black uppercase tracking-tight text-black">{value}</p>
    </div>
  );
}

function ConfigRow({ label, value }) {
  return (
    <div className="flex items-center justify-between border border-gray-100 p-3">
      <span className="text-xs font-bold uppercase tracking-wider text-gray-500">{label}</span>
      <span className="text-xs font-black uppercase tracking-wider text-black">{value}</span>
    </div>
  );
}
